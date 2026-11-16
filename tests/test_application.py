import tempfile
import unittest
from pathlib import Path
from telegram_integration.application import Application
from telegram_integration.contracts import Message, RunResult

class Telegram:
    def __init__(self):
        self.allowed = {10}
        self.reads = []
        self.reports = []
    async def allowed_groups(self, folder_id):
        return self.allowed
    async def message(self, group_id, message_id):
        self.reads.append((group_id, message_id))
        return Message(group_id, message_id, 'Write a greeting')
    async def context(self, group_id, message_id, scope):
        from telegram_integration.contracts import Context
        return Context((await self.message(group_id, message_id),))
    async def send_text(self, group_id, message_id, explanation, topic_id):
        self.reports.append((group_id, message_id, explanation))
        return '500'
    async def send_document(self, group_id, message_id, document, topic_id):
        self.reports.append((group_id, message_id, document.read_text()))
        return '501'

class Codex:
    async def aclose(self):
        pass
    def __init__(self):
        self.chats = []
        self.runs = []
    async def create_chat(self, cwd):
        self.chats.append(cwd)
        return 'chat-actual-123'
    async def run(self, chat_id, cwd, prompt):
        self.runs.append((chat_id, cwd, prompt))
        return RunResult('Greeting prepared.', '# Hello\nWelcome!', 'turn-1')

class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.telegram, self.codex = Telegram(), Codex()
        self.app = Application(self.root/'state.sqlite', self.root/'tasks', self.telegram, self.codex)
        await self.app.handle({'action':'configure', 'folder_id':7})
    async def asyncTearDown(self):
        await self.app.close()
        self.tmp.cleanup()
    async def test_historical_text_and_denied_group(self):
        context = await self.app.handle({'action':'read', 'group_id':10, 'message_id':42})
        self.assertEqual(context['text'], 'Write a greeting')
        result = await self.app.handle({'action':'read', 'group_id':20, 'message_id':42})
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(self.telegram.reads, [(10,42)])
    async def test_task_and_followup_keep_chat_and_folder_across_restart(self):
        first = await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(first['status'], 'finished')
        self.assertEqual(first['chat_id'], 'chat-actual-123')
        self.assertEqual(Path(first['document']).read_text(), '# Hello\nWelcome!')
        self.assertEqual(self.telegram.reports[0][:2], (10,42))
        await self.app.close()
        self.app = Application(self.root/'state.sqlite',self.root/'tasks',self.telegram,self.codex)
        second = await self.app.handle({'action':'followup','task_id':first['task_id'],'message_id':43})
        self.assertEqual(second['status'], 'finished')
        self.assertEqual(second['folder'],first['folder'])
        self.assertEqual(len(self.codex.chats),1)
        self.assertEqual([x[0] for x in self.codex.runs],['chat-actual-123']*2)
        self.assertEqual(self.telegram.reports[2][:2],(10,43))

    async def test_followup_rejects_explicit_different_group_before_retrieval(self):
        first = await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        reads, runs, reports = list(self.telegram.reads), list(self.codex.runs), list(self.telegram.reports)
        self.telegram.allowed.add(20)
        result = await self.app.handle({'action':'followup','task_id':first['task_id'],'group_id':20,'message_id':43})
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('same group', result['reason'])
        self.assertEqual((self.telegram.reads,self.codex.runs,self.telegram.reports),(reads,runs,reports))
        self.assertEqual(await self.app.handle({'action':'status','task_id':first['task_id']}),first)

    async def test_unknown_task_destination_never_starts_chat(self):
        result = await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'production'})
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(self.codex.chats,[])

    async def test_removed_access_prevents_reporting_but_retains_result(self):
        original = self.codex.run
        async def revoke(*args):
            result = await original(*args)
            self.telegram.allowed.clear()
            return result
        self.codex.run = revoke
        result = await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'blocked')
        self.assertTrue(Path(result['document']).exists())
        self.assertEqual(self.telegram.reports,[])

    async def test_partial_remote_report_is_not_blindly_retried(self):
        async def uncertain(*args):
            raise TimeoutError('Report acknowledgment lost; inspect Telegram before retry')
        self.telegram.send_text = uncertain
        result = await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'blocked')
        again = await self.app.handle({'action':'followup','task_id':result['task_id'],'message_id':43})
        self.assertEqual(again['status'],'blocked')
        self.assertEqual(len(self.codex.runs),1)
    async def test_removal_between_text_and_document_prevents_upload(self):
        original = self.telegram.send_text
        async def revoke(*args):
            result = await original(*args)
            self.telegram.allowed.clear()
            return result
        self.telegram.send_text = revoke
        result = await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['report_ids'],['500'])
        self.assertEqual(len(self.telegram.reports),1)

    async def test_execution_blocker_is_reported_to_source(self):
        async def fail(*args):
            raise RuntimeError('Permission decision required')
        self.codex.run = fail
        result = await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(self.telegram.reports,[(10,42,'Blocked: Permission decision required')])

    async def test_attached_input_blocks_before_starting_codex(self):
        async def attached(group_id,message_id):
            return Message(group_id,message_id,'Use the attachment',has_attachment=True)
        self.telegram.message=attached
        result=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
        self.assertEqual(result['status'],'blocked')
        self.assertIn('attachment',result['reason'])
        self.assertEqual(self.codex.chats,[])

    async def test_unknown_creation_and_execution_outcomes_cannot_continue(self):
        async def uncertain(*args):
            raise TimeoutError('Codex acknowledgment lost; inspect chat')
        for phase in ('creating_chat','executing'):
            with self.subTest(phase=phase):
                self.codex.create_chat=Codex().create_chat
                self.codex.run=Codex().run
                if phase=='creating_chat':
                    self.codex.create_chat=uncertain
                else:
                    self.codex.run=uncertain
                blocked=await self.app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
                self.assertEqual(blocked['phase'],phase)
                again=await self.app.handle({'action':'followup','task_id':blocked['task_id'],'message_id':43})
                self.assertEqual(again['status'],'blocked')
                self.assertEqual(await self.app.handle({'action':'status','task_id':blocked['task_id']}),blocked)
