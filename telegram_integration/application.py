"""Shared command boundary. Transports never implement task/access policy."""
import asyncio
import json
import os
import sqlite3
import uuid
from dataclasses import asdict
from pathlib import Path
from .contracts import Blocked, CodexAdapter, TelegramAdapter, TaskInput
from .attachments import owned_directory, family, digest, validate_evidence, FAMILIES

class Application:
    def __init__(self, database: Path, workspace: Path, telegram: TelegramAdapter, codex: CodexAdapter):
        database.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(database)
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS selections (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.workspace = workspace.absolute()
        self.telegram, self.codex = telegram, codex
        self.lock = asyncio.Lock()

    async def close(self):
        try:
            await self.codex.aclose()
        finally:
            self.db.close()

    def _save(self, task):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO tasks VALUES (?, ?)', (task['task_id'], json.dumps(task)))

    def _task(self, task_id):
        row = self.db.execute('SELECT data FROM tasks WHERE id=?', (task_id,)).fetchone()
        if not row:
            raise Blocked('Unknown task identifier')
        return json.loads(row[0])

    async def _access(self, group_id):
        row = self.db.execute("SELECT value FROM settings WHERE key='folder'").fetchone()
        if row is None:
            raise Blocked('Select a Telegram folder before reading or running tasks')
        if group_id not in await self.telegram.allowed_groups(int(row[0])):
            raise Blocked('Group is outside the selected Telegram folder')

    async def _read(self, group_id, message_id):
        await self._access(group_id)
        message = await self.telegram.message(group_id, message_id)
        if message.group_id != group_id or message.message_id != message_id:
            raise Blocked('Telegram resolved a different message destination')
        await self._access(message.group_id)
        return message

    def _remember(self, value):
        identity = uuid.uuid4().hex
        with self.db:
            self.db.execute('INSERT INTO selections VALUES (?, ?)', (identity,json.dumps(value)))
        return identity

    def _selection(self, identity):
        row = self.db.execute('SELECT data FROM selections WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise Blocked('Unknown selection or continuation')
        return json.loads(row[0])

    async def _source(self, c):
        if 'query' in c:
            raise Blocked('Search first, then select a numbered result before running a task')
        if 'selection_id' in c:
            selection = self._selection(c['selection_id'])
            if selection['kind'] != 'context':
                raise Blocked('A context selection is required')
            source = selection['source']
        elif 'search_id' in c:
            search = self._selection(c['search_id'])
            choice = c.get('choice')
            if search['kind'] != 'search' or type(choice) is not int or not 1 <= choice <= len(search['messages']):
                raise Blocked('Choose a valid numbered search result')
            if choice not in search.get('presented',[]):
                raise Blocked('Choose a search result from the presented pages')
            selected = search['messages'][choice-1]
            source = {'group_id':selected['group_id'],'message_id':selected['message_id'],'scope':c.get('scope','message')}
        elif 'link' in c:
            # Adapter resolves the actual peer and enforces current folder access
            # before fetching any message content.
            row = self.db.execute("SELECT value FROM settings WHERE key='folder'").fetchone()
            if row is None:
                raise Blocked('Select a Telegram folder before resolving links')
            await self.telegram.allowed_groups(int(row[0]))
            message = await self.telegram.resolve_link(c['link'])
            await self._access(message.group_id)
            source = {'group_id':message.group_id,'message_id':message.message_id,
                      'scope':c.get('scope','topic' if message.is_topic_root else 'message')}
        else:
            source = {'group_id':int(c['group_id']),'message_id':int(c['message_id']),'scope':c.get('scope','message')}
        if source['scope'] not in ('message','topic'):
            raise Blocked('Selection scope must be message or topic')
        await self._access(source['group_id'])
        return source

    async def _context(self, source):
        group, message = source['group_id'], source['message_id']
        await self._access(group)
        context = await self.telegram.context(group,message,source['scope'])
        if not context.messages or not any(m.message_id == message for m in context.messages):
            raise Blocked('Selected Telegram message is missing from task context')
        if any(m.group_id != group for m in context.messages):
            raise Blocked('Telegram resolved a different context destination')
        if len({m.message_id for m in context.messages}) != len(context.messages):
            raise Blocked('Telegram returned duplicate context identities')
        await self._access(group)
        return context

    async def _page(self, identity, offset, page_size):
        saved = self._selection(identity)
        if type(offset) is not int or offset < 0 or type(page_size) is not int or not 1 <= page_size <= 100:
            raise Blocked('Invalid continuation or page size (1–100)')
        for group in {m['group_id'] for m in saved['messages']}:
            await self._access(group)
        messages = saved['messages'][offset:offset+page_size]
        end = offset+len(messages)
        continuation = None
        if end < len(saved['messages']):
            continuation = self._remember({'kind':'continuation','selection_id':identity,'offset':end,'page_size':page_size})
        common = {'complete':saved['complete'],'reason':saved.get('reason'),
                  'page_complete':continuation is None,'continuation':continuation,'total_messages':len(saved['messages'])}
        if saved['kind'] == 'search':
            saved['presented']=sorted(set(saved.get('presented',[])) | set(range(offset+1,end+1)))
            with self.db:
                self.db.execute('UPDATE selections SET data=? WHERE id=?',(json.dumps(saved),identity))
            return dict(common,status='choices',search_id=identity,
                        choices=[dict(m,choice=offset+i+1) for i,m in enumerate(messages)])
        return dict(common,status='selected',selection_id=identity,scope=saved['source']['scope'],messages=messages,
                    text='\n\n'.join(m['text'] for m in messages),has_attachment=any(m['has_attachment'] for m in messages))

    async def handle(self, command: dict) -> dict:
        """Manual commands today; later normalized listener commands use this seam."""
        async with self.lock:
            try:
                return await self._handle(command)
            except Exception as exc:
                return {'status':'blocked', 'reason':str(exc)}
            finally:
                # A failed state write between chat creation and its first turn
                # must release the unmaterialized chat's owned process too.
                await self.codex.aclose()

    async def _handle(self, c):
        action = c['action']
        if action == 'configure':
            folder = int(c['folder_id'])
            await self.telegram.allowed_groups(folder)  # Validate stable identity before saving.
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO settings VALUES ('folder', ?)", (str(folder),))
            return {'status':'configured', 'folder_id':folder}
        if action == 'status':
            return self._task(c['task_id'])
        if action == 'search':
            query=c.get('query','')
            if not isinstance(query,str) or not query.strip():
                raise Blocked('Search needs nonempty text')
            row=self.db.execute("SELECT value FROM settings WHERE key='folder'").fetchone()
            if row is None:
                raise Blocked('Select a Telegram folder before searching')
            groups=sorted(await self.telegram.allowed_groups(int(row[0]))) if 'group_id' not in c else [int(c['group_id'])]
            messages=[]
            for group in groups:
                await self._access(group)
                found=await self.telegram.search(group,query)
                if any(m.group_id != group for m in found):
                    raise Blocked('Search resolved a different group')
                await self._access(group)
                messages.extend(asdict(m) for m in found)
            identity=self._remember({'kind':'search','messages':messages,'complete':True})
            return await self._page(identity,0,c.get('page_size',50))
        if action == 'read':
            if 'continuation' in c:
                token = self._selection(c['continuation'])
                if token['kind'] != 'continuation':
                    raise Blocked('Invalid continuation')
                return await self._page(token['selection_id'],token['offset'],token['page_size'])
            source = await self._source(c)
            context = await self._context(source)
            identity = self._remember({'kind':'context','source':source,'messages':[asdict(m) for m in context.messages],
                                       'complete':context.complete,'reason':context.reason})
            return await self._page(identity,0,c.get('page_size',50))
        if action not in ('task', 'followup'):
            raise Blocked('Unsupported command')
        if action == 'task':
            if c.get('destination') != 'test':
                raise Blocked('Explicit destination=test required; real-project routing is not configured')
            source = await self._source(c)
            task_id = uuid.uuid4().hex
            task = {'task_id':task_id, **source,
                    'folder':str(self.workspace/task_id), 'chat_id':None, 'status':'pending', 'run':0}
        else:
            task = self._task(c['task_id'])
            if task['status'] != 'finished':
                raise Blocked('Task is not finished; inspect its state before continuing or retrying')
            # Follow-ups may choose a new source only inside the same group.
            if 'group_id' in c and int(c['group_id']) != task['group_id']:
                raise Blocked('Follow-up source must remain in the same group')
            source = await self._source({'group_id':task['group_id'], **c})
            if source['group_id'] != task['group_id']:
                raise Blocked('Follow-up source must remain in the same group')
            task.update(source)
        context = await self._context(task)
        if not context.complete:
            raise Blocked('Selected context is incomplete: '+str(context.reason or 'history unavailable'))
        m = next(m for m in context.messages if m.message_id == task['message_id'])
        text = '\n\n'.join(item.text for item in context.messages)
        if not text.strip():
            raise Blocked('Selected message has no task text')
        folder = Path(task['folder'])
        owned_directory(folder)
        task['run'] += 1
        (folder/f"input-{task['run']}.txt").write_text(text)
        (folder/f"context-{task['run']}.json").write_text(json.dumps([asdict(item) for item in context.messages],ensure_ascii=False))
        task.update(status='running', reason=None, topic_id=m.topic_id)
        self._save(task)
        try:
            inputs=[]
            task['inputs']=[]
            task['phase']='capturing_inputs'
            self._save(task)
            exclusions=c.get('unnecessary_input_ids',[])
            if not isinstance(exclusions,list) or any(not isinstance(value,str) for value in exclusions):
                raise Blocked('unnecessary_input_ids must be an explicit list of input identities')
            identities={f'{item.group_id}:{item.message_id}:{item.attachment.media_id}'
                        for item in context.messages if item.attachment}
            if set(exclusions)-identities:
                raise Blocked('Explicit exclusion names an input outside the selected context')
            blockers=[]
            for index,item in enumerate(context.messages):
                if not item.has_attachment:
                    continue
                if item.attachment is None:
                    blockers.append(f'Message {item.message_id}: attachment metadata is unavailable')
                    continue
                attachment=item.attachment
                identity=f'{item.group_id}:{item.message_id}:{attachment.media_id}'
                kind=family(attachment.original_name,attachment.mime_type)
                excluded=identity in exclusions
                if excluded and kind != 'unsupported':
                    blockers.append(f'{attachment.original_name}: only unsupported inputs may be explicitly excluded')
                directory=owned_directory(folder/'inputs'/str(task['run'])/str(index))
                # Source names never become paths or active instruction filenames.
                suffix=Path(attachment.original_name).suffix.lower()
                suffix=suffix if suffix in {extension for values in FAMILIES.values() for extension in values} else '.bin'
                destination=directory/('original'+suffix)
                record={'input_id':identity,'source_group_id':item.group_id,'source_message_id':item.message_id,
                        'media_id':attachment.media_id,'original_name':attachment.original_name,'mime_type':attachment.mime_type,
                        'path':str(destination),'family':kind,'explicitly_unnecessary':excluded}
                try:
                    await self._access(item.group_id)
                    descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                    with os.fdopen(descriptor,'wb') as stream:
                        await self.telegram.download(item.group_id,item.message_id,attachment,stream)
                        expected_stat=os.fstat(stream.fileno())
                    owned_directory(directory)
                    actual_stat=destination.stat()
                    if (expected_stat.st_dev,expected_stat.st_ino)!=(actual_stat.st_dev,actual_stat.st_ino):
                        raise Blocked('Downloaded original destination changed')
                    if destination.is_symlink() or not destination.is_file():
                        raise Blocked('Downloaded original is not a regular file')
                    size=destination.stat().st_size
                    if attachment.size is not None and size!=attachment.size:
                        raise Blocked(f'Download size differs from source ({size}/{attachment.size})')
                    record.update(sha256=digest(destination),size=size)
                    inputs.append(TaskInput(**record))
                    record['download_status']='preserved'
                except Exception as exc:
                    record.update(download_status='failed',reason=str(exc))
                    blockers.append(f'{attachment.original_name}: {exc}')
                task['inputs'].append(record)
                self._save(task)
                if kind=='unsupported' and not excluded:
                    blockers.append(f'{attachment.original_name}: unsupported input is needed or its necessity is unknown; supply usable input or explicit unnecessary_input_ids')
            (folder/f"inputs-{task['run']}.json").write_text(json.dumps(task['inputs'],ensure_ascii=False))
            if blockers:
                raise Blocked('; '.join(blockers))
            inputs=tuple(inputs)
            if task['chat_id'] is None:
                task['phase'] = 'creating_chat'
                self._save(task)
                task['chat_id'] = await self.codex.create_chat(folder)
                self._save(task)
            task['phase'] = 'executing'
            self._save(task)
            prompt=text+'\n\nReturn the result as Markdown in your final answer. Identify blockers explicitly.'
            result = await self.codex.run(task['chat_id'], folder, prompt, inputs=inputs) if inputs else await self.codex.run(task['chat_id'], folder, prompt)
            task.update(turn_id=result.turn_id, input_evidence=[asdict(item) for item in result.input_evidence])
            self._save(task)
            (folder/f"evidence-{task['run']}.json").write_text(json.dumps(task['input_evidence'],ensure_ascii=False))
            validate_evidence(inputs,result.input_evidence)
            if result.status != 'completed':
                raise Blocked(result.explanation)
            for item in inputs:
                owned_directory(Path(item.path).parent)
                if Path(item.path).is_symlink() or digest(item.path)!=item.sha256:
                    raise Blocked(f'{item.original_name}: preserved original changed during execution')
            task.update(turn_id=result.turn_id, explanation=result.explanation, phase='reporting')
            document = folder/f"result-{task['run']}.md"
            document.write_text(result.markdown)
            task['document'] = str(document)
            self._save(task)
            await self._access(task['group_id'])
            task['report_ids'] = [await self.telegram.send_text(task['group_id'], task['message_id'], result.explanation, task['topic_id'])]
            self._save(task)
            await self._access(task['group_id'])
            task['report_ids'].append(await self.telegram.send_document(task['group_id'], task['message_id'], document, task['topic_id']))
            task.update(status='finished', phase='complete')
        except Exception as exc:
            task.update(status='blocked', reason=str(exc))
            if task.get('phase') != 'reporting':
                try:
                    await self._access(task['group_id'])
                    task['blocker_report_id'] = await self.telegram.send_text(task['group_id'], task['message_id'], 'Blocked: '+str(exc), task['topic_id'])
                except Exception as report_exc:
                    task['report_blocker'] = str(report_exc)
        self._save(task)
        return task
