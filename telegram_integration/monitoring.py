"""Durable monitoring policy, called only through Application.handle."""
import json
import re
from .contracts import Blocked

MARKER = re.compile(r'(?<!\w)#codex(?!\w)', re.IGNORECASE)

class Monitoring:
    def __init__(self, app):
        self.app=app
        app.db.executescript('''
            CREATE TABLE IF NOT EXISTS monitoring_groups (group_id INTEGER PRIMARY KEY, cutoff INTEGER, status TEXT);
            CREATE TABLE IF NOT EXISTS trigger_requests (sequence INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, group_id INTEGER, message_id INTEGER, data TEXT, status TEXT, UNIQUE(account_id,group_id,message_id));
            CREATE TABLE IF NOT EXISTS discovery_progress (group_id INTEGER PRIMARY KEY, message_id INTEGER);
            CREATE TABLE IF NOT EXISTS held_events (group_id INTEGER, message_id INTEGER, data TEXT, reason TEXT, PRIMARY KEY(group_id,message_id));
            CREATE TABLE IF NOT EXISTS generated_messages (group_id INTEGER, message_id INTEGER, PRIMARY KEY(group_id,message_id));
            CREATE TABLE IF NOT EXISTS generated_sends (id TEXT PRIMARY KEY, group_id INTEGER, status TEXT);
        ''')

    async def handle(self, c):
        app=self.app
        if c['action']=='monitor_status':
            return {'status':'monitoring','generated_sends':[dict(operation_id=r[0],group_id=r[1],status=r[2]) for r in app.db.execute('SELECT * FROM generated_sends')],
                    'held_events':[dict(group_id=r[0],message_id=r[1],reason=r[2]) for r in app.db.execute('SELECT group_id,message_id,reason FROM held_events')],
                    'discovery_progress':[dict(group_id=r[0],message_id=r[1]) for r in app.db.execute('SELECT * FROM discovery_progress')],
                    'groups':[dict(group_id=r[0],cutoff=r[1],status=r[2]) for r in app.db.execute('SELECT * FROM monitoring_groups')],
                    'requests':[dict(sequence=r[0],group_id=r[1],message_id=r[2],status=r[3],outcome=json.loads(r[4]).get('outcome')) for r in app.db.execute('SELECT sequence,group_id,message_id,status,data FROM trigger_requests ORDER BY sequence')]}
        if c['action'] in ('monitor_enable','monitor_refresh'):
            folder=app.db.execute("SELECT value FROM settings WHERE key='folder'").fetchone()
            if not folder: raise Blocked('Select a folder before enabling monitoring')
            account=await app.telegram.self_id()
            with app.db:
                app.db.execute("INSERT OR REPLACE INTO settings VALUES ('monitor_account',?)",(str(account),))
            groups=await app.telegram.allowed_groups(int(folder[0]))
            for group in groups:
                row=app.db.execute('SELECT status FROM monitoring_groups WHERE group_id=?',(group,)).fetchone()
                if row and row[0]!='disabled': continue
                cutoff=await app.telegram.latest_message_id(group)
                with app.db:
                    app.db.execute('INSERT OR REPLACE INTO monitoring_groups VALUES (?,?,?)',(group,cutoff,'readiness_pending'))
                try:
                    ready_id=await app._send_generated('text',group,None,'Codex monitoring is ready. Post a fresh #codex request in a topic to start work.',None)
                except Exception:
                    with app.db:
                        app.db.execute("UPDATE monitoring_groups SET status='readiness_uncertain' WHERE group_id=?",(group,))
                    raise
                with app.db:
                    app.db.execute("UPDATE monitoring_groups SET status='ready', cutoff=MAX(cutoff,?) WHERE group_id=?",(int(ready_id),group))
            with app.db:
                for (group,) in app.db.execute('SELECT group_id FROM monitoring_groups').fetchall():
                    if group not in groups:
                        app.db.execute("UPDATE monitoring_groups SET status='disabled' WHERE group_id=?",(group,))
                        app.db.execute("UPDATE trigger_requests SET status='paused' WHERE group_id=? AND status='pending'",(group,))
            return await self.handle({'action':'monitor_status'})
        if c['action']=='telegram_event':
            group=int(c['group_id']); message=int(c['message_id'])
            await app._access(group)
            account=app.db.execute("SELECT value FROM settings WHERE key='monitor_account'").fetchone()
            activation=app.db.execute('SELECT cutoff,status FROM monitoring_groups WHERE group_id=?',(group,)).fetchone()
            reason=None
            if not account or not activation or activation[1]!='ready': reason='Monitoring is not ready for this group'
            elif c.get('kind')!='new_message': reason='Edits and historical observations do not prove a fresh request'
            elif c.get('forwarded'): reason='Forwarded content is not a fresh user-authored request'
            elif c.get('edited'): reason='Edited history cannot prove the original request marker'
            elif c.get('sender_id')!=int(account[0]) or c.get('account_id')!=int(account[0]): reason='Request is not authored by the connected user'
            elif message<=activation[0]: reason='Message predates readiness'
            elif app.db.execute('SELECT 1 FROM generated_messages WHERE group_id=? AND message_id=?',(group,message)).fetchone(): reason='Integration-generated message'
            elif app.db.execute("SELECT 1 FROM generated_sends WHERE group_id=? AND status!='confirmed'",(group,)).fetchone(): reason='Unresolved integration send; candidate held for reconciliation'
            marker=bool(MARKER.search(c.get('text','')))
            if reason:
                if 'held' in reason:
                    with app.db:
                        app.db.execute('INSERT OR REPLACE INTO held_events VALUES (?,?,?,?)',(group,message,json.dumps(c),reason))
                return {'status':'held' if 'held' in reason else 'ignored','reason':reason}
            # Discovery progress and admission are one commit, including harmless context messages.
            with app.db:
                app.db.execute('INSERT INTO discovery_progress VALUES (?,?) ON CONFLICT(group_id) DO UPDATE SET message_id=MAX(message_id,excluded.message_id)',(group,message))
                if marker:
                    cursor=app.db.execute('INSERT OR IGNORE INTO trigger_requests(account_id,group_id,message_id,data,status) VALUES (?,?,?,?,?)',(int(account[0]),group,message,json.dumps(c),'pending'))
                    return {'status':'admitted' if cursor.rowcount else 'duplicate'}
            if c.get('text','').strip()=='#link' or c.get('text','').strip().isdigit():
                if app.lock.locked():
                    return {'status':'held','reason':'Execution is active; resend the chat command after it finishes'}
                async with app.lock:
                    outcome=await app._handle(dict(c,action='chat_command'))
                    if outcome.get('status') in ('chat_choice','linked'):
                        source=await app._read(group,message)
                        if outcome['status']=='chat_choice':
                            text='Choose a Codex chat by replying with its number:\n'+'\n'.join(f"{item['choice']}. {item.get('title',item.get('chat_id','Untitled'))}" for item in outcome['choices'])
                        else:
                            text='Linked this topic to its selected Codex chat.'
                        await app._send_generated('text',group,message,text,source.topic_id)
                    return outcome
            return {'status':'ignored','reason':'Ordinary task context'}
        raise Blocked('Unsupported monitoring command')

    async def dispatch(self):
        app=self.app
        row=app.db.execute("SELECT sequence,group_id,message_id,data FROM trigger_requests WHERE status='pending' ORDER BY sequence LIMIT 1").fetchone()
        if not row: return {'status':'idle'}
        sequence,group,message,data=row
        event=json.loads(data)
        await app._access(group)
        trigger=await app._read(group,message)
        if not MARKER.search(trigger.text):
            with app.db: app.db.execute("UPDATE trigger_requests SET status='cancelled' WHERE sequence=?",(sequence,))
            return {'status':'cancelled'}
        with app.db:
            claimed=app.db.execute("UPDATE trigger_requests SET status='running' WHERE sequence=? AND status='pending'",(sequence,)).rowcount
        if not claimed: return {'status':'busy'}
        try:
            outcome=await app._handle(dict(action='task',group_id=group,message_id=message,scope='topic',destination='project',context_upper_bound=message))
        except Exception as error:
            outcome={'status':'blocked','reason':str(error)}
        event['outcome']=outcome
        with app.db:
            app.db.execute('UPDATE trigger_requests SET status=?,data=? WHERE sequence=?',('finished' if outcome.get('status')=='finished' else 'blocked',json.dumps(event),sequence))
        return outcome
