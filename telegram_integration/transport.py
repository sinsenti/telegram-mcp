"""Thin newline-delimited MCP stdio transport."""
import asyncio
import json

TOOL = {'name':'telegram','description':'Manual local Telegram task commands. Task creation requires explicit destination=test or project; project choices block until selected.',
        'inputSchema':{'type':'object','properties':{'action':{'type':'string','enum':['configure','read','search','task','followup','status','project','link','chat_command','sync_reference','sync_references','monitor_enable','monitor_refresh','monitor_status','dispatch_pending']},
        'folder_id':{'type':'integer'},'group_id':{'type':'integer'},'message_id':{'type':'integer'},'topic_id':{'type':'integer'},'text':{'type':'string'},
        'destination':{'type':'string','enum':['test','project']},'task_id':{'type':'string'},
        'scope':{'type':'string','enum':['message','topic']},'link':{'type':'string'},'query':{'type':'string'},
        'unnecessary_input_ids':{'type':'array','items':{'type':'string'},'description':'Explicit caller instruction that listed unsupported source input identities are unnecessary. Never infer this exclusion.'},
        'selection_id':{'type':'string'},'continuation':{'type':'string'},'search_id':{'type':'string'},
        'choice_id':{'type':'string'},'choice':{'type':'integer','minimum':1},'page_size':{'type':'integer','minimum':1,'maximum':100}},
        'required':['action'],'additionalProperties':False}}

async def serve(application, source, sink):
    while line := await asyncio.to_thread(source.readline):
        request = {}
        try:
            decoded = json.loads(line)
            if not isinstance(decoded, dict):
                raise ValueError('MCP request must be an object')
            request = decoded
            method=request['method']
            if 'id' not in request:
                continue
            if method == 'initialize':
                result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'telegram-codex','version':'0.1.0'}}
            elif method == 'ping':
                result={}
            elif method == 'tools/list':
                result={'tools':[TOOL]}
            elif method == 'tools/call' and request['params']['name']=='telegram':
                outcome=await application.handle(request['params']['arguments'])
                result={'content':[{'type':'text','text':json.dumps(outcome)}], 'isError':outcome.get('status')=='blocked'}
            else:
                raise ValueError('Unknown MCP method or tool')
            response={'jsonrpc':'2.0','id':request['id'],'result':result}
        except (ValueError, KeyError, TypeError) as exc:
            response={'jsonrpc':'2.0','id':request.get('id'), 'error':{'code':-32602,'message':str(exc)}}
        sink.write(json.dumps(response)+'\n')
        sink.flush()
