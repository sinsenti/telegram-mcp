"""Application acceptance checks use real reopened SQLite and task folders."""
import tempfile
import unittest
from pathlib import Path
from telegram_integration.application import Application
from test_application import Telegram, Codex


class IntentTests(unittest.IsolatedAsyncioTestCase):
    async def test_creation_intent_is_durable_before_remote_success_lost_ack(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); telegram=Telegram(); codex=Codex(); effects=[]
            async def create(cwd):
                observer=Application(root/'state',root/'tasks',telegram,Codex())
                try:
                    saved=await observer.handle({'action':'status','task_id':cwd.name})
                    self.assertEqual(saved['phase'],'creating_chat')
                    self.assertTrue(saved['codex_create_intent'])
                    self.assertIsNone(saved['chat_id'])
                finally: await observer.close()
                effects.append('remote-chat-created')
                raise ConnectionError('Chat created but acknowledgment lost')
            codex.create_chat=create
            app=Application(root/'state',root/'tasks',telegram,codex)
            await app.handle({'action':'configure','folder_id':7})
            task=await app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
            await app.close()
            rebuilt=Application(root/'state',root/'tasks',telegram,codex)
            try:
                saved=await rebuilt.handle({'action':'status','task_id':task['task_id']})
                self.assertEqual(saved['codex_create_intent'],task['codex_create_intent'])
                retry=await rebuilt.handle({'action':'followup','task_id':task['task_id'],'message_id':43})
                self.assertEqual(retry['status'],'blocked')
                self.assertEqual(effects,['remote-chat-created'])
            finally: await rebuilt.close()

    async def test_start_intent_and_accepted_identity_survive_lost_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); telegram=Telegram(); codex=Codex(); requests=[]
            async def run(chat,cwd,prompt,*,inputs=(),client_request_id,on_turn_accepted,output_directory=None):
                observer=Application(root/'state',root/'tasks',telegram,Codex())
                saved=await observer.handle({'action':'status','task_id':cwd.name})
                self.assertEqual(saved['client_request_id'],client_request_id)
                self.assertEqual(saved['phase'],'executing')
                requests.append(client_request_id)
                await on_turn_accepted('accepted-exact-turn')
                saved=await observer.handle({'action':'status','task_id':cwd.name})
                self.assertEqual(saved['turn_id'],'accepted-exact-turn')
                await observer.close()
                raise ConnectionError('Turn completed but acknowledgment lost')
            codex.run=run
            app=Application(root/'state',root/'tasks',telegram,codex)
            await app.handle({'action':'configure','folder_id':7})
            task=await app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
            await app.close()
            rebuilt=Application(root/'state',root/'tasks',telegram,codex)
            try:
                saved=await rebuilt.handle({'action':'status','task_id':task['task_id']})
                self.assertEqual(saved['turn_id'],'accepted-exact-turn')
                self.assertEqual(saved['client_request_id'],requests[0])
                retry=await rebuilt.handle({'action':'followup','task_id':task['task_id'],'message_id':43})
                self.assertEqual(retry['status'],'blocked')
                self.assertEqual(len(requests),1)
            finally: await rebuilt.close()
