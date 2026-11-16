"""Local listener: translate Telethon envelopes into the shared application seam."""
import argparse
import asyncio
import fcntl
import json
import os
from pathlib import Path
from telethon import TelegramClient, events
from .application import Application
from .catalog import CodexProjectCatalog
from .codex import CodexAppServer
from .telegram import TelethonAdapter

async def deliver(application, event, account_id, kind='new_message'):
    message=event.message
    return await application.handle({'action':'telegram_event','kind':kind,
        'account_id':account_id,'group_id':event.chat_id,'message_id':message.id,
        'sender_id':message.sender_id,'text':message.raw_text or '',
        'edited':bool(getattr(message,'edit_date',None)),
        'forwarded':bool(getattr(message,'fwd_from',None))})

async def listen(application, client, *, sync_references=False):
    account=await application.telegram.self_id()
    ready=asyncio.Event()
    async def receive(event):
        await ready.wait()
        outcome=await deliver(application,event,account)
        print(json.dumps(outcome,ensure_ascii=False),flush=True)
    async def edited(event):
        await ready.wait()
        outcome=await deliver(application,event,account,'edited_message')
        print(json.dumps(outcome,ensure_ascii=False),flush=True)
    client.add_event_handler(receive,events.NewMessage())
    client.add_event_handler(edited,events.MessageEdited())
    async def worker():
        while True:
            outcome=await application.handle({'action':'dispatch_pending'})
            if outcome['status'] not in ('idle','busy'):
                print(json.dumps(outcome,ensure_ascii=False),flush=True)
            await asyncio.sleep(0.25)
    async def refresh():
        while True:
            await asyncio.sleep(30)
            print(json.dumps(await application.handle({'action':'monitor_refresh'}),ensure_ascii=False),flush=True)
            if sync_references:
                print(json.dumps(await application.handle({'action':'sync_references'}),ensure_ascii=False),flush=True)
    tasks=[]
    try:
        outcome=await application.handle({'action':'monitor_enable'})
        print(json.dumps(outcome,ensure_ascii=False),flush=True)
        if outcome['status']!='monitoring':
            raise ValueError('Monitoring activation failed; inspect status before retrying')
        ready.set()
        await client.catch_up()
        tasks=[asyncio.create_task(worker()),asyncio.create_task(refresh())]
        await client.run_until_disconnected()
    finally:
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        client.remove_event_handler(receive)
        client.remove_event_handler(edited)

async def run(args):
    local=Path(args.state_directory).resolve()
    local.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (local/'listener.lock').open('w') as ownership:
        try:
            fcntl.flock(ownership,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('A listener already owns this state directory')
        client=TelegramClient(str(local/'telegram'),int(os.environ['TELEGRAM_API_ID']),os.environ['TELEGRAM_API_HASH'])
        application=None
        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise ValueError('Connect the Telegram account interactively before starting the listener')
            application=Application(local/'state.sqlite',local/'tasks',TelethonAdapter(client),CodexAppServer(),catalog=CodexProjectCatalog())
            if args.folder_id is not None:
                result=await application.handle({'action':'configure','folder_id':args.folder_id})
                if result['status']!='configured': raise ValueError(result.get('reason','Folder setup failed'))
            await listen(application,client,sync_references=args.sync_references)
        finally:
            if application: await application.close()
            await client.disconnect()

def main():
    parser=argparse.ArgumentParser(description='Enable local Telegram monitoring and execute fresh #codex requests')
    parser.add_argument('--state-directory',default='.local')
    parser.add_argument('--folder-id',type=int,help='Explicitly select the Telegram folder on initial setup')
    parser.add_argument('--sync-references',action='store_true',help='Periodically update linked topic titles and pinned references')
    args=parser.parse_args()
    try: asyncio.run(run(args))
    except (ValueError,OSError,KeyError) as error: parser.exit(1,str(error)+'\n')

if __name__=='__main__': main()
