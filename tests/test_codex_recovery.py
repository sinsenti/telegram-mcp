"""Installed app-server wire shapes, exercised through the adapter's public API."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest

from telegram_integration.codex import CodexAppServer
from telegram_integration.contracts import Blocked


SERVER = r'''
import json, sys, time
from pathlib import Path
mode=sys.argv[-1]
output=json.dumps({'status':'completed','explanation':'Recovered original result.','markdown':'# Original result'})
def emit(value): print(json.dumps(value),flush=True)
def entry(identity,kind='agentMessage',**fields):
    return {'turnId':'wanted-turn','item':dict(id=identity,type=kind,**fields),'startedAtMs':None,'completedAtMs':None}
for line in sys.stdin:
    m=json.loads(line)
    if 'id' not in m: continue
    method=m['method']; p=m.get('params',{})
    result={}
    with Path('requests.jsonl').open('a') as f: f.write(json.dumps(m)+'\n')
    if method in ('thread/start','thread/resume','thread/read'):
        result={'thread':{'id':'known-chat','cwd':str(Path.cwd()),'projectId':None,'name':'Known','status':{'type':'active','activeFlags':[]} if mode=='metadata-active' else {'type':'idle'},'canAcceptDirectInput':True}}
    elif method=='thread/turns/list':
        assert p['threadId']=='known-chat'
        if mode in ('accepted','interrupt','metadata-active'): data=[]; cursor=None
        elif mode=='turn-active':
            data=[{'id':'desktop-owned-turn','status':'inProgress','items':[],'itemsView':'full'}]; cursor=None
        elif mode=='repeated-cursor': data=[]; cursor='never-advances'
        elif p.get('cursor') is None:
            data=[{'id':'unrelated-turn','status':'completed','items':[],'itemsView':'full'}]; cursor='turn-page-two'
        else:
            assert p['cursor']=='turn-page-two'
            data=[{'id':'wanted-turn','status':'completed','items':[],'itemsView':'full'}]; cursor=None
        result={'data':data,'nextCursor':cursor,'backwardsCursor':None}
    elif method=='thread/items/list':
        assert p['threadId']=='known-chat'
        assert p.get('turnId') in (None,'wanted-turn')
        if p.get('cursor') is None:
            data=[entry('user','userMessage',clientId='request-uuid',content=[])]; cursor='item-page-two'
        else:
            assert p['cursor']=='item-page-two'
            item=entry('final',text='not structured JSON' if mode=='malformed' else output,phase='final_answer')
            if mode=='deferred':
                item['item']['text']=''; item['outputDeferred']=True
            data=[item]; cursor=None
            if mode=='duplicate-client':
                duplicate=entry('second-user','userMessage',clientId='request-uuid',content=[])
                duplicate['turnId']='another-turn'
                data.append(duplicate)
        result={'data':data,'nextCursor':cursor,'backwardsCursor':None}
    elif method=='thread/items/read':
        assert p=={'threadId':'known-chat','turnId':'wanted-turn','itemIds':['final']}
        result={'data':[entry('final',text=output,phase='final_answer')]}
    elif method=='turn/start':
        assert p['threadId']=='known-chat'
        assert p['clientUserMessageId']=='request-uuid'
        emit({'id':m['id'],'result':{'turn':{'id':'wanted-turn','status':'inProgress'}}})
        if mode=='interrupt': continue
        deadline=time.monotonic()+3
        while not Path('accepted.txt').exists() and time.monotonic()<deadline: time.sleep(.01)
        if not Path('accepted.txt').exists(): raise RuntimeError('completion awaited before durable acceptance callback')
        emit({'method':'item/completed','params':{'threadId':'known-chat','turnId':'wanted-turn','item':{'id':'final','type':'agentMessage','phase':'final_answer','text':output}}})
        emit({'method':'turn/completed','params':{'threadId':'known-chat','turn':{'id':'wanted-turn','status':'completed'}}})
        continue
    elif method=='turn/interrupt':
        assert p=={'threadId':'known-chat','turnId':'wanted-turn'}
        emit({'id':m['id'],'result':{}})
        emit({'method':'turn/completed','params':{'threadId':'known-chat','turn':{'id':'wanted-turn','status':'interrupted'}}})
        continue
    elif method!='initialize': raise RuntimeError('unexpected method '+method)
    emit({'id':m['id'],'result':result})
'''


class RecoveryWireTests(unittest.IsolatedAsyncioTestCase):
    def adapter(self, root, mode):
        script=root/'server.py'
        script.write_text(SERVER)
        return CodexAppServer([sys.executable,str(script),mode],timeout=3)

    async def test_acceptance_is_durable_before_waiting_for_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); adapter=self.adapter(root,'accepted')
            async def accepted(turn_id):
                self.assertEqual(turn_id,'wanted-turn')
                (root/'accepted.txt').write_text(turn_id)
            try:
                result=await adapter.run('known-chat',root,'Original request',client_request_id='request-uuid',on_turn_accepted=accepted)
                self.assertEqual(result.markdown,'# Original result')
                self.assertEqual((root/'accepted.txt').read_text(),'wanted-turn')
            finally: await adapter.aclose()

    async def test_completed_history_recovers_paginated_and_deferred_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); adapter=self.adapter(root,'deferred')
            try:
                observation=await adapter.observe_turn('known-chat',root,'wanted-turn')
                self.assertEqual(observation.status,'completed')
                self.assertEqual(observation.turn_id,'wanted-turn')
                self.assertEqual(observation.result.markdown,'# Original result')
                requests=[json.loads(line)['method'] for line in (root/'requests.jsonl').read_text().splitlines()]
                self.assertNotIn('turn/start',requests)
                self.assertIn('thread/items/read',requests)
            finally: await adapter.aclose()

    async def test_completed_malformed_output_does_not_become_unknown_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); adapter=self.adapter(root,'malformed')
            try:
                observation=await adapter.observe_turn('known-chat',root,'wanted-turn')
                self.assertEqual(observation.status,'completed')
                self.assertIsNone(observation.result)
                self.assertTrue(observation.reason)
            finally: await adapter.aclose()

    async def test_exact_persisted_client_identity_finds_original_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); adapter=self.adapter(root,'history')
            try:
                observation=await adapter.find_turn('known-chat',root,'request-uuid')
                self.assertEqual(observation.turn_id,'wanted-turn')
                self.assertEqual(observation.result.explanation,'Recovered original result.')
                absent=await adapter.find_turn('known-chat',root,'different-request')
                self.assertEqual(absent.status,'unknown')
                self.assertIsNone(absent.result)
            finally: await adapter.aclose()

    async def test_interrupt_uses_the_running_owner_without_competing_readers(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); adapter=self.adapter(root,'interrupt')
            accepted_event=asyncio.Event()
            async def accepted(turn_id): accepted_event.set()
            running=asyncio.create_task(adapter.run('known-chat',root,'Original request',client_request_id='request-uuid',on_turn_accepted=accepted))
            try:
                await asyncio.wait_for(accepted_event.wait(),3)
                await asyncio.wait_for(adapter.interrupt_turn('known-chat',root,'wanted-turn'),3)
                with self.assertRaisesRegex(Blocked,'interrupted'):
                    await asyncio.wait_for(running,3)
                requests=[json.loads(line)['method'] for line in (root/'requests.jsonl').read_text().splitlines()]
                self.assertEqual(requests.count('initialize'),1)
                self.assertEqual(requests.count('turn/interrupt'),1)
            finally:
                if not running.done(): running.cancel()
                await asyncio.gather(running,return_exceptions=True)
                await adapter.aclose()

    async def test_duplicate_client_identity_does_not_guess_a_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); adapter=self.adapter(root,'duplicate-client')
            try:
                observation=await adapter.find_turn('known-chat',root,'request-uuid')
                self.assertEqual(observation.status,'unknown')
                self.assertIsNone(observation.result)
                self.assertTrue(observation.reason)
            finally: await adapter.aclose()

    async def test_repeated_history_cursor_is_an_observable_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); adapter=self.adapter(root,'repeated-cursor')
            try:
                observation=await adapter.observe_turn('known-chat',root,'wanted-turn')
                self.assertEqual(observation.status,'unknown')
                self.assertIsNone(observation.result)
                self.assertIn('pagination',observation.reason)
            finally: await adapter.aclose()

    async def test_existing_active_work_blocks_new_fixed_input(self):
        for mode in ('turn-active','metadata-active'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                root=Path(folder); adapter=self.adapter(root,mode)
                try:
                    with self.assertRaises(Blocked):
                        await adapter.run('known-chat',root,'Original request',client_request_id='request-uuid')
                    requests=[json.loads(line)['method'] for line in (root/'requests.jsonl').read_text().splitlines()]
                    self.assertNotIn('turn/start',requests)
                finally: await adapter.aclose()

    async def test_missing_live_owner_cannot_interrupt_another_process(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); adapter=self.adapter(root,'history')
            try:
                with self.assertRaises(Blocked):
                    await adapter.interrupt_turn('known-chat',root,'wanted-turn')
                self.assertFalse((root/'requests.jsonl').exists())
            finally: await adapter.aclose()
