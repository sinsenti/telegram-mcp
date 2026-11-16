import unittest
import test_application
from telegram_integration.contracts import Message


class ContextTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_application.ApplicationTests.asyncSetUp
    asyncTearDown = test_application.ApplicationTests.asyncTearDown
    async def test_message_and_topic_scopes_execute_all_selected_text(self):
        from telegram_integration.contracts import Context
        async def context(group, message, scope):
            messages = [Message(group, message, 'Write a greeting', topic_id=2),
                        Message(group, 43, 'Use Spanish', topic_id=2)]
            if scope == 'topic':
                messages.append(Message(group, 44, 'Include a farewell', topic_id=2))
            return Context(tuple(messages))
        self.telegram.context = context
        for scope, expected in [('message', 2), ('topic', 3)]:
            read = await self.app.handle({'action':'read','group_id':10,'message_id':42,'scope':scope})
            self.assertEqual([m['text'] for m in read['messages']], ['Write a greeting', 'Use Spanish'] + (['Include a farewell'] if scope == 'topic' else []))
            self.assertTrue(read['complete'])
            task = await self.app.handle({'action':'task','selection_id':read['selection_id'],'destination':'test'})
            self.assertEqual(task['status'], 'finished')
            self.assertIn('Use Spanish', self.codex.runs[-1][2])
            if scope == 'topic':
                self.assertIn('Include a farewell', self.codex.runs[-1][2])
            self.assertEqual(self.telegram.reports[-1][:2], (10,42))

    async def test_search_requires_a_numbered_choice_and_revalidates_it(self):
        async def search(group, query):
            return (Message(group,42,'First task'),Message(group,43,'Second task'))
        self.telegram.search=search
        found=await self.app.handle({'action':'search','group_id':10,'query':'task'})
        self.assertEqual([(m['choice'],m['text']) for m in found['choices']],[(1,'First task'),(2,'Second task')])
        self.assertEqual(self.codex.runs,[])
        for invalid in ({'search_id':found['search_id']}, {'query':'task','group_id':10},
                        {'search_id':found['search_id'],'choice':3}, {'search_id':found['search_id'],'choice':True}):
            outcome=await self.app.handle(dict(invalid,action='task',destination='test'))
            self.assertEqual(outcome['status'],'blocked')
        task=await self.app.handle({'action':'task','search_id':found['search_id'],'choice':2,'destination':'test'})
        self.assertEqual(task['status'],'finished')
        self.assertEqual(self.telegram.reports[0][:2],(10,43))
        self.telegram.allowed.clear()
        denied=await self.app.handle({'action':'task','search_id':found['search_id'],'choice':1,'destination':'test'})
        self.assertEqual(denied['status'],'blocked')

    async def test_paged_full_text_survives_restart_and_unseen_search_choices_are_invalid(self):
        from telegram_integration.contracts import Context
        long_text='Instruction '+('αβγ\n'*3000)
        async def context(group, message, scope):
            return Context((Message(group,message,long_text),Message(group,43,'Last instruction')))
        async def search(group, query):
            return (Message(group,42,'First'),Message(group,43,'Second'))
        self.telegram.context=context
        self.telegram.search=search
        first=await self.app.handle({'action':'read','group_id':10,'message_id':42,'page_size':1})
        self.assertEqual(first['text'],long_text)
        self.assertTrue(first['complete'])
        self.assertFalse(first['page_complete'])
        await self.app.close()
        self.app=test_application.Application(self.root/'state.sqlite',self.root/'tasks',self.telegram,self.codex)
        last=await self.app.handle({'action':'read','continuation':first['continuation']})
        self.assertEqual(last['text'],'Last instruction')
        self.assertTrue(last['page_complete'])
        results=await self.app.handle({'action':'search','group_id':10,'query':'task','page_size':1})
        unseen=await self.app.handle({'action':'task','search_id':results['search_id'],'choice':2,'destination':'test'})
        self.assertEqual(unseen['status'],'blocked')
        self.assertIn('presented',unseen['reason'])
        next_page=await self.app.handle({'action':'read','continuation':results['continuation']})
        self.assertEqual(next_page['choices'][0]['choice'],2)
        task=await self.app.handle({'action':'task','selection_id':first['selection_id'],'destination':'test'})
        self.assertEqual(task['status'],'finished')
        self.assertIn(long_text+'\n\nLast instruction',self.codex.runs[-1][2])

    async def test_incomplete_or_deleted_context_blocks_execution_and_revoked_pages_expose_no_text(self):
        from telegram_integration.contracts import Context, Blocked
        async def incomplete(group, message, scope):
            return Context((Message(group,message,'Partial instructions'),),False,'Missing parent 41')
        self.telegram.context=incomplete
        read=await self.app.handle({'action':'read','group_id':10,'message_id':42})
        self.assertFalse(read['complete'])
        self.assertEqual(read['reason'],'Missing parent 41')
        task=await self.app.handle({'action':'task','selection_id':read['selection_id'],'destination':'test'})
        self.assertEqual(task['status'],'blocked')
        self.assertIn('incomplete',task['reason'])
        async def deleted(*args):
            raise Blocked('Selected message was deleted')
        self.telegram.context=deleted
        task=await self.app.handle({'action':'task','selection_id':read['selection_id'],'destination':'test'})
        self.assertEqual(task['reason'],'Selected message was deleted')
        self.assertEqual(self.codex.chats,[])
        async def pages(group,message,scope):
            return Context((Message(group,message,'First'),Message(group,43,'Second')))
        self.telegram.context=pages
        read=await self.app.handle({'action':'read','group_id':10,'message_id':42,'page_size':1})
        self.telegram.allowed.clear()
        revoked=await self.app.handle({'action':'read','continuation':read['continuation']})
        self.assertEqual(revoked['status'],'blocked')
        self.assertNotIn('text',revoked)

    async def test_links_choose_message_or_topic_scope_from_resolved_source(self):
        from telegram_integration.contracts import Context
        async def resolve(link):
            return Message(10,2 if link.endswith('/2') else 42,'Selected',topic_id=2,is_topic_root=link.endswith('/2'))
        async def context(group,message,scope):
            return Context((Message(group,message,scope,topic_id=2),))
        self.telegram.resolve_link=resolve
        self.telegram.context=context
        message=await self.app.handle({'action':'read','link':'https://t.me/c/10/2/42'})
        topic=await self.app.handle({'action':'read','link':'https://t.me/c/10/2'})
        self.assertEqual((message['scope'],message['text']),('message','message'))
        self.assertEqual((topic['scope'],topic['text']),('topic','topic'))
