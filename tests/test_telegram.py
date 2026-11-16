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
        self.media=None
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
        return NS(id=ids,chat_id=-1000000000010,raw_text='Old task',media=self.media,reply_to=NS(reply_to_top_id=5,forum_topic=True,reply_to_msg_id=5),action=None)
    async def upload_file(self, path):
        return types.InputFile(id=1,parts=1,name='result.md',md5_checksum='')

class TelegramTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_links_keep_message_scope_and_validate_thread_identity(self):
        client=Client()
        adapter=TelethonAdapter(client)
        await adapter.allowed_groups(7)
        selected=await adapter.resolve_link('https://t.me/c/10/5/42')
        self.assertEqual((selected.group_id,selected.message_id,selected.topic_id,selected.is_topic_root),
                         (-1000000000010,42,5,False))
        for link in ['https://t.me/c/10/6/42','https://t.me/c/10/42?comment=8',
                     'https://t.me/c/11/42','https://example.com/c/10/42']:
            with self.subTest(link=link),self.assertRaises(Blocked):
                await adapter.resolve_link(link)
    async def test_topic_history_filters_message_selection_to_transitive_replies(self):
        client=Client()
        original=client.__call__
        async def request(request):
            if not isinstance(request,functions.messages.GetRepliesRequest):
                return await original(request)
            self.assertEqual((request.msg_id,request.limit),(5,100))
            messages=[]
            if request.offset_id == 42:
                return NS(messages=[])
            page=[(46,43,'Nested reply'),(45,5,'Sibling conversation')] if request.offset_id == 0 else [(43,42,'Reply'),(42,5,'Root')]
            for identity, parent, text in page:
                messages.append(NS(id=identity,chat_id=-1000000000010,raw_text=text,media=None,
                         reply_to=NS(reply_to_top_id=5,forum_topic=True,reply_to_msg_id=parent),action=None))
            return NS(messages=messages)
        class PagedClient(Client):
            async def __call__(self, r):
                return await request(r)
        paged=PagedClient()
        paged.get_messages=client.get_messages
        client=paged
        adapter=TelethonAdapter(client)
        await adapter.allowed_groups(7)
        selected=await adapter.context(-1000000000010,42,'message')
        self.assertEqual([m.text for m in selected.messages],['Old task','Reply','Nested reply'])
        topic=await adapter.context(-1000000000010,42,'topic')
        self.assertEqual([m.message_id for m in topic.messages],[5,42,43,45,46])
        self.assertTrue(topic.complete)

    async def test_general_history_excludes_other_topics_and_search_is_peer_scoped(self):
        class GeneralClient(Client):
            async def get_entity(self, peer):
                return NS(forum=True)
            async def get_messages(self, peer, ids):
                if ids == 1:
                    return None
                return NS(id=ids,chat_id=-1000000000010,raw_text='General task',media=None,reply_to=None,action=None)
            async def __call__(self, request):
                if isinstance(request,(functions.messages.GetHistoryRequest,functions.messages.SearchRequest)):
                    self.requests.append(request)
                    if request.offset_id:
                        return NS(messages=[])
                    return NS(messages=[NS(id=9,chat_id=-1000000000010,raw_text='General task',media=None,reply_to=None,action=None),
                        NS(id=8,chat_id=-1000000000010,raw_text='Other topic',media=None,
                           reply_to=NS(forum_topic=True,reply_to_top_id=5,reply_to_msg_id=5),action=None)])
                return await super().__call__(request)
        client=GeneralClient()
        adapter=TelethonAdapter(client)
        await adapter.allowed_groups(7)
        topic=await adapter.context(-1000000000010,1,'topic')
        self.assertEqual([m.text for m in topic.messages],['','General task'])
        self.assertTrue(topic.complete)
        linked=await adapter.resolve_link('https://t.me/project/1/9')
        self.assertEqual((linked.topic_id,linked.message_id,linked.is_topic_root),(1,9,False))
        await adapter.search(-1000000000010,'task')
        searches=[r for r in client.requests if isinstance(r,functions.messages.SearchRequest)]
        self.assertEqual([(r.peer.channel_id,r.q,r.offset_id) for r in searches],[(10,'task',0),(10,'task',8)])
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

    async def test_link_previews_are_text_but_real_and_unsupported_media_are_attachments(self):
        client=Client()
        adapter=TelethonAdapter(client)
        await adapter.allowed_groups(7)
        cases=[
            (types.MessageMediaWebPage(types.WebPageEmpty(id=123)), False),
            (types.MessageMediaPhoto(types.PhotoEmpty(id=123)), True),
            (types.MessageMediaDocument(types.DocumentEmpty(id=123)), True),
            (types.MessageMediaGeo(types.GeoPointEmpty()), True),
        ]
        for media, expected in cases:
            with self.subTest(media=type(media).__name__):
                client.media=media
                selected=await adapter.message(-1000000000010,42)
                self.assertEqual(selected.has_attachment,expected)
