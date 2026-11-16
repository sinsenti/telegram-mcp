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
        self.assertEqual(self.writes,['create','pin','rename','edit'])
        self.assertEqual(result['chat_id'],task['chat_id'])
        self.assertEqual(len(self.codex.created),1)
        self.assertEqual(self.references['80'],'Project: help\nChat: Desktop title\nStatus: finished\nCodex: codex://threads/actual-chat\nChat ID: actual-chat')

    async def test_full_unicode_title_survives_telegram_limit_and_partial_pin_failure(self):
        task=await self.task()
        self.title='🛰' * 40
        async def denied(*args): raise PermissionError('pin denied')
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
        self.title='Renamed'
        async def rename(*args):
            self.topic='Renamed'
            async def removed(folder): return set()
            self.telegram.allowed_groups=removed
        self.telegram.rename_topic=rename
        result=await self.sync(task)
        self.assertEqual(self.references,{})
        self.assertEqual(result['status'],'paused')
        self.assertIn('disabled',result['reference_sync']['reference']['reason'])

    async def test_uncertain_create_is_not_duplicated_after_restart(self):
        task=await self.task()
        async def lost(*args):
            self.writes.append('uncertain create')
            raise TimeoutError('lost acknowledgement')
        self.telegram.create_reference=lost
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
        task=await self.task(); identities={}; lose=True
        async def create(group, topic, text, *, random_id=None):
            nonlocal lose
            identities.setdefault(random_id,'80')
            self.references['80']=text
            if lose:
                lose=False
                raise TimeoutError('remote success; lost create acknowledgment')
            return identities[random_id]
        self.telegram.create_reference=create
        first=await self.sync(task)
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
        self.assertEqual(self.writes,['create','pin','rename','edit','pin'])
