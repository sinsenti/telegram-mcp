import asyncio
import unittest
from pathlib import Path
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
        self.assertEqual((await self.app.handle({'action':'monitor_status'}))['discovery_progress'],[{'group_id':10,'message_id':101}])
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
    async def test_existing_automatic_chat_current_placement_blocks_before_another_turn(self):
        from telegram_integration.contracts import Message
        async def trigger(group,message): return Message(group,message,'#codex greeting',topic_id=2)
        self.telegram.message=trigger
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101)
        first=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(first['status'],'finished',first)
        self.assertNotIn('membership',first)
        for index,changed in enumerate(({'project_id':'foreign'}, {'cwd':str(self.root)}, {'chat_id':'other'})):
            with self.subTest(changed=changed):
                async def observe(chat,cwd):
                    return dict(dict(chat_id=chat,cwd=str(cwd),project_id='server-help'),**changed)
                self.codex.observe_chat=observe
                await self.event(102+index)
                blocked=await self.app.handle({'action':'dispatch_pending'})
                self.assertEqual(blocked['status'],'blocked',blocked)
                self.assertEqual(len(self.codex.runs),1)
                self.assertEqual(await self.app.handle({'action':'status','task_id':first['task_id']}),first)
        async def restored(chat,cwd): return dict(chat_id=chat,cwd=str(cwd),project_id='server-help')
        self.codex.observe_chat=restored
        await self.event(110)
        continued=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual((continued['task_id'],continued['chat_id'],continued['run']),
                         (first['task_id'],first['chat_id'],2))

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
        async def context(group, identity, scope, *, upper_bound=None): return Context((await message(group,identity),)) if upper_bound is not None else Context((await message(group,identity),Message(group,identity+100,'later instruction',topic_id=2)))
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

    async def test_successful_report_releases_held_human_request_without_self_trigger(self):
        from telegram_integration.contracts import Message, Context, RunResult
        async def message(group, identity): return Message(group,identity,'#codex greet',topic_id=2)
        async def context(group, identity, scope, *, upper_bound=None): return Context((await message(group,identity),))
        self.telegram.message=message; self.telegram.context=context
        turn_started=asyncio.Event(); finish_turn=asyncio.Event()
        send_started=asyncio.Event(); finish_send=asyncio.Event(); closed=[]
        async def run(chat,cwd,prompt,**kwargs):
            self.codex.runs.append((chat,cwd)); turn_started.set()
            await finish_turn.wait()
            return RunResult('Done','Result quoting #codex','turn')
        async def close(): closed.append(True)
        self.codex.run=run; self.codex.aclose=close
        await self.app.handle({'action':'monitor_enable'})
        async def slow_send(*args):
            send_started.set(); await finish_send.wait(); return '201'
        self.telegram.send_text=slow_send
        await self.event()
        worker=asyncio.create_task(self.app.handle({'action':'dispatch_pending'}))
        try:
            await asyncio.wait_for(turn_started.wait(),1)
            finish_turn.set()
            await asyncio.wait_for(send_started.wait(),1)
            self.assertEqual((await asyncio.wait_for(self.event(102),1))['status'],'held')
            self.assertEqual((await self.event(201))['status'],'held')
            ordinary=dict(action='telegram_event',kind='new_message',group_id=10,message_id=103,
                          sender_id=77,account_id=77,text='ordinary context')
            self.assertEqual((await self.app.handle(ordinary))['status'],'held')
            self.assertEqual((await self.app.handle(dict(ordinary,message_id=104,kind='edit',text='#codex')))['status'],'ignored')
            self.assertEqual(closed,[])
            finish_send.set()
            self.assertEqual((await asyncio.wait_for(worker,1))['status'],'finished')
            status=await self.app.handle({'action':'monitor_status'})
            self.assertEqual([(r['message_id'],r['status']) for r in status['requests']],[(101,'finished'),(102,'pending')])
            self.assertEqual(status['held_events'],[])
            self.assertEqual((await self.event(102))['status'],'duplicate')
            self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'finished')
            self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'idle')
            self.assertEqual(len(self.codex.runs),2)
        finally:
            finish_turn.set(); finish_send.set()
            await worker

    async def test_uncertain_send_holds_self_echo_instead_of_recursing(self):
        await self.app.handle({'action':'monitor_enable'})
        async def failed(*args): raise TimeoutError('unknown send result')
        self.telegram.send_text=failed
        # Test uncertain report on an active ready group through public task seam.
        await self.app.handle({'action':'task','destination':'project','group_id':10,'message_id':3})
        self.assertEqual((await self.event())['status'],'held')
        # A later confirmed send does not resolve the earlier unknown outcome.
        async def success(*args): return '202'
        self.telegram.send_text=success
        await self.app.handle({'action':'task','destination':'project','group_id':10,'message_id':3})
        status=await self.app.handle({'action':'monitor_status'})
        self.assertEqual(status['requests'],[])
        self.assertEqual([r['message_id'] for r in status['held_events']],[101])
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
    async def test_fresh_human_link_commands_share_project_binding_and_generated_exclusion(self):
        from telegram_integration.contracts import Message
        async def listing(project_id,cwd):
            return [{'chat_id':'existing','title':'Existing #codex work','project_id':'server-help','cwd':str(cwd)}]
        self.codex.list_chats=listing
        texts={101:'#link',102:'1',103:'#codex greet'}
        async def message(group,identity): return Message(group,identity,texts.get(identity,'#codex generated'),topic_id=2)
        self.telegram.message=message
        await self.app.handle({'action':'monitor_enable'})
        choices=await self.app.handle(dict(action='telegram_event',kind='new_message',account_id=77,sender_id=77,group_id=10,message_id=101,text='#link'))
        self.assertEqual(choices['status'],'chat_choice',choices)
        self.assertEqual((await self.event(201))['reason'],'Integration-generated message')
        linked=await self.app.handle(dict(action='telegram_event',kind='new_message',account_id=77,sender_id=77,group_id=10,message_id=102,text='1'))
        self.assertEqual(linked['status'],'linked',linked)
        await self.event(103)
        result=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual((result['status'],result['chat_id']),('finished','existing'))
        self.assertEqual(self.codex.created,[])

    async def test_reference_identity_is_excluded_even_when_title_quotes_marker(self):
        # External metadata/Telegram fixture; real Application, store and files remain in use.
        self.title='Research #codex notes'; self.topic='New chat'; self.references={}; self.pinned=False; self.writes=[]
        async def observe(chat,cwd): return dict(chat_id=chat,cwd=str(cwd),project_id='server-help',name=self.title)
        async def topic(group,identity): return self.topic
        async def rename(group,identity,title): self.topic=title
        send_started=asyncio.Event(); finish_send=asyncio.Event()
        async def create(group,identity,text):
            send_started.set(); await finish_send.wait()
            self.references['203']=text; return '203'
        async def reference(group,topic,identity): return dict(text=self.references[identity],pinned=self.pinned)
        async def pin(group,topic,identity): self.pinned=True
        self.codex.observe_chat=observe; self.telegram.topic_title=topic; self.telegram.rename_topic=rename
        self.telegram.create_reference=create; self.telegram.reference=reference; self.telegram.pin_reference=pin
        await self.app.handle({'action':'monitor_enable'})
        task=await self.app.handle(dict(action='task',destination='project',group_id=10,message_id=3))
        worker=asyncio.create_task(self.app.handle(dict(action='sync_reference',task_id=task['task_id'])))
        try:
            await asyncio.wait_for(send_started.wait(),1)
            self.assertEqual((await asyncio.wait_for(self.event(102),1))['status'],'held')
            self.assertEqual((await self.event(203))['status'],'held')
        finally:
            finish_send.set()
            result=await asyncio.wait_for(worker,1)
        status=await self.app.handle({'action':'monitor_status'})
        self.assertEqual([(r['message_id'],r['status']) for r in status['requests']],[(102,'pending')])
        self.assertEqual(status['held_events'],[])
        self.assertEqual((await self.event(102))['status'],'duplicate')
        self.assertEqual(result['reference_sync']['reference']['message_id'],'203')
        self.assertEqual((await self.event(203))['reason'],'Integration-generated message')

    async def test_reconciliation_releases_human_once_and_excludes_early_generated_echo(self):
        from telegram_integration.application import Application
        from telegram_integration.contracts import Message, Context, RunResult
        async def message(group,identity): return Message(group,identity,'#codex greeting',topic_id=2)
        async def context(group,identity,scope,*,upper_bound=None): return Context((await message(group,identity),))
        self.telegram.message=message; self.telegram.context=context
        async def run(*args,**kwargs):
            self.codex.runs.append(args)
            return RunResult('Result quoting #codex','Document','turn')
        self.codex.run=run
        await self.app.handle({'action':'monitor_enable'})
        remote={}; lose=True
        async def send(group,source,text,topic,*,random_id=None):
            nonlocal lose
            remote.setdefault(random_id,'201')
            if lose:
                self.assertEqual((await self.event(201))['status'],'held')
                self.assertEqual((await self.event(102))['status'],'held')
                lose=False
                raise TimeoutError('remote success with lost ack')
            return remote[random_id]
        self.telegram.send_text=send
        await self.event(101)
        first=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(first['status'],'blocked')
        self.assertIn('task_id',first,first)
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        result=await self.app.handle({'action':'reconcile_reports','task_id':first['task_id']})
        self.assertEqual(result['status'],'finished')
        status=await self.app.handle({'action':'monitor_status'})
        self.assertEqual([r['message_id'] for r in status['requests']],[101,102])
        self.assertEqual(status['requests'][0]['status'],'finished')
        self.assertEqual(status['requests'][0]['outcome']['status'],'finished')
        self.assertEqual(status['held_events'],[])
        self.assertEqual((await self.event(102))['status'],'duplicate')
        self.assertEqual((await self.event(201))['status'],'ignored')
        self.assertEqual(len(remote),1)
        self.assertEqual(len(self.codex.runs),1)

    async def test_report_recovery_updates_only_current_blocked_request(self):
        from telegram_integration.contracts import Message
        async def message(group,identity): return Message(group,identity,'#codex greeting',topic_id=2)
        self.telegram.message=message
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101)
        first=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(first['status'],'finished',first)
        historical=(await self.app.handle({'action':'monitor_status'}))['requests'][0]
        lose=True
        async def send(group,source,text,topic,*,random_id=None):
            nonlocal lose
            if lose:
                lose=False
                raise TimeoutError('text delivered with acknowledgment lost')
            return '205'
        self.telegram.send_text=send
        await self.event(102)
        second=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual((second['status'],second['task_id'],second['run']),('blocked',first['task_id'],2))
        recovered=await self.app.handle({'action':'reconcile_reports','task_id':second['task_id']})
        self.assertEqual(recovered['status'],'finished',recovered)
        requests=(await self.app.handle({'action':'monitor_status'}))['requests']
        self.assertEqual(requests[0],historical)
        self.assertEqual((requests[1]['status'],requests[1]['outcome']['run']),('finished',2))
        self.assertEqual(len(self.codex.runs),2)

    async def test_lost_readiness_ack_preserves_cutoff_and_later_human_request(self):
        from telegram_integration.application import Application
        remote={}; lose=True
        async def send(group,message,text,topic,*,random_id=None):
            nonlocal lose
            remote.setdefault(random_id,'101')
            if lose:
                lose=False
                raise TimeoutError('ready was delivered; response lost')
            return remote[random_id]
        self.telegram.send_text=send
        self.assertEqual((await self.app.handle({'action':'monitor_enable'}))['status'],'blocked')
        self.assertEqual((await self.event(102))['status'],'held')
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        result=await self.app.handle({'action':'monitor_refresh'})
        self.assertEqual(result['groups'],[{'group_id':10,'cutoff':101,'status':'ready'}])
        result=await self.app.handle({'action':'monitor_status'})
        self.assertEqual([r['message_id'] for r in result['requests']],[102])
        self.assertEqual(len(remote),1)
    async def test_shared_state_worker_and_manual_execution_are_globally_busy(self):
        from telegram_integration.application import Application
        from telegram_integration.contracts import Message, RunResult
        async def trigger(group,message): return Message(group,message,'#codex greet',topic_id=2)
        self.telegram.message=trigger
        started=asyncio.Event(); finish=asyncio.Event()
        async def run(*args,**kwargs):
            started.set(); await finish.wait(); return RunResult('Done','Hello','turn')
        self.codex.run=run
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101); await self.event(102)
        other=Application(self.root/'db',self.root/'tasks',self.telegram,test_routing.Codex(),catalog=self.catalog)
        worker=asyncio.create_task(self.app.handle({'action':'dispatch_pending'}))
        try:
            await asyncio.wait_for(started.wait(),1)
            self.assertEqual((await asyncio.wait_for(other.handle({'action':'dispatch_pending'}),1))['status'],'busy')
            self.assertEqual((await other.handle(dict(action='task',destination='project',group_id=10,message_id=103)))['status'],'busy')
            self.assertEqual((await other.handle({'action':'monitor_status'}))['requests'][1]['status'],'pending')
            self.assertEqual((await other.handle(dict(action='telegram_event',kind='new_message',group_id=10,message_id=103,sender_id=77,account_id=77,text='#codex')))['status'],'admitted')
        finally:
            finish.set(); await worker; await other.close()

    async def test_deleted_trigger_cancels_but_unavailable_trigger_blocks(self):
        from telegram_integration.contracts import MissingMessage
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101); await self.event(102)
        async def unavailable(group,message):
            if message==101: raise MissingMessage('Message was deleted')
            raise ConnectionError('Telegram offline')
        self.telegram.message=unavailable
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'cancelled')
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'blocked')
        self.assertEqual([r['status'] for r in (await self.app.handle({'action':'monitor_status'}))['requests']],['cancelled','blocked'])
        self.assertEqual(self.codex.created,[])

    async def test_queue_reads_current_bounded_inputs_once_then_continues_same_chat_after_restart(self):
        from telegram_integration.contracts import Message, Context, RunResult
        from telegram_integration.application import Application
        texts={100:'draft preparation',101:'#codex first',102:'#codex second',103:'future reply'}
        bounds=[]; prompts=[]; started=asyncio.Event(); finish=asyncio.Event()
        async def message(group,identity): return Message(group,identity,texts[identity],topic_id=2)
        async def context(group,identity,scope,*,upper_bound=None):
            bounds.append(upper_bound)
            return Context(tuple([await message(group,k) for k in sorted(texts) if upper_bound is None or k<=upper_bound]))
        async def run(chat,cwd,prompt,**kwargs):
            prompts.append(prompt); started.set(); await finish.wait(); return RunResult('Done','Hello','turn')
        self.telegram.message=message; self.telegram.context=context; self.codex.run=run
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101); await self.event(102)
        texts[100]='corrected before execution'
        worker=asyncio.create_task(self.app.handle({'action':'dispatch_pending'}))
        try:
            await asyncio.wait_for(started.wait(),1)
            texts[100]='edited while first runs'
        finally:
            finish.set(); first=await worker
        self.assertEqual(first['status'],'finished',first)
        self.assertIn('corrected before execution',prompts[0])
        self.assertNotIn('#codex second',prompts[0]); self.assertNotIn('future reply',prompts[0])
        self.assertNotIn('edited while first runs',prompts[0])
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        second=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual((second['task_id'],second['chat_id'],second['run']),(first['task_id'],first['chat_id'],2))
        self.assertEqual(bounds,[101,102])
        self.assertIn('edited while first runs',prompts[1]); self.assertIn('#codex second',prompts[1])
        self.assertNotIn('future reply',prompts[1])
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'idle')

    async def test_withdrawn_marker_and_incomplete_required_context_never_start_codex(self):
        from telegram_integration.contracts import Message, Context
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101); await self.event(102)
        async def message(group,identity): return Message(group,identity,'Withdrawn' if identity==101 else '#codex work',topic_id=2)
        async def context(group,identity,scope,*,upper_bound=None):
            return Context((await message(group,identity),),False,'required reply unavailable')
        self.telegram.message=message; self.telegram.context=context
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'cancelled')
        blocked=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual(blocked['status'],'blocked'); self.assertIn('required reply unavailable',blocked['reason'])
        self.assertEqual(self.codex.created,[])

    async def test_another_process_owns_execution_and_crash_releases_ownership(self):
        import sys
        from telegram_integration.contracts import Message
        async def message(group,identity): return Message(group,identity,'#codex greeting',topic_id=2)
        self.telegram.message=message
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101); await self.event(102)
        script="""
import asyncio, sys
from pathlib import Path
sys.path.insert(0,'tests')
from test_routing import Telegram,Codex,Catalog
from telegram_integration.application import Application
from telegram_integration.contracts import Message
async def main():
    root=Path(sys.argv[1]); telegram=Telegram(); codex=Codex()
    async def message(group,identity): return Message(group,identity,'#codex greeting',topic_id=2)
    async def run(*args,**kwargs):
        print('RUNNING',flush=True)
        await asyncio.Event().wait()
    telegram.message=message; codex.run=run
    app=Application(root/'db',root/'tasks',telegram,codex,catalog=Catalog(root/'real'))
    await app.handle({'action':'dispatch_pending'})
asyncio.run(main())
"""
        child=await asyncio.create_subprocess_exec(sys.executable,'-c',script,str(self.root),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        try:
            self.assertEqual(await asyncio.wait_for(child.stdout.readline(),5),b'RUNNING\n')
            self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'busy')
            request=(await self.app.handle({'action':'monitor_status'}))['requests'][0]
            self.assertIsNotNone(request['task_id'])
            task=await self.app.handle({'action':'status','task_id':request['task_id']})
            self.assertEqual(task['phase'],'executing')
        finally:
            child.kill(); await child.communicate()
        # No blind rerun of the crashed request, and no stale ownership lock.
        status=await self.app.handle({'action':'monitor_status'})
        self.assertEqual([r['status'] for r in status['requests']],['running','pending'])
        result=await self.app.handle({'action':'dispatch_pending'})
        self.assertNotEqual(result['status'],'busy')

    async def test_unknown_codex_outcome_retains_task_binding_and_blocks_later_execution(self):
        from telegram_integration.contracts import Message
        async def message(group,identity): return Message(group,identity,'#codex greeting',topic_id=2)
        async def run(*args,**kwargs): raise ConnectionError('lost Codex connection after start')
        self.telegram.message=message; self.codex.run=run
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101); await self.event(102)
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'blocked')
        requests=(await self.app.handle({'action':'monitor_status'}))['requests']
        self.assertEqual([request['status'] for request in requests],['uncertain','pending'])
        task=await self.app.handle({'action':'status','task_id':requests[0]['task_id']})
        self.assertEqual(task['phase'],'executing')
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'blocked')
        self.assertEqual((await self.app.handle(dict(action='task',destination='project',group_id=10,message_id=103)))['status'],'blocked')
        self.assertEqual(len(self.codex.created),1)

    async def test_removal_during_execution_keeps_result_paused_and_readd_needs_fresh_request(self):
        from telegram_integration.application import Application
        from telegram_integration.contracts import Message, RunResult
        groups={10}; started=asyncio.Event(); finish=asyncio.Event()
        async def allowed(folder): return groups.copy()
        async def message(group,identity): return Message(group,identity,'#codex greeting',topic_id=2)
        async def run(*args,**kwargs):
            if kwargs.get('on_turn_accepted'): await kwargs['on_turn_accepted']('active-turn')
            started.set(); await finish.wait(); return RunResult('Done','Preserved result','active-turn')
        self.telegram.allowed_groups=allowed; self.telegram.message=message; self.codex.run=run
        await self.app.handle({'action':'monitor_enable'})
        await self.event(101); await self.event(102)
        worker=asyncio.create_task(self.app.handle({'action':'dispatch_pending'}))
        try:
            await asyncio.wait_for(started.wait(),1)
            groups.clear()
            removed=await asyncio.wait_for(self.app.handle({'action':'folder_changed'}),1)
            self.assertEqual([r['status'] for r in removed['requests']],['paused','paused'])
        finally:
            finish.set(); result=await worker
        self.assertEqual(result['status'],'paused',result)
        self.assertEqual(Path(result['document']).read_text(),'Preserved result')
        self.assertEqual(result.get('report_ids',[]),[])
        await self.app.close()
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        groups.add(10)
        await self.app.handle({'action':'monitor_refresh'})
        self.assertEqual((await self.app.handle({'action':'dispatch_pending'}))['status'],'idle')
        await self.event(103)
        continued=await self.app.handle({'action':'dispatch_pending'})
        self.assertEqual((continued['status'],continued['chat_id']),('finished',result['chat_id']),continued)
