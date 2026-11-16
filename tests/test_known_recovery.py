"""Restart policy exercised only through Application and external adapters."""
import unittest
import tempfile
from pathlib import Path
from telegram_integration.application import Application
from tests.test_report_recovery import DurableTelegram
from tests.test_application import Codex

class KnownRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.telegram=DurableTelegram(); self.codex=Codex()
        self.app=self.construct()
        await self.app.handle({'action':'configure','folder_id':7})
    def construct(self):
        return Application(self.root/'db',self.root/'tasks',self.telegram,self.codex)
    async def restart(self):
        await self.app.close(); self.app=self.construct()
    async def asyncTearDown(self):
        await self.app.close(); self.tmp.cleanup()
    async def test_completed_reports_recover_once_to_original_source(self):
        first=await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        self.assertEqual(first['phase'],'reporting',first)
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'finished',result)
        self.assertEqual(result['tasks'][0]['task_id'],first['task_id'])
        self.assertEqual([(v[1],v[2]) for v in self.telegram.remote.values()],[('text',42),('document',42)])
        self.assertEqual(len(self.codex.runs),1)
        await self.restart()
        await self.app.handle({'action':'recover'})
        self.assertEqual(len(self.telegram.remote),2)
        self.assertEqual(len(self.codex.runs),1)

    async def test_completed_execution_is_saved_before_placement_and_recovered_without_run(self):
        import asyncio
        from tests.test_routing import Telegram, Codex, Catalog
        await self.app.close()
        project=self.root/'project'; project.mkdir()
        self.telegram=Telegram(); self.codex=Codex(); self.catalog=Catalog(project)
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        async def crash(chat,cwd): raise asyncio.CancelledError()
        self.codex.observe_chat=crash
        with self.assertRaises(asyncio.CancelledError):
            await self.app.handle(dict(action='task',destination='project',group_id=10,message_id=42))
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        async def observe(chat,cwd): return dict(chat_id=chat,cwd=str(cwd),project_id='server-help')
        self.codex.observe_chat=observe
        recovered=await self.app.handle({'action':'recover'})
        self.assertEqual(recovered['tasks'][0]['status'],'finished',recovered)
        self.assertEqual(len(self.codex.runs),1)

    async def test_known_turn_observation_recovers_result_without_starting_again(self):
        from types import SimpleNamespace
        from telegram_integration.contracts import RunResult
        async def lost(chat,cwd,prompt,**kwargs):
            callback=kwargs.get('on_turn_accepted')
            if callback: await callback('known-turn')
            self.codex.runs.append((chat,cwd,prompt))
            raise ConnectionError('execution connection lost')
        self.codex.run=lost
        first=await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        self.assertEqual(first['phase'],'executing',first)
        observed=[]
        async def observe(chat,cwd,turn):
            observed.append((chat,turn))
            return SimpleNamespace(turn_id=turn,status='completed',result=RunResult('Recovered','Original output',turn),reason=None)
        self.codex.observe_turn=observe
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'finished',result)
        self.assertEqual(observed,[('chat-actual-123','known-turn')])
        self.assertEqual(len(self.codex.runs),1)

    async def test_captured_snapshot_continues_without_recapturing_edited_source(self):
        import asyncio
        crash=True
        self.telegram.lose=None
        async def allowed(folder):
            if crash and list((self.root/'tasks').glob('*/inputs-1.json')):
                raise asyncio.CancelledError()
            return {10}
        self.telegram.allowed_groups=allowed
        with self.assertRaises(asyncio.CancelledError):
            await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        crash=False
        async def edited(*args,**kwargs): raise AssertionError('Recovery must use fixed context, never refetch source')
        self.telegram.context=edited
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'finished',result)
        self.assertIn('Write a greeting',self.codex.runs[0][2])
        self.assertEqual(len(self.codex.chats),1)
        self.assertTrue((Path(result['tasks'][0]['folder'])/'context-1.json').is_file())

    async def test_lost_start_ack_uses_exact_correlation_and_never_replays_start(self):
        from types import SimpleNamespace
        from telegram_integration.contracts import RunResult
        remote={}
        async def lost(chat,cwd,prompt,**kwargs):
            remote[kwargs['client_request_id']]=(chat,cwd)
            raise ConnectionError('accepted remotely, response lost')
        self.codex.run=lost
        first=await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        async def find(chat,cwd,correlation):
            self.assertEqual(remote[correlation],(chat,cwd))
            return SimpleNamespace(turn_id='remote-turn',status='completed',result=RunResult('Found','Saved output','remote-turn'),reason=None)
        self.codex.find_turn=find
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'finished',result)
        self.assertEqual(len(remote),1)
        self.assertEqual(result['tasks'][0]['chat_id'],first['chat_id'])

    async def test_lost_create_ack_keeps_blocker_without_creating_replacement(self):
        created=[]
        async def lost(cwd):
            created.append(cwd)
            raise ConnectionError('chat created, response lost')
        self.codex.create_chat=lost
        first=await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'blocked',result)
        self.assertEqual(result['tasks'][0]['phase'],'creating_chat')
        self.assertEqual(result['tasks'][0]['codex_create_intent'],first['codex_create_intent'])
        self.assertEqual(len(created),1)

    async def test_completed_malformed_result_remains_terminal_after_repeated_restart(self):
        from types import SimpleNamespace
        async def lost(chat,cwd,prompt,**kwargs):
            await kwargs['on_turn_accepted']('known-turn')
            self.codex.runs.append((chat,cwd,prompt))
            raise ConnectionError('lost')
        self.codex.run=lost
        first=await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        async def observe(*args): return SimpleNamespace(turn_id='known-turn',status='completed',result=None,reason='Malformed final output')
        self.codex.observe_turn=observe
        for _ in range(2):
            await self.restart()
            result=await self.app.handle({'action':'recover'})
            self.assertEqual(result['tasks'][0]['status'],'blocked',result)
            self.assertEqual(result['tasks'][0]['phase'],'terminal_result')
        self.assertEqual(len(self.codex.runs),1)

    async def test_recovery_cannot_observe_or_start_while_another_instance_owns_worker(self):
        import asyncio
        started=asyncio.Event(); finish=asyncio.Event()
        async def run(chat,cwd,prompt,**kwargs):
            await kwargs['on_turn_accepted']('owned-turn')
            started.set(); await finish.wait()
            from telegram_integration.contracts import RunResult
            return RunResult('Done','Output','owned-turn')
        self.codex.run=run; self.telegram.lose=None
        worker=asyncio.create_task(self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42)))
        await asyncio.wait_for(started.wait(),2)
        other=self.construct()
        try:
            self.assertEqual((await other.handle({'action':'recover'}))['status'],'busy')
            self.assertEqual((await self.app.handle({'action':'recover'}))['status'],'busy')
        finally:
            finish.set(); await worker; await other.close()

    async def observed_terminal_case(self, remote_status):
        from types import SimpleNamespace
        async def lost(chat,cwd,prompt,**kwargs):
            await kwargs['on_turn_accepted']('known-'+remote_status)
            self.codex.runs.append((chat,cwd,prompt))
            raise ConnectionError('lost')
        self.codex.run=lost
        first=await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        async def observe(chat,cwd,turn):
            return SimpleNamespace(turn_id=turn,status=remote_status,result=None,reason='Observed '+remote_status)
        self.codex.observe_turn=observe
        await self.restart()
        before=len(self.codex.runs)
        result=await self.app.handle({'action':'recover','task_id':first['task_id']})
        task=result['tasks'][0]
        self.assertEqual(task['status'],'blocked',task)
        self.assertEqual(len(self.codex.runs),before)
        self.assertEqual(task['phase'],'terminal_'+remote_status if remote_status in ('interrupted','failed') else 'executing')
    async def test_running_turn_does_not_restart(self): await self.observed_terminal_case('inProgress')
    async def test_interrupted_turn_does_not_restart(self): await self.observed_terminal_case('interrupted')
    async def test_failed_turn_does_not_restart(self): await self.observed_terminal_case('failed')
    async def test_unknown_turn_does_not_restart(self): await self.observed_terminal_case('unknown')

    async def test_queue_order_and_task_binding_survive_worker_crash_and_recovery(self):
        import asyncio
        from types import SimpleNamespace
        from tests.test_routing import Telegram, Codex, Catalog
        from telegram_integration.contracts import Message, Context, RunResult
        await self.app.close()
        project=self.root/'project'; project.mkdir()
        self.telegram=Telegram(); self.codex=Codex(); self.catalog=Catalog(project)
        async def account(): return 77
        async def latest(group): return 100
        async def message(group,identity): return Message(group,identity,'#codex request '+str(identity),topic_id=2)
        async def context(group,identity,scope,*,upper_bound=None): return Context((await message(group,identity),))
        self.telegram.self_id=account; self.telegram.latest_message_id=latest
        self.telegram.message=message; self.telegram.context=context
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        await self.app.handle({'action':'monitor_enable'})
        for identity in (101,102):
            await self.app.handle(dict(action='telegram_event',kind='new_message',group_id=10,message_id=identity,
                account_id=77,sender_id=77,text='#codex request '+str(identity)))
        normal_run=self.codex.run
        async def crash(chat,cwd,prompt,**kwargs):
            await kwargs['on_turn_accepted']('first-turn')
            self.codex.runs.append((chat,cwd)); raise asyncio.CancelledError()
        self.codex.run=crash
        with self.assertRaises(asyncio.CancelledError): await self.app.handle({'action':'dispatch_pending'})
        before=(await self.app.handle({'action':'monitor_status'}))['requests']
        self.assertEqual([r['status'] for r in before],['running','pending'])
        task=await self.app.handle({'action':'status','task_id':before[0]['task_id']})
        original=(Path(task['folder'])/'context-1.json').read_bytes()
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        async def observe(chat,cwd,turn): return SimpleNamespace(turn_id=turn,status='completed',result=RunResult('Recovered','First result',turn),reason=None)
        self.codex.observe_turn=observe; self.codex.run=normal_run
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'finished',result)
        after=(await self.app.handle({'action':'monitor_status'}))['requests']
        self.assertEqual([r['status'] for r in after],['finished','pending'])
        self.assertEqual([r['sequence'] for r in after],[r['sequence'] for r in before])
        self.assertEqual((Path(task['folder'])/'context-1.json').read_bytes(),original)
        second=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual((second['task_id'],second['chat_id'],second['run']),(task['task_id'],task['chat_id'],2))
        self.assertEqual(len(self.codex.created),1)
        self.assertEqual(len(self.codex.runs),2)

    async def test_paused_known_turn_can_be_observed_without_reporting_or_resuming(self):
        from types import SimpleNamespace
        from telegram_integration.contracts import RunResult
        async def lost(chat,cwd,prompt,**kwargs):
            await kwargs['on_turn_accepted']('paused-turn')
            self.codex.runs.append((chat,cwd,prompt))
            raise ConnectionError('completion connection lost')
        self.codex.run=lost
        first=await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        self.telegram.allowed.clear()
        await self.app.handle(dict(action='read',group_id=10,message_id=42))
        paused=await self.app.handle({'action':'status','task_id':first['task_id']})
        self.assertEqual(paused['status'],'paused',paused)
        before=dict(self.telegram.remote)
        async def observe(chat,cwd,turn):
            return SimpleNamespace(turn_id=turn,status='completed',result=RunResult('Recovered','Paused output',turn),reason=None)
        self.codex.observe_turn=observe
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        task=result['tasks'][0]
        self.assertEqual((task['status'],task['phase']),('paused','terminal_result'),task)
        self.assertEqual(self.telegram.remote,before)
        self.assertEqual(len(self.codex.runs),1)
        self.assertTrue((Path(task['folder'])/'run-result-1.json').is_file())
        self.telegram.allowed.add(10)
        await self.app.handle({'action':'recover'})
        self.assertEqual((await self.app.handle({'action':'status','task_id':task['task_id']}))['status'],'paused')
        self.assertEqual(self.telegram.remote,before)

    async def test_captured_attachment_retains_original_file_and_evidence_after_restart(self):
        import asyncio
        from telegram_integration.contracts import Attachment, Context, Message, RunResult, InputEvidence
        self.telegram.lose=None
        async def context(group,identity,scope):
            return Context((Message(group,identity,'Read preserved code',True,2,attachment=Attachment('input','note.txt')),))
        async def download(group,identity,attachment,stream): stream.write(b'Original code: 739')
        self.telegram.context=context; self.telegram.download=download
        crash=True
        async def allowed(folder):
            if crash and list((self.root/'tasks').glob('*/inputs-1.json')): raise asyncio.CancelledError()
            return {10}
        self.telegram.allowed_groups=allowed
        with self.assertRaises(asyncio.CancelledError):
            await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        original=next((self.root/'tasks').glob('*/inputs/1/0/original.txt'))
        original_bytes=original.read_bytes()
        crash=False
        async def no_download(*args): raise AssertionError('Captured originals must not be downloaded again')
        self.telegram.download=no_download
        async def run(chat,cwd,prompt,inputs=(),**kwargs):
            await kwargs['on_turn_accepted']('attachment-turn')
            self.assertEqual((inputs[0].path,Path(inputs[0].path).read_bytes()),(str(original),b'Original code: 739'))
            self.codex.runs.append((chat,cwd,prompt))
            return RunResult('Read code','Code 739','attachment-turn',(InputEvidence(inputs[0].input_id,'interpreted','Line 1: Original code: 739'),))
        self.codex.run=run
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'finished',result)
        self.assertEqual(original.read_bytes(),original_bytes)
        self.assertEqual(result['tasks'][0]['input_evidence'][0]['evidence'],'Line 1: Original code: 739')
        self.assertEqual(len(self.codex.runs),1)

    async def test_known_created_chat_continues_snapshot_without_creating_replacement(self):
        import asyncio
        self.telegram.lose=None
        create=self.codex.create_chat; known=False; crash=True
        async def created(cwd):
            nonlocal known
            identity=await create(cwd); known=True; return identity
        async def allowed(folder):
            if known and crash: raise asyncio.CancelledError()
            return {10}
        self.codex.create_chat=created; self.telegram.allowed_groups=allowed
        with self.assertRaises(asyncio.CancelledError):
            await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        crash=False
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'finished',result)
        self.assertEqual(result['tasks'][0]['chat_id'],'chat-actual-123')
        self.assertEqual(len(self.codex.chats),1)
        self.assertEqual(len(self.codex.runs),1)

    async def test_observed_terminal_result_is_retained_when_original_temporarily_changed(self):
        from types import SimpleNamespace
        from telegram_integration.contracts import Attachment, Context, Message, RunResult, InputEvidence
        async def context(group,identity,scope):
            return Context((Message(group,identity,'Read original',True,2,attachment=Attachment('input','note.txt')),))
        async def download(group,identity,attachment,stream): stream.write(b'Original code: 739')
        self.telegram.context=context; self.telegram.download=download
        saved={}
        async def lost(chat,cwd,prompt,inputs=(),**kwargs):
            await kwargs['on_turn_accepted']('changed-input-turn')
            saved['path']=Path(inputs[0].path)
            saved['path'].write_bytes(b'Changed locally')
            saved['result']=RunResult('Read code','Code 739','changed-input-turn',(InputEvidence(inputs[0].input_id,'interpreted','Line 1: code 739'),))
            self.codex.runs.append((chat,cwd,prompt))
            raise ConnectionError('completion connection lost')
        self.codex.run=lost
        first=await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        async def observe(chat,cwd,turn): return SimpleNamespace(turn_id=turn,status='completed',result=saved['result'],reason=None)
        self.codex.observe_turn=observe
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'blocked',result)
        saved['path'].write_bytes(b'Original code: 739')
        await self.restart()
        result=await self.app.handle({'action':'recover'})
        self.assertEqual(result['tasks'][0]['status'],'finished',result)
        self.assertEqual(len(self.codex.runs),1)

    async def test_listener_startup_recovers_saved_result_before_dispatch_worker(self):
        from telegram_integration.listener import listen
        first=await self.app.handle(dict(action='task',destination='test',group_id=10,message_id=42))
        self.assertEqual(first['phase'],'reporting',first)
        await self.restart()
        async def account(): return 77
        async def latest(group): return 100
        async def history(group,after,limit): return []
        self.telegram.self_id=account; self.telegram.latest_message_id=latest; self.telegram.history_page=history
        class Client:
            def add_event_handler(self,*args): pass
            def remove_event_handler(self,*args): pass
            async def catch_up(self): pass
            async def run_until_disconnected(self): pass
        await listen(self.app,Client())
        task=await self.app.handle({'action':'status','task_id':first['task_id']})
        self.assertEqual(task['status'],'finished',task)
        self.assertEqual(len(self.codex.runs),1)
        self.assertEqual([(v[1],v[2]) for v in self.telegram.remote.values() if v[2]==42],[('text',42),('document',42)])
