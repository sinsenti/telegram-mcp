"""Recovery observed through Application with real SQLite and remote effects."""
import tempfile
import unittest
from pathlib import Path
from telegram_integration.application import Application
from tests.test_application import Telegram, Codex

class DurableTelegram(Telegram):
    def __init__(self):
        super().__init__()
        self.remote={}
        self.lose='text'
    async def send_text(self, group, message, text, topic, *, random_id=None):
        return await self.send('text',group,message,text,topic,random_id)
    async def send_document(self, group, message, path, topic, *, random_id=None):
        return await self.send('document',group,message,path.read_text(),topic,random_id)
    async def send(self,kind,group,message,payload,topic,random_id):
        key=(group,random_id)
        self.remote.setdefault(key,(str(500+len(self.remote)),kind,message,payload))
        if self.lose==kind:
            self.lose=None
            raise TimeoutError('remote success; acknowledgment lost')
        return self.remote[key][0]

class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_restart_recovers_reply_and_upload_without_duplicate_or_new_turn(self):
        for lost in ('text','document'):
            with self.subTest(lost=lost), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); telegram=DurableTelegram(); telegram.lose=lost; codex=Codex()
                app=Application(root/'db',root/'tasks',telegram,codex)
                await app.handle({'action':'configure','folder_id':7})
                first=await app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
                self.assertEqual(first['status'],'blocked')
                await app.close()
                app=Application(root/'db',root/'tasks',telegram,codex)
                result=await app.handle({'action':'reconcile_reports','task_id':first['task_id']})
                self.assertEqual(result['status'],'finished')
                self.assertEqual([(v[1],v[2]) for v in telegram.remote.values()],[('text',42),('document',42)])
                self.assertEqual(len(codex.runs),1)
                await app.handle({'action':'reconcile_reports','task_id':first['task_id']})
                self.assertEqual(len(telegram.remote),2)
                await app.close()

    async def test_revoked_group_retains_output_until_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); telegram=DurableTelegram(); codex=Codex()
            app=Application(root/'db',root/'tasks',telegram,codex)
            await app.handle({'action':'configure','folder_id':7})
            first=await app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
            telegram.allowed.clear()
            result=await app.handle({'action':'reconcile_reports','task_id':first['task_id']})
            self.assertEqual(result['status'],'blocked')
            self.assertEqual(len(telegram.remote),1)
            self.assertTrue(Path(first['document']).exists())
            telegram.allowed.add(10)
            self.assertEqual((await app.handle({'action':'reconcile_reports','task_id':first['task_id']}))['status'],'finished')
            self.assertEqual(len(telegram.remote),2)
            await app.close()

    async def test_changed_account_never_replays_an_old_random_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); telegram=DurableTelegram(); codex=Codex()
            async def account(): return telegram.account
            telegram.account=77; telegram.self_id=account
            app=Application(root/'db',root/'tasks',telegram,codex)
            await app.handle({'action':'configure','folder_id':7})
            first=await app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
            telegram.account=88
            result=await app.handle({'action':'reconcile_reports','task_id':first['task_id']})
            self.assertEqual(result['status'],'blocked')
            self.assertIn('account',result['reason'])
            self.assertEqual(len(telegram.remote),1)
            await app.close()

    async def test_legacy_confirmed_sends_stay_delivered_and_uncertain_ones_block(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with sqlite3.connect(root/'db') as old:
                old.execute('CREATE TABLE generated_sends (id TEXT PRIMARY KEY, group_id INTEGER, status TEXT)')
                old.executemany('INSERT INTO generated_sends VALUES (?,?,?)',[('old-delivered',10,'confirmed'),('old-unknown',10,'uncertain')])
            telegram=DurableTelegram(); app=Application(root/'db',root/'tasks',telegram,Codex())
            await app.handle({'action':'configure','folder_id':7})
            result=await app.handle({'action':'reconcile_reports'})
            self.assertEqual(result['status'],'blocked')
            self.assertEqual(result['operations'],[{'operation_id':'old-unknown','status':'blocked','reason':'Legacy send lacks durable payload and random identity; inspect Telegram manually'}])
            self.assertEqual(telegram.remote,{})
            await app.close()

    async def test_legacy_reporting_task_with_unassociated_confirmed_send_never_replays(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); telegram=DurableTelegram(); app=Application(root/'db',root/'tasks',telegram,Codex())
            await app.handle({'action':'configure','folder_id':7})
            document=root/'old.md'; document.write_text('Already delivered file')
            legacy=dict(task_id='old',group_id=10,message_id=42,topic_id=None,run=1,status='blocked',phase='reporting',explanation='Known old work',document=str(document))
            # Simulate the old schema's crash between confirmed send and task save.
            with app.db:
                app.db.execute('INSERT INTO tasks VALUES (?,?)',('old',json.dumps(legacy)))
                app.db.execute('INSERT INTO generated_sends VALUES (?,?,?)',('unassociated-confirmed',10,'confirmed'))
            result=await app.handle({'action':'reconcile_reports','task_id':'old'})
            self.assertEqual(result['status'],'blocked')
            self.assertIn('Legacy',result['reason'])
            self.assertEqual(telegram.remote,{})
            await app.close()
