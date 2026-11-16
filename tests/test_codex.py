import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from telegram_integration.codex import CodexAppServer
from telegram_integration.contracts import Blocked


SERVER = r'''
import json, os, sys
from pathlib import Path
Path('server.pid').write_text(str(os.getpid()))
loaded=False
rollout=Path("rollout.json")
for line in sys.stdin:
    m=json.loads(line)
    if 'id' not in m:
        continue
    method=m.get('method')
    p=m.get('params', {})
    forbidden={'model', 'sandbox', 'sandboxPolicy', 'approvalPolicy', 'approvalsReviewer'}
    if forbidden.intersection(p):
        print(json.dumps({'id':m['id'],'error':{'message':'settings overridden'}}), flush=True)
        continue
    result={}
    if method=='thread/start':
        if sys.argv[-1]=='reject':
            print(json.dumps({'id':m['id'],'error':{'message':'cannot create thread'}}), flush=True)
            continue
        loaded=True
        result={'thread':{'id':'chat-actual'}}
    elif method=='thread/resume':
        if not rollout.exists():
            print(json.dumps({'id':m['id'],'error':{'message':'no rollout found'}}), flush=True)
            continue
        loaded=True
        result={'thread':{'id':'chat-actual'}}
    elif method=='turn/start':
        if not loaded or p['threadId']!='chat-actual':
            raise RuntimeError('wrong chat')
        if sys.argv[-1]=='approval':
            print(json.dumps({'id':99,'method':'item/commandExecution/requestApproval','params':{'threadId':'chat-actual','turnId':'turn-actual','reason':'Needs permission'}}), flush=True)
            continue
        rollout.write_text('materialized')
        result={'turn':{'id':'turn-actual'}}
        print(json.dumps({'method':'item/completed','params':{'threadId':'chat-actual','turnId':'turn-actual','item':{'type':'agentMessage','phase':'commentary','text':'Working'}}}), flush=True)
    print(json.dumps({'id':m['id'],'result':result}), flush=True)
    if method=='turn/start':
        text=json.dumps({'status':'completed','explanation':'Done.','markdown':'# Result\n\n42'})
        print(json.dumps({'method':'item/completed','params':{'threadId':'chat-actual','turnId':'turn-actual','item':{'type':'agentMessage','phase':'final_answer','text':text}}}), flush=True)
        print(json.dumps({'method':'turn/completed','params':{'threadId':'chat-actual','turn':{'id':'turn-actual','status':'completed'}}}), flush=True)
'''


class CodexAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_creates_and_resumes_actual_chat_without_permission_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            script=path/'server.py'
            script.write_text(SERVER)
            codex=CodexAppServer(command=[sys.executable, str(script), 'success'])
            chat=await codex.create_chat(path)
            result=await codex.run(chat, path, 'Write the answer')
            self.assertEqual(chat, 'chat-actual')
            self.assertEqual(result.turn_id, 'turn-actual')
            self.assertEqual(result.explanation, 'Done.')
            self.assertEqual(result.markdown, '# Result\n\n42')
            first_pid=int((path/'server.pid').read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(first_pid,0)
            await codex.aclose()
            resumed=CodexAppServer(command=[sys.executable, str(script), 'success'])
            again=await resumed.run(chat, path, 'Continue the answer')
            self.assertEqual(again.explanation, 'Done.')
            self.assertNotEqual(int((path/'server.pid').read_text()), first_pid)
            await resumed.aclose()

    async def test_permission_decision_is_a_blocker_instead_of_implicit_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            script=path/'server.py'
            script.write_text(SERVER)
            codex=CodexAppServer(command=[sys.executable, str(script), 'approval'])
            chat=await codex.create_chat(path)
            with self.assertRaisesRegex(Blocked, 'Needs permission'):
                await codex.run(chat, path, 'Run a task')
            with self.assertRaises(ProcessLookupError):
                os.kill(int((path/'server.pid').read_text()),0)
            await codex.aclose()

    async def test_shutdown_releases_a_chat_waiting_for_its_first_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            script=path/'server.py'
            script.write_text(SERVER)
            codex=CodexAppServer(command=[sys.executable,str(script),'success'])
            await codex.create_chat(path)
            pid=int((path/'server.pid').read_text())
            os.kill(pid,0)
            await codex.aclose()
            with self.assertRaises(ProcessLookupError):
                os.kill(pid,0)
            await codex.aclose()

    async def test_failed_creation_releases_its_owned_server(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            script=path/'server.py'
            script.write_text(SERVER)
            codex=CodexAppServer(command=[sys.executable,str(script),'reject'])
            with self.assertRaisesRegex(Blocked,'cannot create thread'):
                await codex.create_chat(path)
            with self.assertRaises(ProcessLookupError):
                os.kill(int((path/'server.pid').read_text()),0)
            await codex.aclose()
