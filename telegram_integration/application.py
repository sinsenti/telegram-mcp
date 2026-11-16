"""Shared command boundary. Transports never implement task/access policy."""
import asyncio
import json
import sqlite3
import uuid
from pathlib import Path
from .contracts import Blocked, CodexAdapter, TelegramAdapter

class Application:
    def __init__(self, database: Path, workspace: Path, telegram: TelegramAdapter, codex: CodexAdapter):
        database.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(database)
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.workspace = workspace.resolve()
        self.telegram, self.codex = telegram, codex
        self.lock = asyncio.Lock()

    def close(self):
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

    async def handle(self, command: dict) -> dict:
        """Manual commands today; later normalized listener commands use this seam."""
        async with self.lock:
            try:
                return await self._handle(command)
            except Exception as exc:
                return {'status':'blocked', 'reason':str(exc)}

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
        if action == 'read':
            m = await self._read(int(c['group_id']), int(c['message_id']))
            return {'status':'selected', 'text':m.text, 'has_attachment':m.has_attachment, 'complete':True}
        if action not in ('task', 'followup'):
            raise Blocked('Unsupported command')
        if action == 'task':
            if c.get('destination') != 'test':
                raise Blocked('Explicit destination=test required; real-project routing is not configured')
            task_id = uuid.uuid4().hex
            task = {'task_id':task_id, 'group_id':int(c['group_id']), 'message_id':int(c['message_id']),
                    'folder':str(self.workspace/task_id), 'chat_id':None, 'status':'pending', 'run':0}
        else:
            task = self._task(c['task_id'])
            if task['status'] != 'finished':
                raise Blocked('Task is not finished; inspect its state before continuing or retrying')
            # Follow-ups may choose a new source only inside the same group.
            task['message_id'] = int(c['message_id'])
        m = await self._read(task['group_id'], task['message_id'])
        if m.has_attachment:
            raise Blocked('Selected message has an attachment; attachment handling is not available in this text slice')
        if not m.text.strip():
            raise Blocked('Selected message has no task text')
        folder = Path(task['folder'])
        folder.mkdir(parents=True, exist_ok=True)
        task['run'] += 1
        (folder/f"input-{task['run']}.txt").write_text(m.text)
        task.update(status='running', reason=None, topic_id=m.topic_id)
        self._save(task)
        try:
            if task['chat_id'] is None:
                task['phase'] = 'creating_chat'
                self._save(task)
                task['chat_id'] = await self.codex.create_chat(folder)
                self._save(task)
            task['phase'] = 'executing'
            self._save(task)
            result = await self.codex.run(task['chat_id'], folder,
                m.text+'\n\nReturn the result as Markdown in your final answer. Identify blockers explicitly.')
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
