import asyncio
import unittest
import test_routing

class MonitoringTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await test_routing.RoutingTests.asyncSetUp(self)
        async def send(*args): return '100' if args[1] is None else '201'
        self.telegram.send_text=send
        self.telegram.send_document=send
        self.telegram.self_id = self.self_id
        self.telegram.latest_message_id = self.latest
    async def asyncTearDown(self): await test_routing.RoutingTests.asyncTearDown(self)
    async def self_id(self): return 77
    async def latest(self, group): return 100
    async def event(self, message=101, **extra):
        return await self.app.handle(dict(action='telegram_event',kind='new_message',group_id=10,
            message_id=message,sender_id=77,account_id=77,text='Please #codex write greeting',**extra))
    async def test_activation_restart_and_fresh_trigger_dedup(self):
        enabled=await self.app.handle({'action':'monitor_enable'})
        self.assertEqual(enabled['status'],'monitoring',enabled)
        self.assertEqual((await self.event(99))['status'],'ignored')
        first=await self.event()
        self.assertEqual(first['status'],'admitted',first)
        self.assertEqual((await self.event())['status'],'duplicate')
        await self.app.close()
        from telegram_integration.application import Application
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        self.assertEqual((await self.event())['status'],'duplicate')
        from telegram_integration.contracts import Message
        async def trigger(group,message): return Message(group,message,'#codex greeting',topic_id=2)
        self.telegram.message=trigger
        result=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(result['status'],'finished',result)
        await self.event(102)
        followup=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual((followup['task_id'],followup['chat_id'],followup['run']),(result['task_id'],result['chat_id'],2))
        self.assertEqual(len(self.codex.created),1)
    async def test_edits_other_authors_generated_echo_and_old_messages_cannot_trigger(self):
        await self.app.handle({'action':'monitor_enable'})
        for change in ({'kind':'edit'},{'sender_id':88},{'edited':True},{'message_id':1}):
            command=dict(action='telegram_event',kind='new_message',group_id=10,message_id=101,
                         sender_id=77,account_id=77,text='#codex')
            command.update(change)
            self.assertEqual((await self.app.handle(command))['status'],'ignored')
        self.assertEqual((await self.app.handle({'action':'monitor_status'}))['requests'],[])

    async def test_admission_and_status_do_not_wait_for_worker_or_close_its_connection(self):
        from telegram_integration.contracts import Message, Context, RunResult
        async def message(group, identity): return Message(group,identity,'#codex greet',topic_id=2)
        async def context(group, identity, scope): return Context((await message(group,identity),Message(group,identity+100,'later instruction',topic_id=2)))
        self.telegram.message=message; self.telegram.context=context
        started=asyncio.Event(); finish=asyncio.Event(); prompts=[]; closed=[]
        async def run(chat,cwd,prompt,**kwargs):
            prompts.append(prompt); started.set(); await finish.wait(); return RunResult('Done','Hello','turn')
        async def close(): closed.append(True)
        self.codex.run=run; self.codex.aclose=close
        await self.app.handle({'action':'monitor_enable'})
        await self.event()
        worker=asyncio.create_task(self.app.handle({'action':'dispatch_pending'}))
        await asyncio.wait_for(started.wait(),1)
        self.assertEqual((await asyncio.wait_for(self.event(102),1))['status'],'admitted')
        status=await asyncio.wait_for(self.app.handle({'action':'monitor_status'}),1)
        self.assertEqual([r['status'] for r in status['requests']],['running','pending'])
        self.assertEqual(closed,[])
        self.assertEqual((await self.app.handle({'action':'task','destination':'project','group_id':10,'message_id':102}))['status'],'busy')
        finish.set(); self.assertEqual((await worker)['status'],'finished')
        self.assertNotIn('later instruction',prompts[0])
        self.assertEqual((await self.event(201))['reason'],'Integration-generated message')

    async def test_uncertain_send_holds_self_echo_instead_of_recursing(self):
        await self.app.handle({'action':'monitor_enable'})
        async def failed(*args): raise TimeoutError('unknown send result')
        self.telegram.send_text=failed
        # Test uncertain report on an active ready group through public task seam.
        await self.app.handle({'action':'task','destination':'project','group_id':10,'message_id':3})
        self.assertEqual((await self.event())['status'],'held')
    async def test_new_group_requires_readiness_and_removal_pauses_pending_work(self):
        groups={10}
        async def allowed(folder): return groups.copy()
        self.telegram.allowed_groups=allowed
        await self.app.handle({'action':'monitor_enable'})
        groups.add(20)
        await self.app.handle({'action':'monitor_refresh'})
        status=await self.app.handle({'action':'monitor_status'})
        self.assertEqual([(r['group_id'],r['cutoff'],r['status']) for r in status['groups']],[(10,100,'ready'),(20,100,'ready')])
        old=dict(action='telegram_event',kind='new_message',account_id=77,sender_id=77,group_id=20,message_id=99,text='#codex')
        self.assertEqual((await self.app.handle(old))['status'],'ignored')
        self.assertEqual((await self.app.handle(dict(old,message_id=101)))['status'],'admitted')
        groups.remove(20)
        await self.app.handle({'action':'monitor_refresh'})
        self.assertEqual((await self.app.handle({'action':'monitor_status'}))['requests'][0]['status'],'paused')

    async def test_listener_envelope_preserves_self_author_and_edit_evidence(self):
        from types import SimpleNamespace as NS
        from telegram_integration.listener import deliver
        await self.app.handle({'action':'monitor_enable'})
        event=NS(chat_id=10,message=NS(id=101,sender_id=77,raw_text='#codex greet',edit_date=None,fwd_from=None))
        self.assertEqual((await deliver(self.app,event,77))['status'],'admitted')
        event.message.id=102; event.message.edit_date='today'
        self.assertEqual((await deliver(self.app,event,77,'edited_message'))['status'],'ignored')
