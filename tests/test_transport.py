import io
import json
import unittest
from telegram_integration.transport import serve

class Application:
    def __init__(self):
        self.commands=[]
    async def handle(self, command):
        self.commands.append(command)
        return {'status':'selected','text':'Historical task'}

class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_mcp_envelope_reaches_application(self):
        app = Application()
        request = {'jsonrpc':'2.0','id':9,'method':'tools/call','params':{'name':'telegram','arguments':{'action':'read','group_id':10,'message_id':42}}}
        output=io.StringIO()
        await serve(app, io.StringIO(json.dumps(request)+'\n'),output)
        response=json.loads(output.getvalue())
        self.assertEqual(response['id'],9)
        self.assertEqual(json.loads(response['result']['content'][0]['text'])['text'],'Historical task')
        self.assertEqual(app.commands,[{'action':'read','group_id':10,'message_id':42}])
