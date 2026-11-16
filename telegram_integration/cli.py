"""Local CLI and MCP entry points; no external activity occurs at import time."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from telethon import TelegramClient
from .application import Application
from .codex import CodexAppServer
from .telegram import TelethonAdapter
from .transport import serve

async def run(args):
    root=Path(args.root).resolve()
    local=root/'.local'
    local.mkdir(mode=0o700,parents=True,exist_ok=True)
    local.chmod(0o700)
    api_id=os.environ.get('TELEGRAM_API_ID')
    api_hash=os.environ.get('TELEGRAM_API_HASH')
    if not api_id or not api_hash:
        raise ValueError('Set TELEGRAM_API_ID and TELEGRAM_API_HASH from your Telegram account developer application')
    client=TelegramClient(str(local/'telegram'),int(api_id),api_hash,sequential_updates=True)
    app=None
    try:
        if args.mode == 'login':
            await client.start()
            print('Telegram account connected. Session saved under .local/.')
            return
        await client.connect()
        if not await client.is_user_authorized():
            raise ValueError('Telegram login required: run telegram-codex login interactively first')
        adapter=TelethonAdapter(client)
        if args.mode=='folders':
            print(json.dumps(await adapter.folders(),ensure_ascii=False))
            return
        app=Application(local/'state.sqlite',local/'tasks',adapter,CodexAppServer())
        if args.mode=='mcp':
            await serve(app,sys.stdin,sys.stdout)
        else:
            command=json.loads(args.command or sys.stdin.read())
            print(json.dumps(await app.handle(command),ensure_ascii=False))
    finally:
        if app:
            await app.close()
        await client.disconnect()

def main():
    parser=argparse.ArgumentParser(description='Local Telegram/Codex manual task integration')
    parser.add_argument('--root',default='.',help='Integration repository root; test tasks are stored inside .local/tasks')
    parser.add_argument('mode',choices=['login','folders','command','mcp'])
    parser.add_argument('command',nargs='?',help='JSON command; otherwise read command from stdin')
    args=parser.parse_args()
    try:
        asyncio.run(run(args))
    except (ValueError,OSError) as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__':
    main()
