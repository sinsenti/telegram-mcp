"""Local CLI and MCP entry points; no external activity occurs at import time."""
import argparse
import asyncio
import getpass
import json
import os
from pathlib import Path
import sys
import qrcode
from dotenv import dotenv_values
from telethon import TelegramClient
from telethon.errors import PasswordHashInvalidError, RPCError, SessionPasswordNeededError
from .application import Application
from .codex import CodexAppServer
from .catalog import CodexProjectCatalog
from .telegram import TelethonAdapter
from .transport import serve

async def login_qr(client):
    qr = await client.qr_login()
    print('On your phone, open Telegram > Settings > Devices > Link Desktop Device.')
    print('Scan the QR code below and approve the login. Press Ctrl+C to cancel.')
    while True:
        image = qrcode.QRCode(border=4)
        image.add_data(qr.url)
        image.make(fit=True)
        # Telethon requires its update handler to be active before a scan.
        waiter = asyncio.create_task(qr.wait())
        try:
            await asyncio.sleep(0)
            image.print_ascii(invert=True)
            sys.stdout.flush()
            await waiter
            break
        except TimeoutError:
            print('QR code expired. Scan the new code below.')
            await qr.recreate()
        except SessionPasswordNeededError:
            for attempt in range(3):
                password = getpass.getpass('Telegram two-step verification password: ')
                try:
                    await client.sign_in(password=password)
                    break
                except PasswordHashInvalidError:
                    if attempt == 2:
                        raise ValueError('Password was not accepted. Run login-qr again to retry.') from None
                    print('Password was not accepted; try again.')
            break
        finally:
            if not waiter.done():
                waiter.cancel()
            await asyncio.gather(waiter, return_exceptions=True)
    if not await client.is_user_authorized():
        raise ValueError('QR login was not completed. Run login-qr again.')

async def run(args):
    root=Path(args.root).resolve()
    local=root/'.local'
    local.mkdir(mode=0o700,parents=True,exist_ok=True)
    local.chmod(0o700)
    config={**dotenv_values(root/'.env'), **os.environ}
    api_id=config.get('TELEGRAM_API_ID')
    api_hash=config.get('TELEGRAM_API_HASH')
    if not api_id or not api_hash:
        raise ValueError('Fill TELEGRAM_API_ID and TELEGRAM_API_HASH in the repository .env file using your Telegram account developer application')
    client=TelegramClient(str(local/'telegram'),int(api_id),api_hash,sequential_updates=True)
    app=None
    try:
        if args.mode == 'login':
            await client.start()
            print('Telegram account connected. Session saved under .local/.')
            return
        await client.connect()
        if args.mode == 'login-qr':
            if not await client.is_user_authorized():
                await login_qr(client)
            print('Telegram account connected. Session saved under .local/.')
            return
        if not await client.is_user_authorized():
            raise ValueError('Telegram login required: run telegram-codex login-qr or login interactively first')
        adapter=TelethonAdapter(client)
        if args.mode=='folders':
            print(json.dumps(await adapter.folders(),ensure_ascii=False))
            return
        app=Application(local/'state.sqlite',local/'tasks',adapter,CodexAppServer(),catalog=CodexProjectCatalog())
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
    parser.add_argument('mode',choices=['login','login-qr','folders','command','mcp'])
    parser.add_argument('command',nargs='?',help='JSON command; otherwise read command from stdin')
    args=parser.parse_args()
    try:
        asyncio.run(run(args))
    except (ValueError,OSError,RPCError) as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print('Canceled.', file=sys.stderr)
        raise SystemExit(130)

if __name__=='__main__':
    main()
