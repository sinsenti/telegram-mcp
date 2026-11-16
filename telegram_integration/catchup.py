"""Bounded application discovery, independent of Telethon's update cursor."""
from datetime import datetime
from .contracts import Blocked
from .monitoring import MARKER

class Catchup:
    def __init__(self, app):
        self.app=app
        app.db.executescript('''
            CREATE TABLE IF NOT EXISTS catchup_progress (group_id INTEGER PRIMARY KEY, cutoff INTEGER, message_id INTEGER);
            CREATE TABLE IF NOT EXISTS catchup_uncertainties (group_id INTEGER, message_id INTEGER, reason TEXT, PRIMARY KEY(group_id,message_id));
        ''')

    async def discover(self, command):
        app=self.app
        size=command.get('page_size',100)
        if type(size) is not int or not 1<=size<=100:
            raise Blocked('Catch-up page size must be 1–100')
        folder=app.db.execute("SELECT value FROM settings WHERE key='folder'").fetchone()
        account=app.db.execute("SELECT value FROM settings WHERE key='monitor_account'").fetchone()
        if not folder or not account:
            raise Blocked('Enable monitoring before catching up')
        allowed=await app.telegram.allowed_groups(int(folder[0]))
        pages=[]
        for group,cutoff,status in app.db.execute('SELECT * FROM monitoring_groups ORDER BY group_id').fetchall():
            if group not in allowed or status!='ready':
                continue
            saved=app.db.execute('SELECT cutoff,message_id FROM catchup_progress WHERE group_id=?',(group,)).fetchone()
            after=saved[1] if saved and saved[0]==cutoff else cutoff
            await app._access(group)
            events=await app.telegram.history_page(group,after,size)
            if len(events)>size or any(e.get('group_id')!=group or type(e.get('message_id')) is not int or e['message_id']<=after for e in events):
                raise Blocked('Catch-up page has an invalid group, boundary, or size')
            ids=[e['message_id'] for e in events]
            if ids!=sorted(set(ids)):
                raise Blocked('Catch-up page must be ordered without duplicate identities')
            pages.append((group,cutoff,after,events))
        observed=[]
        for group,cutoff,after,events in pages:
            for event in events:
                try:
                    created=datetime.fromisoformat(event['created_at'])
                    if created.tzinfo is None: raise ValueError()
                except (KeyError,TypeError,ValueError):
                    raise Blocked('Catch-up observation lacks a timezone-aware creation timestamp')
                observed.append((created,group,event['message_id'],event))
        outcomes=[]
        # Every admission and page cursor commits together. A crash or rejected
        # page leaves both untouched; duplicate identities also protect retries.
        with app.db:
            for _,group,message,event in sorted(observed,key=lambda e:e[:3]):
                if event.get('kind')!='history_message':
                    raise Blocked('Catch-up requires history observations, not forged new-message events')
                outcome=await app.monitoring.handle(dict(event,action='telegram_event',account_id=int(account[0])),replay=True,commit=False)
                outcomes.append(outcome)
                if event.get('edited') and MARKER.search(event.get('text','')):
                    app.db.execute('INSERT OR IGNORE INTO catchup_uncertainties VALUES (?,?,?)',
                        (group,message,'Edited offline history cannot prove the original #codex marker; excluded unless a pristine new-message observation was already recorded'))
            for group,cutoff,after,events in pages:
                app.db.execute('INSERT OR REPLACE INTO catchup_progress VALUES (?,?,?)',(group,cutoff,max([after]+[e['message_id'] for e in events])))
        return {'status':'caught_up','observed':len(observed),'admitted':sum(o['status']=='admitted' for o in outcomes),
                'possibly_more':any(len(events)==size for _,_,_,events in pages),
                'uncertainties':[dict(group_id=g,message_id=m,reason=r) for g,m,r in app.db.execute('SELECT * FROM catchup_uncertainties ORDER BY group_id,message_id')]}
