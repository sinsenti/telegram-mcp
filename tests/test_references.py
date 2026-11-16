import unittest
import test_routing

class ReferenceTests(unittest.IsolatedAsyncioTestCase):
    task = test_routing.RoutingTests.task
    asyncTearDown = test_routing.RoutingTests.asyncTearDown
    async def asyncSetUp(self):
        await test_routing.RoutingTests.asyncSetUp(self)
        self.title = None
        self.topic = 'New chat'
        self.references = {}
        self.pinned = False
        self.writes = []
        async def observe(chat, cwd):
            return {'chat_id':chat,'cwd':str(cwd),'project_id':'server-help','name':self.title}
        async def topic_title(group, topic): return self.topic
        async def rename(group, topic, title):
            self.topic=title; self.writes.append('rename')
        async def create(group, topic, text):
            self.references['80'] = text; self.writes.append('create'); return '80'
        async def reference(group, topic, identity):
            return {'text':self.references[identity], 'pinned':self.pinned}
        async def edit(group, topic, identity, text):
            self.references[identity]=text; self.writes.append('edit')
        async def pin(group, topic, identity):
            self.pinned=True; self.writes.append('pin')
        self.codex.observe_chat=observe
        self.telegram.topic_title=topic_title
        self.telegram.rename_topic=rename
        self.telegram.create_reference=create
        self.telegram.reference=reference
        self.telegram.edit_reference=edit
        self.telegram.pin_reference=pin

    async def sync(self, task):
        return await self.app.handle({'action':'sync_reference','task_id':task['task_id']})

    async def test_missing_title_stays_pending_then_canonical_changes_update_same_binding(self):
        task=await self.task()
        result=await self.sync(task)
        self.assertEqual(result['reference_sync']['title']['status'],'pending',result)
        self.assertEqual(self.topic,'New chat')
        self.assertIn('Title pending',self.references['80'])
        self.title='Desktop title'
        result=await self.sync(task)
        self.assertEqual(self.topic,'Desktop title')
        self.assertEqual(result['reference_sync']['pin']['status'],'current')
        self.assertEqual(self.writes,['create','pin','edit','rename','edit'])
        self.assertEqual(result['chat_id'],task['chat_id'])
        self.assertEqual(len(self.codex.created),1)
        self.assertEqual(self.references['80'],'Project: help\nChat: Desktop title\nStatus: finished\nCodex: codex://threads/actual-chat\nChat ID: actual-chat')

    async def test_full_unicode_title_survives_telegram_limit_and_partial_pin_failure(self):
        task=await self.task()
        self.title='🛰' * 40
        async def denied(*args): raise PermissionError('pin denied')
        self.pinned=False
        self.telegram.pin_reference=denied
        result=await self.sync(task)
        self.assertEqual(self.topic,'🛰' * 32)
        self.assertIn('Chat: '+'🛰' * 40,self.references['80'])
        self.assertEqual(result['reference_sync']['title']['status'],'current')
        self.assertEqual(result['reference_sync']['reference']['status'],'current')
        self.assertEqual(result['reference_sync']['pin']['status'],'failed')
        self.assertEqual(result['status'],'finished')

    async def test_removal_between_operations_blocks_reference_after_successful_rename(self):
        task=await self.task()
        original=dict(self.references)
        self.title='Renamed'
        async def rename(*args):
            self.topic='Renamed'
            async def removed(folder): return set()
            self.telegram.allowed_groups=removed
        self.telegram.rename_topic=rename
        result=await self.sync(task)
        self.assertEqual(self.references,original)
        self.assertEqual(result['status'],'paused')
        self.assertIn('disabled',result['reference_sync']['reference']['reason'])

    async def test_uncertain_create_is_not_duplicated_after_restart(self):
        async def lost(*args):
            self.writes.append('uncertain create')
            raise TimeoutError('lost acknowledgement')
        self.telegram.create_reference=lost
        task=await self.task()
        result=await self.sync(task)
        self.assertEqual(result['reference_sync']['reference']['status'],'uncertain')
        await self.app.close()
        from telegram_integration.application import Application
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        result=await self.sync(task)
        self.assertEqual(self.writes,['uncertain create'])
        self.assertIn('inspect',result['reference_sync']['reference']['reason'])

    async def test_desktop_name_refresh_preserves_last_name_when_missing_and_manual_topic_rename_never_reroutes(self):
        task=await self.task()
        self.title='Canonical name'
        await self.sync(task)
        self.topic='Manual Telegram name'
        self.title=None
        result=await self.sync(task)
        self.assertEqual(self.topic,'Canonical name')
        self.assertEqual(result['reference_sync']['observation']['status'],'pending')
        self.assertEqual(result['project_id'],'server-help')
        self.assertEqual(result['chat_id'],'actual-chat')

    async def test_metadata_failure_keeps_verified_title_and_refreshes_completed_status(self):
        async def chats(project_id,cwd):
            return [dict(chat_id='existing',title='Canonical name',project_id=project_id,cwd=str(cwd))]
        self.codex.list_chats=chats
        choices=await self.app.handle(dict(action='link',group_id=10,topic_id=2))
        task=await self.app.handle(dict(action='link',group_id=10,topic_id=2,
                                        choice_id=choices['choice_id'],choice=1))
        self.title='Canonical name'
        await self.sync(task)
        self.assertIn('Status: linked',self.references['80'])
        finished=await self.task()
        self.assertEqual(finished['status'],'finished',finished)
        self.topic='Manual topic name'
        async def unavailable(*args): raise ConnectionError('Codex metadata unavailable')
        self.codex.observe_chat=unavailable
        result=await self.sync(finished)
        state=result['reference_sync']
        self.assertEqual(state['observation']['status'],'failed')
        self.assertIn('metadata unavailable',state['observation']['reason'])
        self.assertEqual(state['name'],'Canonical name')
        self.assertIn('Chat: Canonical name\nStatus: finished',self.references['80'])
        self.assertEqual(state['reference']['status'],'current')
        self.assertEqual(state['pin']['status'],'current')
        self.assertEqual(self.topic,'Canonical name')

    async def test_lost_reference_create_ack_replays_same_identity_after_restart(self):
        identities={}; lose=True
        async def create(group, topic, text, *, random_id=None):
            nonlocal lose
            identities.setdefault(random_id,'80')
            self.references['80']=text
            if lose:
                lose=False
                raise TimeoutError('remote success; lost create acknowledgment')
            return identities[random_id]
        self.telegram.create_reference=create
        # The first lifecycle attempt loses its ACK. Avoid the completion retry
        # until reconstruction by leaving the original adapter unavailable.
        original_run=self.codex.run
        async def run(*args,**kwargs):
            nonlocal lose
            result=await original_run(*args,**kwargs)
            lose=True
            return result
        self.codex.run=run
        task=await self.task()
        first=task
        lose=False
        self.assertEqual(first['reference_sync']['reference']['status'],'uncertain')
        await self.app.close()
        from telegram_integration.application import Application
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        result=await self.sync(task)
        self.assertEqual(result['reference_sync']['reference']['status'],'current')
        self.assertEqual(result['reference_sync']['pin']['status'],'current')
        self.assertEqual(len(identities),1)
        self.assertNotIn(None,identities)

    async def test_lost_edit_pin_and_rename_ack_use_remote_state_after_restart(self):
        task=await self.task()
        await self.sync(task)
        self.title='Changed title'
        original_rename=self.telegram.rename_topic
        original_edit=self.telegram.edit_reference
        original_pin=self.telegram.pin_reference
        self.pinned=False
        async def rename(*args):
            await original_rename(*args)
            raise TimeoutError('lost rename acknowledgment')
        async def edit(*args):
            await original_edit(*args)
            raise TimeoutError('lost edit acknowledgment')
        async def pin(*args):
            await original_pin(*args)
            raise TimeoutError('lost pin acknowledgment')
        self.telegram.rename_topic=rename; self.telegram.edit_reference=edit; self.telegram.pin_reference=pin
        await self.sync(task)  # rename and edit both succeeded remotely
        await self.sync(task)  # edit readback allows pin, whose ack is lost
        await self.app.close()
        from telegram_integration.application import Application
        self.app=Application(self.root/'db',self.root/'tasks',self.telegram,self.codex,catalog=self.catalog)
        result=await self.sync(task)
        self.assertEqual(result['reference_sync']['title']['status'],'current')
        self.assertEqual(result['reference_sync']['reference']['status'],'current')
        self.assertEqual(result['reference_sync']['pin']['status'],'current')
        self.assertEqual(self.writes,['create','pin','edit','rename','edit','pin'])

class ReferenceLifecycleTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = ReferenceTests.asyncSetUp
    asyncTearDown = ReferenceTests.asyncTearDown
    task = ReferenceTests.task
    async def test_running_reference_is_automatic_and_sync_does_not_own_execution(self):
        import asyncio
        from telegram_integration.contracts import RunResult
        started=asyncio.Event(); finish=asyncio.Event(); closed=[]
        async def run(*args,**kwargs):
            started.set(); await finish.wait(); return RunResult('Done','Hello','turn')
        async def close(): closed.append(True)
        self.codex.run=run; self.codex.aclose=close
        self.title='Active task'
        worker=asyncio.create_task(self.task())
        try:
            await asyncio.wait_for(started.wait(),2)
            self.assertTrue(self.pinned)
            self.assertIn('Status: running',self.references['80'])
            self.title='Desktop renamed during execution'
            result=await asyncio.wait_for(self.app.handle({'action':'sync_references'}),2)
            self.assertEqual(result['status'],'synchronized')
            self.assertEqual(self.topic,'Desktop renamed during execution')
            self.assertEqual(closed,[])
        finally:
            finish.set(); task=await worker
        self.assertEqual(task['status'],'finished')
        self.assertIn('Status: finished',self.references['80'])
        self.assertEqual(self.writes.count('create'),1)
        self.assertEqual((await self.app.handle({'action':'status','task_id':task['task_id']}))['phase'],'complete')

    async def test_ordinary_listener_creates_running_and_finished_pin_without_flags(self):
        import asyncio
        from telegram_integration.listener import listen
        from telegram_integration.contracts import Message, RunResult
        started=asyncio.Event(); finish=asyncio.Event()
        async def self_id(): return 77
        async def latest(group): return 100
        async def send(group,source,text,topic): return '100' if source is None else '201'
        async def message(group,identity): return Message(group,identity,'#codex greeting',topic_id=2)
        async def run(*args,**kwargs):
            started.set(); await finish.wait(); return RunResult('Done','Hello','turn')
        self.telegram.self_id=self_id; self.telegram.latest_message_id=latest
        self.telegram.send_text=send; self.telegram.message=message; self.codex.run=run
        application=self.app; case=self
        class Client:
            def add_event_handler(self,*args): pass
            def remove_event_handler(self,*args): pass
            async def catch_up(self):
                await application.handle(dict(action='telegram_event',kind='new_message',group_id=10,
                    message_id=101,sender_id=77,account_id=77,text='#codex greeting'))
            async def run_until_disconnected(self):
                try:
                    await asyncio.wait_for(started.wait(),2)
                    case.assertTrue(case.pinned)
                    case.assertIn('Status: running',case.references['80'])
                finally:
                    finish.set()
                async with asyncio.timeout(3):
                    while 'Status: finished' not in case.references['80']:
                        await asyncio.sleep(0.01)
        await listen(self.app,Client())
        self.assertEqual(self.writes.count('create'),1)

    async def test_removal_during_pre_run_metadata_prevents_turn_and_retains_no_start_intent(self):
        import asyncio
        groups={10}; observing=asyncio.Event(); release=asyncio.Event()
        async def allowed(folder): return groups.copy()
        async def self_id(): return 77
        async def latest(group): return 100
        async def observe(chat,cwd):
            observing.set(); await release.wait()
            return dict(chat_id=chat,cwd=str(cwd),project_id='server-help',name='Prepared chat')
        self.telegram.allowed_groups=allowed
        self.telegram.self_id=self_id; self.telegram.latest_message_id=latest
        self.codex.observe_chat=observe
        await self.app.handle({'action':'monitor_enable'})
        worker=asyncio.create_task(self.task())
        try:
            await asyncio.wait_for(observing.wait(),2)
            groups.clear()
            await self.app.handle({'action':'folder_changed'})
        finally:
            release.set(); result=await worker
        self.assertEqual(result['status'],'paused',result)
        self.assertEqual(self.codex.runs,[])
        self.assertNotIn('client_request_id',result)
        self.assertNotEqual(result['phase'],'executing')

    async def test_second_application_reference_refresh_preserves_concurrent_completion(self):
        import asyncio
        from telegram_integration.application import Application
        from telegram_integration.contracts import RunResult
        started=asyncio.Event(); finish=asyncio.Event(); observing=asyncio.Event(); release=asyncio.Event()
        async def run(*args,**kwargs):
            started.set(); await finish.wait(); return RunResult('Done','Preserved final document','completed-turn')
        self.codex.run=run
        other_codex=test_routing.Codex()
        async def observe(chat,cwd):
            observing.set(); await release.wait()
            return dict(chat_id=chat,cwd=str(cwd),project_id='server-help',name='Changed from desktop')
        other_codex.observe_chat=observe
        other=Application(self.root/'db',self.root/'tasks',self.telegram,other_codex,catalog=self.catalog)
        worker=asyncio.create_task(self.task())
        refresh=None
        try:
            await asyncio.wait_for(started.wait(),2)
            refresh=asyncio.create_task(other.handle({'action':'sync_references'}))
            await asyncio.wait_for(observing.wait(),2)
            finish.set(); completed=await asyncio.wait_for(worker,2)
            release.set(); await asyncio.wait_for(refresh,2)
            retained=await self.app.handle({'action':'status','task_id':completed['task_id']})
            self.assertEqual((retained['status'],retained['phase'],retained['turn_id']),('finished','complete','completed-turn'))
            self.assertEqual(retained['report_ids'],completed['report_ids'])
            from pathlib import Path
            self.assertEqual(Path(retained['document']).read_text(),'Preserved final document')
            self.assertIn('Status: finished',self.references['80'])
            self.assertIn('Changed from desktop',self.references['80'])
            self.assertEqual(self.writes.count('create'),1)
            self.assertEqual(other_codex.runs,[])
        finally:
            finish.set(); release.set()
            await worker
            if refresh: await refresh
            await other.close()
