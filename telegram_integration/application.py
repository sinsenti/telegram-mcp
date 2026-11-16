"""Shared command boundary. Transports never implement task/access policy."""
import asyncio
import fcntl
import json
import os
import sqlite3
import uuid
from dataclasses import asdict
from pathlib import Path
from .contracts import Blocked, CodexAdapter, TelegramAdapter, TaskInput
from .attachments import owned_directory, family, digest, validate_evidence, FAMILIES

class Application:
    def __init__(self, database: Path, workspace: Path, telegram: TelegramAdapter, codex: CodexAdapter, catalog=None):
        database.parent.mkdir(parents=True, exist_ok=True)
        self.execution_path = database.resolve().with_name(database.resolve().name+'.execution.lock')
        self.db = sqlite3.connect(database)
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS selections (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS group_projects (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS topic_tasks (group_id INTEGER, topic_id INTEGER, task_id TEXT, PRIMARY KEY(group_id,topic_id))')
        self.catalog = catalog
        self.workspace = workspace.absolute()
        self.telegram, self.codex = telegram, codex
        self.lock = asyncio.Lock()
        self.monitor_lock = asyncio.Lock()
        from .monitoring import Monitoring
        self.monitoring = Monitoring(self)
        from .outgoing import Outgoing
        self.outgoing = Outgoing(self)

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

    async def _context(self, source, upper_bound=None):
        group, message = source['group_id'], source['message_id']
        await self._access(group)
        context = await self.telegram.context(group,message,source['scope'],upper_bound=upper_bound) if upper_bound is not None else await self.telegram.context(group,message,source['scope'])
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
        """Keep held-event admission outside execution and monitoring ownership."""
        if command.get('action') in ('monitor_status','status'):
            return await self._command(command)
        try:
            return await self._command(command)
        finally:
            # A nested send may have run under monitor_lock (readiness/chat commands).
            # Revisit only after its owner exits; never acquire execution ownership or
            # close the adapter when admitting held requests for an active worker.
            if not self.monitor_lock.locked():
                async with self.monitor_lock:
                    await self.monitoring.release_confirmed()

    async def _command(self, command: dict) -> dict:
        """Manual commands, normalized listener events, and worker dispatch share this seam."""
        action=command.get('action')
        try:
            if action == 'telegram_send_ack':
                return {'status':'confirmed' if self.outgoing.acknowledge(command['random_id'],command['message_id']) else 'unknown'}
            if action in ('monitor_enable','monitor_refresh','monitor_status','telegram_event'):
                if action == 'monitor_status':
                    return await self.monitoring.handle(command)
                async with self.monitor_lock:
                    return await self.monitoring.handle(command)
            if action == 'status':
                return self._task(command['task_id'])
            if self.lock.locked():
                return {'status':'busy','reason':'Another execution owns the Codex adapter'}
            # A distinct open file description per claim gives mutual exclusion
            # across Application instances and processes. The OS releases it on
            # process death; never unlink the shared inode while an owner runs.
            with self.execution_path.open('a+b') as ownership:
                try:
                    fcntl.flock(ownership,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:
                    return {'status':'busy','reason':'Another execution owns this state directory'}
                try:
                    async with self.lock:
                        try:
                            if action in ('task','followup','chat_command','link') and self.monitoring.requires_recovery():
                                return {'status':'blocked','reason':'A previous automatic request requires recovery before manual execution'}
                            if action == 'dispatch_pending':
                                return await self.monitoring.dispatch()
                            return await self._handle(command)
                        finally:
                            await self.codex.aclose()
                finally:
                    fcntl.flock(ownership,fcntl.LOCK_UN)
        except Exception as exc:
            return {'status':'blocked','reason':str(exc)}

    async def _send_generated(self, kind, group, *args, operation_key=None, document_sha256=None):
        return await self.outgoing.send(kind,group,args,operation_key,document_sha256=document_sha256)

    def _verify_report_document(self, task):
        if not task.get('document_sha256'):
            raise Blocked('Legacy report lacks original document identity; inspect Telegram manually')
        document=Path(task['document'])
        if document.is_symlink() or not document.is_file() or digest(document)!=task['document_sha256']:
            raise Blocked('Completed report document changed; original payload is required')

    async def _deliver_reports(self, task):
        if not task.get('reporting_version') and len(task.get('report_ids',[]))<2:
            raise Blocked('Legacy task reporting lacks durable operation identity; inspect Telegram manually')
        if len(task.get('report_ids',[]))<2:
            self._verify_report_document(task)
        prefix=f"task:{task['task_id']}:run:{task['run']}"
        if not task.get('report_ids'):
            task['report_ids']=[await self._send_generated('text',task['group_id'],task['message_id'],task['explanation'],task['topic_id'],operation_key=prefix+':text')]
            self._save(task)
            self._verify_report_document(task)
        if len(task['report_ids'])<2:
            self._verify_report_document(task)
            task['report_ids'].append(await self._send_generated('document',task['group_id'],task['message_id'],Path(task['document']),task['topic_id'],operation_key=prefix+':document',document_sha256=task['document_sha256']))
            self._verify_report_document(task)
        task.update(status='finished',phase='complete',reason=None)
        self._save(task)
        return task

    async def _project(self, group, choice_id=None, choice=None):
        await self._access(group)
        metadata = await self.telegram.group_metadata(group)
        if metadata.group_id != group or not isinstance(metadata.name,str) or not metadata.name:
            raise Blocked('Telegram resolved invalid or different group metadata')
        await self._access(group)
        if self.catalog is None:
            raise Blocked('A refreshable Codex project catalog is required')
        projects = await asyncio.to_thread(self.catalog.refresh)
        row = self.db.execute('SELECT data FROM group_projects WHERE id=?',(group,)).fetchone()
        saved = json.loads(row[0]) if row else None
        if choice_id is not None:
            selection = self._selection(choice_id)
            if selection['kind'] != 'project' or selection['group_id'] != group or type(choice) is not int or not 1 <= choice <= len(selection['projects']):
                raise Blocked('Choose a valid project for this group')
            selected = selection['projects'][choice-1]
            matches = [p for p in projects if p.id == selected['project_id']]
            if len(matches) != 1 or [str(r) for r in matches[0].roots] != [selected['cwd']]:
                raise Blocked('Project choice changed or disappeared; refresh choices')
            saved = selected
        elif saved:
            matches = [p for p in projects if p.id == saved['project_id']]
            if len(matches) != 1 or [str(r) for r in matches[0].roots] != [saved['cwd']]:
                saved = None
        else:
            matches = [p for p in projects if p.name == metadata.name]
            if len(matches) == 1 and len(matches[0].roots) == 1:
                saved = {'project_id':matches[0].id,'cwd':str(matches[0].roots[0])}
        if saved is None:
            choices = [{'project_id':p.id,'name':p.name,'cwd':str(p.roots[0])} for p in projects if len(p.roots)==1]
            identity = self._remember({'kind':'project','group_id':group,'projects':choices})
            return {'status':'project_choice','group_id':group,'choice_id':identity,
                    'reason':'Choose an existing project: group name has no unique destination',
                    'choices':[dict(p,choice=i+1) for i,p in enumerate(choices)]}
        cwd = Path(saved['cwd'])
        if not cwd.is_absolute() or not cwd.is_dir():
            raise Blocked('Selected project working directory is unavailable')
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO group_projects VALUES (?,?)',(group,json.dumps(saved)))
        return saved

    async def _chat_choices(self, project):
        projects = await asyncio.to_thread(self.catalog.refresh)
        matches = [p for p in projects if p.id == project['project_id']]
        if len(matches) != 1 or [str(root) for root in matches[0].roots] != [project['cwd']]:
            raise Blocked('Assigned project changed during chat selection; refresh')
        # A legacy unassigned chat can belong by exact cwd only when precisely
        # one catalog project owns it. Non-null canonical membership wins.
        unique_root = sum(str(root) == project['cwd'] for p in projects for root in p.roots) == 1
        chats = await self.codex.list_chats(project['project_id'], Path(project['cwd']))
        result = []
        seen = set()
        for chat in chats:
            identity = chat.get('chat_id')
            if not isinstance(identity, str) or not identity or identity in seen:
                raise Blocked('Codex returned invalid or duplicate chat identifiers')
            seen.add(identity)
            if chat.get('cwd') != project['cwd']:
                continue
            canonical = chat.get('project_id')
            if canonical == project['project_id'] or (canonical is None and unique_root):
                result.append({'chat_id':identity,'title':chat.get('title') or identity,
                               'membership':'canonical' if canonical else 'unique_project_cwd'})
        return result

    async def _link(self, c):
        group, topic = int(c['group_id']), int(c['topic_id'])
        await self._access(group)
        project = await self._project(group)
        if project.get('status') == 'project_choice':
            return project
        chats = await self._chat_choices(project)
        await self._access(group)
        if 'choice_id' not in c:
            identity = self._remember({'kind':'chat','group_id':group,'topic_id':topic,
                                       'project':project,'chats':chats})
            with self.db:
                self.db.execute('CREATE TABLE IF NOT EXISTS topic_choices (group_id INTEGER, topic_id INTEGER, choice_id TEXT, PRIMARY KEY(group_id,topic_id))')
                self.db.execute('INSERT OR REPLACE INTO topic_choices VALUES (?,?,?)',(group,topic,identity))
            return {'status':'chat_choice','choice_id':identity,'group_id':group,'topic_id':topic,
                    'choices':[dict(chat,choice=i+1) for i,chat in enumerate(chats)]}
        saved = self._selection(c['choice_id'])
        choice = c.get('choice')
        if (saved.get('kind') != 'chat' or saved['group_id'] != group or saved['topic_id'] != topic
                or saved['project'] != project or type(choice) is not int or not 1 <= choice <= len(saved['chats'])):
            raise Blocked('Choose a valid presented chat for this project and topic')
        pending = self.db.execute('SELECT choice_id FROM topic_choices WHERE group_id=? AND topic_id=?',(group,topic)).fetchone()
        if not pending or pending[0] != c['choice_id']:
            raise Blocked('Chat choices expired; send #link again')
        selected = saved['chats'][choice-1]
        current = next((chat for chat in chats if chat['chat_id'] == selected['chat_id']), None)
        if current is None:
            raise Blocked('Selected chat disappeared or changed project; refresh choices')
        for other_group, other_topic, task_id in self.db.execute('SELECT group_id,topic_id,task_id FROM topic_tasks'):
            if (other_group,other_topic) != (group,topic) and self._task(task_id).get('chat_id') == selected['chat_id']:
                raise Blocked('Selected chat already has another Telegram topic')
        row = self.db.execute('SELECT task_id FROM topic_tasks WHERE group_id=? AND topic_id=?',(group,topic)).fetchone()
        previous = self._task(row[0]) if row else None
        if previous and previous['status'] not in ('finished','linked'):
            raise Blocked('Inspect unfinished topic work before linking another chat')
        if previous and previous['chat_id'] == selected['chat_id']:
            task = previous
        else:
            retained = [json.loads(row[0]) for row in self.db.execute('SELECT data FROM tasks')]
            retained = [t for t in retained if t.get('chat_id') == selected['chat_id'] and t.get('group_id') == group and t.get('topic_id') == topic and t.get('project_id') == project['project_id'] and t.get('cwd') == project['cwd']]
            if retained:
                task = retained[-1]
                if task['status'] not in ('finished','linked'):
                    raise Blocked('Inspect unfinished selected chat work before linking')
            else:
                task_id = uuid.uuid4().hex
                task = {'task_id':task_id,'group_id':group,'topic_id':topic,**project,
                    'chat_id':selected['chat_id'],'folder':str(self.workspace/task_id),
                    'status':'linked','run':0,'membership':current['membership']}
            owned_directory(Path(task['folder']))
        task['membership'] = current['membership']
        self._save(task)
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO topic_tasks VALUES (?,?,?)',(group,topic,task['task_id']))
            self.db.execute('DELETE FROM topic_choices WHERE group_id=? AND topic_id=?',(group,topic))
        return dict(task,status='linked')

    async def _chat_command(self, c):
        # Normalized event admission owns fresh author/generation eligibility. This boundary
        # independently resolves the actual source topic and never scans context.
        text = c.get('text','').strip()
        if text != '#link' and not (text.isascii() and text.isdecimal()):
            return {'status':'ignored'}
        message = await self._read(int(c['group_id']),int(c['message_id']))
        if message.text.strip() != text:
            raise Blocked('Command text differs from its current source message')
        if message.topic_id is None:
            raise Blocked('Chat linking requires a Telegram topic')
        normalized = {'group_id':message.group_id,'topic_id':message.topic_id}
        if text == '#link':
            return await self._link(normalized)
        self.db.execute('CREATE TABLE IF NOT EXISTS topic_choices (group_id INTEGER, topic_id INTEGER, choice_id TEXT, PRIMARY KEY(group_id,topic_id))')
        row = self.db.execute('SELECT choice_id FROM topic_choices WHERE group_id=? AND topic_id=?',(message.group_id,message.topic_id)).fetchone()
        if not row:
            return {'status':'ignored'}
        return await self._link(dict(normalized,choice_id=row[0],choice=int(text)))

    def _validate_topic_binding(self, task):
        if not task.get('project_id'):
            return
        row = self.db.execute('SELECT task_id FROM topic_tasks WHERE group_id=? AND topic_id=?',
                              (task['group_id'],task.get('topic_id'))).fetchone()
        if not row or row[0] != task['task_id']:
            raise Blocked('Task topic binding was superseded; use the current topic chat')
        for group, topic, task_id in self.db.execute('SELECT group_id,topic_id,task_id FROM topic_tasks'):
            owner = self._task(task_id)
            if task.get('chat_id') and owner.get('chat_id') == task['chat_id'] and (
                    (group,topic) != (task['group_id'],task['topic_id'])
                    or (owner.get('group_id'),owner.get('topic_id')) != (group,topic)):
                raise Blocked('Linked chat has a different Telegram topic owner')

    async def _placement(self, task):
        # Standalone thread/read observes canonical server assignment, not the
        # desktop's independently cached sidebar. Never claim the latter here.
        observations=[]
        for _ in range(3):
            try:
                observed=await asyncio.wait_for(self.codex.observe_chat(task['chat_id'],Path(task['cwd'])),5)
                observations.append(observed)
                if observed.get('chat_id') != task['chat_id']:
                    break
                canonical = observed.get('project_id') == task['project_id']
                legacy = False
                if task.get('membership') == 'unique_project_cwd' and observed.get('project_id') is None:
                    projects = await asyncio.to_thread(self.catalog.refresh)
                    legacy = sum(str(root) == task['cwd'] for project in projects for root in project.roots) == 1
                if (canonical or legacy) and observed.get('cwd') == task['cwd']:
                    return {'status':'legacy_cwd_verified_desktop_unverified' if legacy else 'server_verified_desktop_unverified','observations':observations}
                await asyncio.sleep(0.2)
            except Exception as error:
                observations.append({'error':str(error)})
                break
        return {'status':'unresolved','observations':observations,
                'reason':'Project placement could not be reconciled; inspect before continuing'}

    def _store_result(self, task, result):
        folder=Path(task['folder'])
        task.update(turn_id=result.turn_id, explanation=result.explanation,
                    result_status=result.status, input_evidence=[asdict(item) for item in result.input_evidence])
        (folder/f"run-result-{task['run']}.json").write_text(json.dumps(asdict(result),ensure_ascii=False))
        task['phase']='terminal_result'
        self._save(task)

    async def _finish_result(self, task, result, inputs):
        folder=Path(task['folder'])
        self._store_result(task,result)
        if task.get('project_id'):
            task['placement']=await self._placement(task)
        (folder/f"evidence-{task['run']}.json").write_text(json.dumps(task['input_evidence'],ensure_ascii=False))
        if result.status != 'completed':
            raise Blocked(result.explanation)
        if task.get('placement',{}).get('status') == 'unresolved':
            raise Blocked(task['placement']['reason'])
        validate_evidence(inputs,result.input_evidence)
        for item in inputs:
            owned_directory(Path(item.path).parent)
            if Path(item.path).is_symlink() or digest(item.path)!=item.sha256:
                raise Blocked(f'{item.original_name}: preserved original changed during execution')
        task.update(turn_id=result.turn_id, explanation=result.explanation, phase='reporting')
        document = folder/f"result-{task['run']}.md"
        document.write_text(result.markdown)
        task['document'] = str(document)
        task['document_sha256'] = digest(document)
        task['reporting_version'] = 1
        self._save(task)
        await self._deliver_reports(task)

    async def _start_captured(self, task, text, inputs):
        """Initiate each external operation only after its durable intent exists."""
        await self._access(task['group_id'])
        if task['chat_id'] is None:
            if task.get('codex_create_intent'):
                raise Blocked('Codex chat creation outcome is unresolved; no replacement chat is safe')
            task.update(phase='creating_chat',codex_create_intent=uuid.uuid4().hex)
            self._save(task)
            task['chat_id'] = (await self.codex.create_chat(Path(task['cwd']),project_id=task['project_id'])
                               if task.get('project_id') else await self.codex.create_chat(Path(task['folder'])))
            self._save(task)
        await self._access(task['group_id'])
        if task.get('client_request_id'):
            raise Blocked('Codex turn start outcome needs reconciliation before another turn can start')
        task.update(phase='executing',client_request_id=str(uuid.uuid4()))
        self._save(task)
        async def accepted(turn_id):
            task['turn_id']=turn_id
            self._save(task)
            if hasattr(self,'folder_access'):
                await self.folder_access.interrupt_if_revoked(task)
        prompt=text+'\n\nReturn the result as Markdown in your final answer. Identify blockers explicitly.'
        return await self.codex.run(task['chat_id'],Path(task.get('cwd',task['folder'])),prompt,
            inputs=inputs,client_request_id=task['client_request_id'],on_turn_accepted=accepted)

    async def _handle(self, c):
        action = c['action']
        if action == 'configure':
            folder = int(c['folder_id'])
            await self.telegram.allowed_groups(folder)  # Validate stable identity before saving.
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO settings VALUES ('folder', ?)", (str(folder),))
            return {'status':'configured', 'folder_id':folder}
        if action == 'project':
            return await self._project(int(c['group_id']),c.get('choice_id'),c.get('choice'))
        if action == 'link':
            return await self._link(c)
        if action == 'chat_command':
            return await self._chat_command(c)
        if action == 'recover':
            from .recovery import Recovery
            return await Recovery(self).recover(c.get('task_id'))
        if action == 'reconcile_reports':
            if not c.get('task_id'):
                return await self.outgoing.reconcile()
            task=self._task(c['task_id'])
            if task.get('phase') not in ('reporting','complete') or not task.get('document'):
                raise Blocked('Task has no completed result awaiting reporting')
            try:
                await self._deliver_reports(task)
                self.monitoring.update_matching_delivery_outcome(task)
                return task
            except Exception as exc:
                task.update(status='blocked',reason=str(exc))
                self._save(task)
                return task
        if action == 'sync_reference':
            from .references import synchronize
            return await synchronize(self, self._task(c['task_id']))
        if action == 'sync_references':
            from .references import synchronize
            rows = self.db.execute('SELECT DISTINCT task_id FROM topic_tasks').fetchall()
            results = []
            for row in rows:
                task = self._task(row[0])
                if task.get('chat_id'):
                    results.append(await synchronize(self, task))
            return {'status':'synchronized','tasks':results}
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
            if c.get('destination') not in ('test','project'):
                raise Blocked('Explicit destination=test or destination=project required')
            source = await self._source(c)
            project = None
            if c['destination'] == 'project':
                project = await self._project(source['group_id'])
                if project.get('status') == 'project_choice':
                    return project
                selected = await self._read(source['group_id'],source['message_id'])
                if selected.topic_id is None:
                    raise Blocked('Project routing requires a Telegram topic')
                row = self.db.execute('SELECT task_id FROM topic_tasks WHERE group_id=? AND topic_id=?',(source['group_id'],selected.topic_id)).fetchone()
                if row:
                    return await self._handle(dict(c,action='followup',task_id=row[0]))
            task_id = uuid.uuid4().hex
            task = {'task_id':task_id, **source,
                    'folder':str(self.workspace/task_id), 'chat_id':None, 'status':'pending', 'run':0}
            if project:
                task.update(project,topic_id=selected.topic_id)
        else:
            task = self._task(c['task_id'])
            self._validate_topic_binding(task)
            can_continue=(task['status']=='blocked'
                          and task.get('phase') in ('capturing_inputs','terminal_result')
                          and not task.get('report_blocker')
                          and task.get('placement',{}).get('status') != 'unresolved')
            if task['status'] not in ('finished','linked') and not can_continue:
                raise Blocked('Task is not finished; inspect its state before continuing or retrying')
            # Follow-ups may choose a new source only inside the same group.
            if 'group_id' in c and int(c['group_id']) != task['group_id']:
                raise Blocked('Follow-up source must remain in the same group')
            source = await self._source({'group_id':task['group_id'], **c})
            if source['group_id'] != task['group_id']:
                raise Blocked('Follow-up source must remain in the same group')
            task.update(source)
        if task.get('project_id'):
            project = await self._project(task['group_id'])
            if project.get('status') == 'project_choice':
                return project
            if project.get('project_id') != task['project_id'] or project.get('cwd') != task['cwd']:
                raise Blocked('Task destination differs from its group assignment')
        if task.get('membership'):
            chats = await self._chat_choices(project)
            if not any(chat['chat_id'] == task['chat_id'] for chat in chats):
                raise Blocked('Linked chat no longer belongs to the assigned project')
        if task.get('project_id') and task.get('chat_id'):
            placement = await self._placement(task)
            if placement['status'] == 'unresolved':
                raise Blocked('Existing chat no longer belongs to the assigned project: '+placement['reason'])
        context = await self._context(task,c.get('context_upper_bound'))
        if c.get('context_upper_bound') is not None and any(m.message_id>c['context_upper_bound'] for m in context.messages):
            raise Blocked('Telegram returned context beyond the request boundary')
        if not context.complete:
            raise Blocked('Selected context is incomplete: '+str(context.reason or 'history unavailable'))
        m = next(m for m in context.messages if m.message_id == task['message_id'])
        if task.get('project_id') and task.get('topic_id') not in (None,m.topic_id):
            raise Blocked('Follow-up source must remain in the same topic')
        text = '\n\n'.join(item.text for item in context.messages)
        if not text.strip():
            raise Blocked('Selected message has no task text')
        folder = Path(task['folder'])
        owned_directory(folder)
        task['run'] += 1
        (folder/f"input-{task['run']}.txt").write_text(text)
        (folder/f"context-{task['run']}.json").write_text(json.dumps([asdict(item) for item in context.messages],ensure_ascii=False))
        # These fields describe only the current run. Earlier artifacts remain on disk.
        for key in ('codex_create_intent','client_request_id','turn_id','input_evidence','result_status','explanation','document',
                    'report_ids','blocker_report_id','report_blocker','document_sha256'):
            task.pop(key,None)
        task.update(status='running', reason=None, topic_id=m.topic_id)
        self._save(task)
        if c.get('request_sequence') is not None:
            self.monitoring.bind_task(c['request_sequence'],task)
        if task.get('project_id'):
            with self.db:
                self.db.execute('INSERT OR REPLACE INTO topic_tasks VALUES (?,?,?)',(task['group_id'],m.topic_id,task['task_id']))
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
            task['snapshot_sha256']={name:digest(folder/name) for name in (f"input-{task['run']}.txt",f"context-{task['run']}.json",f"inputs-{task['run']}.json")}
            task['phase']='captured'
            self._save(task)
            result = await self._start_captured(task,text,inputs)
            await self._finish_result(task,result,inputs)
        except Exception as exc:
            task.update(status='blocked', reason=str(exc))
            if task.get('phase') != 'reporting':
                try:
                    await self._access(task['group_id'])
                    task['blocker_report_id'] = await self._send_generated('text',task['group_id'], task['message_id'], 'Blocked: '+str(exc), task['topic_id'])
                except Exception as report_exc:
                    task['report_blocker'] = str(report_exc)
        self._save(task)
        return task
