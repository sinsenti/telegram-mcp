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
