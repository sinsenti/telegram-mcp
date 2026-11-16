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

    async def test_original_manifest_images_skills_and_content_evidence(self):
        from telegram_integration.contracts import TaskInput
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            image=path/'original.png'
            image.write_bytes(b'image fixture; protocol test only')
            server=SERVER.replace("result={}\n", "result={}\n    if method=='skills/list':\n        result={'data':[{'cwd':str(Path.cwd()),'skills':[{'name':'pdf','path':'/tools/pdf/SKILL.md','enabled':True}],'errors':[]}]}\n")
            server=server.replace("if method=='turn/start':\n        text=", "if method=='turn/start':\n        Path('payload.json').write_text(json.dumps(p))\n        text=")
            server=server.replace("'markdown':'# Result\\n\\n42'", "'markdown':'# Result\\n\\n42','input_evidence':[{'input_id':'photo','outcome':'interpreted','evidence':'Three red squares above two blue circles'},{'input_id':'pdf','outcome':'interpreted','evidence':'Page 2: amber bridge 47'}]")
            script=path/'server.py';script.write_text(server)
            codex=CodexAppServer(command=[sys.executable,str(script),'success'])
            chat=await codex.create_chat(path)
            inputs=(TaskInput('photo',10,42,'p','shape.png','image/png',str(image),'image','hash',5),
                    TaskInput('pdf',10,43,'d','checkpoint.pdf','application/pdf',str(path/'original.pdf'),'pdf','hash',5))
            result=await codex.run(chat,path,'Read originals',inputs=inputs)
            self.assertEqual(result.input_evidence[0].evidence,'Three red squares above two blue circles')
            payload=json.loads((path/'payload.json').read_text())
            self.assertIn({'type':'localImage','path':str(image)},payload['input'])
            self.assertIn({'type':'skill','name':'pdf','path':'/tools/pdf/SKILL.md'},payload['input'])
            self.assertIn('checkpoint.pdf',payload['input'][0]['text'])
            self.assertIn('input_evidence',payload['outputSchema']['required'])

    async def test_application_retains_terminal_wire_result_before_evidence_policy(self):
        invalid=[[],[{'input_id':'unknown','outcome':'interpreted','evidence':'Fact'}],
                 [{'input_id':'10:42:a','outcome':'interpreted','evidence':''}],
                 [{'input_id':'10:42:a','outcome':'interpreted','evidence':'Fact'}]*2,
                 [{'input_id':'10:42:a','outcome':'explicitly_unnecessary','evidence':'Model guessed'}],
                 [{'input_id':'10:42:a','outcome':'unreadable','evidence':'Corrupt original'}]]
        cases=[('completed',evidence) for evidence in invalid]
        cases.append(('blocked',[{'input_id':'10:42:a','outcome':'unreadable','evidence':'Corrupt original'}]))
        for status,evidence in cases:
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)
                output={'status':status,'explanation':'Original cannot be used','markdown':'# Summary','input_evidence':evidence}
                server=SERVER.replace("text=json.dumps({'status':'completed','explanation':'Done.','markdown':'# Result\\n\\n42'})",'text='+repr(json.dumps(output)))
                script=path/'server.py';script.write_text(server)
                codex=CodexAppServer(command=[sys.executable,str(script),'success'])
                from telegram_integration.application import Application
                from telegram_integration.contracts import Attachment, Context, Message
                from test_application import Telegram
                telegram=Telegram()
                usable_context=telegram.context
                async def context(group,message,scope):
                    return Context((Message(group,message,'Read original',True,
                        attachment=Attachment('a','note.txt')),))
                async def download(group,message,attachment,file):
                    file.write(b'original')
                telegram.context=context
                telegram.download=download
                app=Application(path/'state.sqlite',path/'tasks',telegram,codex)
                await app.handle({'action':'configure','folder_id':7})
                result=await app.handle({'action':'task','group_id':10,'message_id':42,'destination':'test'})
                self.assertEqual(result['status'],'blocked',result)
                self.assertEqual(result['turn_id'],'turn-actual',result)
                self.assertEqual(result['input_evidence'],evidence)
                self.assertEqual(result['explanation'],'Original cannot be used')
                artifact=json.loads((Path(result['folder'])/'run-result-1.json').read_text())
                self.assertEqual(artifact['input_evidence'],evidence)
                self.assertEqual(artifact['markdown'],'# Summary')
                self.assertEqual(artifact['status'],status)
                self.assertNotIn('document',result)
                self.assertEqual((await app.handle({'action':'status','task_id':result['task_id']}))['turn_id'],'turn-actual')
                # Explicit new request replaces the unusable input, using the same
                # materialized chat through the actual resume wire contract.
                telegram.context=usable_context
                script.write_text(SERVER)
                again=await app.handle({'action':'followup','task_id':result['task_id'],'message_id':43})
                self.assertEqual(again['status'],'finished',again)
                self.assertEqual(again['chat_id'],result['chat_id'])
                self.assertEqual(again['folder'],result['folder'])
                self.assertEqual(again['input_evidence'],[])
                self.assertEqual(artifact,json.loads((Path(result['folder'])/'run-result-1.json').read_text()))
                await app.close()
