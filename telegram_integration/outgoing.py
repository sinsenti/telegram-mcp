"""Durable Telegram send identities; no guessing from matching message text."""
import inspect
import json
import secrets
import uuid
from pathlib import Path
from .attachments import digest
from .contracts import Blocked, FrozenDocument

class Outgoing:
    def __init__(self, app):
        self.app=app
        app.db.execute('CREATE TABLE IF NOT EXISTS outgoing_operations (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        # Old uncertain rows have no payload/random ID and must continue blocking.
        if hasattr(app.telegram,'set_outgoing_observer'):
            app.telegram.set_outgoing_observer(self.acknowledge)

    def acknowledge(self, random_id, message_id):
        app=self.app
        for identity,data in app.db.execute('SELECT id,data FROM outgoing_operations').fetchall():
            operation=json.loads(data)
            if operation['random_id']==random_id:
                operation['message_id']=str(message_id)
                with app.db:
                    app.db.execute('UPDATE outgoing_operations SET data=? WHERE id=?',(json.dumps(operation),identity))
                    app.db.execute('INSERT OR IGNORE INTO generated_messages VALUES (?,?)',(operation['group_id'],int(message_id)))
                    app.db.execute("UPDATE generated_sends SET status='confirmed' WHERE id=?",(identity,))
                return True
        return False

    async def send(self, kind, group, args, key=None, *, document_sha256=None):
        app=self.app
        identity=key or uuid.uuid4().hex
        row=app.db.execute('SELECT data FROM outgoing_operations WHERE id=?',(identity,)).fetchone()
        if row:
            operation=json.loads(row[0])
            if operation.get('message_id') is not None:
                return operation['message_id']
            if not operation['replayable']:
                raise Blocked('Telegram outcome cannot be reconciled: adapter has no stable send identity; inspect Telegram manually')
        else:
            if app.db.execute("SELECT 1 FROM generated_sends WHERE group_id=? AND status!='confirmed' AND id NOT IN (SELECT id FROM outgoing_operations)",(group,)).fetchone():
                raise Blocked('Legacy Telegram send lacks a durable identity; inspect Telegram before new delivery')
            method=app.telegram.create_reference if kind=='reference' else getattr(app.telegram,'send_'+kind)
            replayable='random_id' in inspect.signature(method).parameters
            stored=list(args)
            if kind=='document':
                stored[1]=str(Path(stored[1]).absolute())
            original_sha256=(document_sha256 or digest(stored[1])) if kind=='document' else None
            operation=dict(kind=kind,group_id=group,args=stored,random_id=secrets.randbits(63),replayable=replayable,account_id=await app.telegram.self_id() if hasattr(app.telegram,'self_id') else None)
            if kind=='document': operation['sha256']=original_sha256
            with app.db:
                app.db.execute('INSERT INTO outgoing_operations VALUES (?,?)',(identity,json.dumps(operation)))
                app.db.execute('INSERT INTO generated_sends VALUES (?,?,?)',(identity,group,'pending'))
        group=operation['group_id']; args=list(operation['args']); kind=operation['kind']
        await app._access(group)
        if operation.get('account_id') is not None and await app.telegram.self_id()!=operation['account_id']:
            raise Blocked('Outgoing operation belongs to a different Telegram account')
        if kind=='document':
            args[1]=Path(args[1])
            if (document_sha256 is not None and operation.get('sha256')!=document_sha256
                    or args[1].is_symlink() or digest(args[1])!=operation['sha256']):
                raise Blocked('Pending Telegram upload changed; original payload is required')
        method=app.telegram.create_reference if kind=='reference' else getattr(app.telegram,'send_'+kind)
        send_args=list(args)
        if kind=='document':
            send_args[1]=FrozenDocument.capture(args[1],operation['sha256'])
        try:
            message=await method(group,*send_args,**({'random_id':operation['random_id']} if operation['replayable'] else {}))
        except BaseException:
            with app.db:
                app.db.execute("UPDATE generated_sends SET status='uncertain' WHERE id=? AND status!='confirmed'",(identity,))
            raise
        self.acknowledge(operation['random_id'],message)
        if kind=='document' and (args[1].is_symlink() or digest(args[1])!=operation['sha256']):
            raise Blocked('Telegram upload changed during delivery; original payload is required')
        return str(message)

    async def reconcile(self):
        app=self.app
        outcomes=[]
        for identity,data in app.db.execute("SELECT outgoing_operations.id,data FROM outgoing_operations JOIN generated_sends USING(id) WHERE status!='confirmed'").fetchall():
            operation=json.loads(data)
            try:
                await self.send(operation['kind'],operation['group_id'],operation['args'],identity)
                outcomes.append({'operation_id':identity,'status':'confirmed'})
            except Exception as exc:
                outcomes.append({'operation_id':identity,'status':'blocked','reason':str(exc)})
        for identity, in app.db.execute("SELECT id FROM generated_sends WHERE status!='confirmed' AND id NOT IN (SELECT id FROM outgoing_operations)"):
            outcomes.append({'operation_id':identity,'status':'blocked','reason':'Legacy send lacks durable payload and random identity; inspect Telegram manually'})
        return {'status':'blocked' if any(x['status']=='blocked' for x in outcomes) else 'reconciled','operations':outcomes}
