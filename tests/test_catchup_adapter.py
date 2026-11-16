import unittest
from datetime import datetime,timezone
from types import SimpleNamespace as NS
from telethon.tl import functions,types
from telegram_integration.telegram import TelethonAdapter
from telegram_integration.contracts import Blocked
from test_telegram import Client

class CatchupAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_scoped_forward_pages_preserve_edit_evidence_and_check_access_each_time(self):
        class HistoryClient(Client):
            async def __call__(self,request):
                if isinstance(request,functions.messages.GetHistoryRequest):
                    self.requests.append(request)
                    return NS(messages=[NS(id=102,chat_id=-1000000000010,sender_id=77,raw_text='#codex',date=datetime(2026,1,1,tzinfo=timezone.utc),edit_date=datetime.now(timezone.utc),fwd_from=None),
                                        NS(id=101,chat_id=-1000000000010,sender_id=77,raw_text='context',date=datetime(2026,1,1,tzinfo=timezone.utc),edit_date=None,fwd_from=None)])
                return await super().__call__(request)
            async def iter_dialogs(self):
                raise AssertionError('Explicit catch-up must not enumerate unrelated dialogs')
                yield
        client=HistoryClient(); adapter=TelethonAdapter(client)
        await adapter.allowed_groups(7)
        page=await adapter.history_page(-1000000000010,100,2)
        self.assertEqual([(e['message_id'],e['kind'],e['edited']) for e in page],[(101,'history_message',False),(102,'history_message',True)])
        request=next(r for r in client.requests if isinstance(r,functions.messages.GetHistoryRequest))
        self.assertEqual((request.offset_id,request.add_offset,request.limit),(101,-2,2))
        client.filter.include_peers=[]
        with self.assertRaises(Blocked): await adapter.history_page(-1000000000010,102,2)
        self.assertEqual(sum(isinstance(r,functions.messages.GetHistoryRequest) for r in client.requests),1)
