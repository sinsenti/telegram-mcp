import unittest
import test_monitoring
from telegram_integration.application import Application
from telegram_integration.contracts import Context, Message


class MonitoringBlockerTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_monitoring.MonitoringTests.asyncSetUp
    asyncTearDown = test_monitoring.MonitoringTests.asyncTearDown
    self_id = test_monitoring.MonitoringTests.self_id
    latest = test_monitoring.MonitoringTests.latest
    event = test_monitoring.MonitoringTests.event

    async def test_project_choice_is_returned_to_source_once_and_generated_echo_never_triggers(self):
        sent=[]
        async def send(group, source, text, topic, *, random_id=None):
            sent.append((group,source,text,topic,random_id))
            return '100' if source is None else '202'
        self.telegram.send_text=send
        async def message(group, identity): return Message(group,identity,'#codex greeting',topic_id=2)
        self.telegram.message=message
        self.telegram.name='unmatched'
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101)
        outcome=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(outcome['status'],'project_choice',outcome)
        self.assertEqual(len(sent),2)
        self.assertEqual((sent[-1][0],sent[-1][1],sent[-1][3]),(10,101,2))
        self.assertIn('1. help',sent[-1][2])
        self.assertIn(outcome['choice_id'],sent[-1][2])
        self.assertEqual((await self.event(202))['reason'],'Integration-generated message')
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'idle')
        self.assertEqual(len(sent),2)
        self.assertEqual(self.codex.created,[])

    async def test_missing_context_blocker_lost_ack_reconciles_after_restart_without_duplicate(self):
        remote={}; attempts=[]; lose=True
        async def send(group,source,text,topic,*,random_id=None):
            nonlocal lose
            if source is None: return '100'
            attempts.append(random_id)
            remote.setdefault(random_id,(group,source,text,topic,'203'))
            if lose:
                lose=False
                self.assertEqual((await self.event(203))['status'],'held')
                raise TimeoutError('reply accepted but response lost')
            return remote[random_id][-1]
        self.telegram.send_text=send
        async def message(group, identity): return Message(group,identity,'#codex greeting',topic_id=2)
        async def context(group,identity,scope,*,upper_bound=None):
            return Context((await message(group,identity),),False,'required reply unavailable')
        self.telegram.message=message; self.telegram.context=context
        await self.app.handle({'action':'monitor_enable'}); await self.event(101)
        outcome=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(outcome['status'],'blocked',outcome)
        self.assertEqual(len(remote),1)
        self.assertIn('required reply unavailable',next(iter(remote.values()))[2])
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        recovered=await self.app.handle({'action':'reconcile_reports'})
        self.assertEqual(recovered['status'],'reconciled',recovered)
        self.assertEqual(len(remote),1)
        self.assertEqual(attempts,[attempts[0]]*2)
        self.assertEqual((await self.event(203))['reason'],'Integration-generated message')
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'idle')
        self.assertEqual(self.codex.created,[])

    async def test_restart_delivers_saved_blocker_before_outgoing_identity_was_allocated(self):
        import asyncio
        sent=[]; prepared=asyncio.Event()
        async def send(group,source,text,topic,*,random_id=None):
            sent.append((source,text))
            return '100' if source is None else '203'
        self.telegram.send_text=send
        async def message(group, identity): return Message(group,identity,'#codex greeting',topic_id=2)
        self.telegram.message=message; self.telegram.name='unmatched'
        await self.app.handle({'action':'monitor_enable'}); await self.event(101)
        async def waiting_identity():
            prepared.set(); await asyncio.Event().wait()
        self.telegram.self_id=waiting_identity
        worker=asyncio.create_task(self.app.handle({'action':'dispatch_pending'}))
        await asyncio.wait_for(prepared.wait(),1)
        worker.cancel()
        with self.assertRaises(asyncio.CancelledError): await worker
        await self.app.close()
        self.telegram.self_id=self.self_id
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(len(sent),2)
        self.assertEqual(sent[-1][0],101)
        self.assertIn('1. help',sent[-1][1])
        await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(len(sent),2)

    async def test_revoked_blocker_delivery_stays_paused_after_group_returns(self):
        groups={10}; attempts=[]
        async def allowed(folder): return groups.copy()
        async def send(group,source,text,topic,*,random_id=None):
            if source is None: return '100'
            attempts.append(random_id)
            raise TimeoutError('reply outcome unresolved')
        async def message(group, identity): return Message(group,identity,'#codex greeting',topic_id=2)
        self.telegram.allowed_groups=allowed; self.telegram.send_text=send
        self.telegram.message=message; self.telegram.name='unmatched'
        await self.app.handle({'action':'monitor_enable'}); await self.event(101)
        await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(len(attempts),1)
        groups.clear(); await self.app.handle({'action':'folder_changed'})
        groups.add(10); await self.app.handle({'action':'monitor_refresh'})
        replay=await self.app.handle({'action':'reconcile_reports'})
        self.assertEqual(replay['status'],'paused',replay)
        await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(len(attempts),1)
        self.assertEqual((await self.app.handle({'action':'monitor_status'}))['requests'][0]['status'],'paused')
