import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from telethon.tl import functions, types
from telegram_integration.telegram import TelethonAdapter
from telegram_integration.contracts import Blocked

class Client:
    def __init__(self):
        self.requests=[]
        self.filter=types.DialogFilter(id=7,title=types.TextWithEntities('Codex',[]),pinned_peers=[],include_peers=[types.InputPeerChannel(10,123)],exclude_peers=[])
    async def __call__(self, request):
        self.requests.append(request)
        if isinstance(request, functions.messages.GetDialogFiltersRequest):
            return NS(filters=[self.filter])
        return types.UpdateShortSentMessage(id=500,pts=1,pts_count=1,date=None,out=True)
    async def iter_dialogs(self):
        yield NS(id=-1000000000010,is_group=True,entity=types.Channel(id=10,title='Project',photo=types.ChatPhotoEmpty(),date=None,megagroup=True),dialog=NS(folder_id=None))
    async def get_input_entity(self, group):
        return types.InputPeerChannel(10,123)
    async def get_messages(self, peer, ids):
        return NS(id=ids,chat_id=-1000000000010,raw_text='Old task',media=None,reply_to=NS(reply_to_top_id=5,forum_topic=True,reply_to_msg_id=5),action=None)
    async def upload_file(self, path):
        return types.InputFile(id=1,parts=1,name='result.md',md5_checksum='')

class TelegramTests(unittest.IsolatedAsyncioTestCase):
    async def test_stable_filter_identity_and_actual_destination(self):
        client=Client()
        adapter=TelethonAdapter(client)
        self.assertEqual(await adapter.allowed_groups(7),{-1000000000010})
        selected=await adapter.message(-1000000000010,42)
        self.assertEqual(selected.text,'Old task')
        self.assertEqual(selected.topic_id,5)
        with self.assertRaises(Blocked):
            await adapter.message(999,42)
        with self.assertRaises(Blocked):
            await adapter.allowed_groups(8)

    async def test_raw_source_reply_and_document_use_topic(self):
        client=Client()
        adapter=TelethonAdapter(client)
        await adapter.allowed_groups(7)
        await adapter.send_text(-1000000000010,42,'Done',5)
        with tempfile.TemporaryDirectory() as tmp:
            document=Path(tmp)/'result.md'
            document.write_text('# Result')
            await adapter.send_document(-1000000000010,42,document,5)
        sent=[r for r in client.requests if isinstance(r,(functions.messages.SendMessageRequest,functions.messages.SendMediaRequest))]
        self.assertEqual(len(sent),2)
        self.assertEqual([(r.reply_to.reply_to_msg_id,r.reply_to.top_msg_id) for r in sent],[(42,5),(42,5)])
        self.assertTrue(all(r.random_id for r in sent))
        client.filter.exclude_peers=[types.InputPeerChannel(10,123)]
        with self.assertRaises(Blocked):
            await adapter.send_text(-1000000000010,42,'Should not send',5)
