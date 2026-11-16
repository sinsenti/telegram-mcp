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
        self.assertEqual(result['status'],'finished')
        self.assertIn('outside',result['reference_sync']['reference']['reason'])

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
