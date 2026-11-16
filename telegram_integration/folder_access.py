"""Durable observed revocation; remote operations already accepted cannot be undone."""
import json
from pathlib import Path
from .contracts import Blocked

class FolderAccess:
    def __init__(self, app):
        self.app=app
        app.db.execute('CREATE TABLE IF NOT EXISTS folder_access (group_id INTEGER PRIMARY KEY, epoch INTEGER NOT NULL, enabled INTEGER NOT NULL)')

    def state(self, group):
        row=self.app.db.execute('SELECT epoch,enabled FROM folder_access WHERE group_id=?',(group,)).fetchone()
        return row if row else (0,1)

    def check_enabled(self, group):
        if not self.state(group)[1]:
            raise Blocked('Group access is disabled after observed folder removal')

    def preserve_pause(self, task):
        epoch,enabled=self.state(task['group_id'])
        if not enabled or task.get('access_epoch',0)!=epoch:
            task.update(status='paused',reason='Group was removed from the selected Telegram folder')
        row=self.app.db.execute('SELECT data FROM tasks WHERE id=?',(task['task_id'],)).fetchone()
        if row:
            previous=json.loads(row[0])
            if previous.get('run')==task.get('run') and previous.get('interruption') and (not task.get('interruption') or task['interruption'].get('status')=='requested'):
                task['interruption']=previous['interruption']

    async def revoke(self, group, *, interrupt=True):
        app=self.app
        epoch,enabled=self.state(group)
        with app.db:
            if enabled:
                app.db.execute('INSERT OR REPLACE INTO folder_access VALUES (?,?,0)',(group,epoch+1))
            app.db.execute("UPDATE monitoring_groups SET status='disabled' WHERE group_id=?",(group,))
            app.db.execute("UPDATE trigger_requests SET status='paused' WHERE group_id=? AND status IN ('pending','running','blocked','uncertain')",(group,))
            tasks=[]
            for (data,) in app.db.execute('SELECT data FROM tasks').fetchall():
                task=json.loads(data)
                if task['group_id']==group and task.get('status') not in ('finished','linked','cancelled'):
                    task.update(status='paused',reason='Group was removed from the selected Telegram folder')
                    app._save(task); tasks.append(task)
        if interrupt:
            for task in tasks:
                await self.interrupt_if_revoked(task)

    async def interrupt_group(self, group):
        for (data,) in self.app.db.execute('SELECT data FROM tasks').fetchall():
            task=json.loads(data)
            if task['group_id']==group:
                await self.interrupt_if_revoked(task)

    async def interrupt_if_revoked(self, task):
        if self.state(task['group_id'])[1] and task.get('access_epoch',0)==self.state(task['group_id'])[0]:
            return
        if not task.get('chat_id') or not task.get('turn_id') or task.get('phase')!='executing':
            return
        if task.get('interruption',{}).get('turn_id')==task['turn_id']:
            return
        task['interruption']={'turn_id':task['turn_id'],'status':'requested'}
        self.app._save(task)
        try:
            await self.app.codex.interrupt_turn(task['chat_id'],Path(task.get('cwd',task['folder'])),task['turn_id'])
            task['interruption']['status']='acknowledged'
        except Exception as error:
            task['interruption'].update(status='unresolved',reason=str(error))
        # Ack means requested, never proof of terminal interruption.
        with self.app.db:
            current=self.app._task(task['task_id'])
            current['interruption']=task['interruption']
            self.app._save(current)

    def enable(self, group):
        epoch,_=self.state(group)
        with self.app.db:
            self.app.db.execute('INSERT OR REPLACE INTO folder_access VALUES (?,?,1)',(group,epoch))
