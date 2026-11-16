import asyncio
import contextlib
import io
import os
import tempfile
import unittest
import qrcode
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from telethon.errors import PasswordHashInvalidError, SessionPasswordNeededError
from telegram_integration.cli import run


class QRLoginTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, outcomes, *, authorized=False, passwords=()):
        class QR:
            url = 'tg://login?token=test-fixture-only'
            refreshed = 0
            waiting = False

            async def wait(self):
                self.waiting = True
                await asyncio.sleep(0)
                outcome = outcomes.pop(0)
                if isinstance(outcome, BaseException):
                    raise outcome
                client.authorized = True

            async def recreate(self):
                self.refreshed += 1

        class Client:
            def __init__(self, session, api_id, api_hash, **kwargs):
                self.session = session
                self.authorized = authorized
                self.disconnected = False
                self.qr_requests = 0
                self.passwords = []

            async def connect(self): pass
            async def disconnect(self): self.disconnected = True
            async def is_user_authorized(self): return self.authorized

            async def qr_login(self):
                self.qr_requests += 1
                return qr

            async def sign_in(self, *, password):
                self.passwords.append(password)
                if password == 'incorrect':
                    raise PasswordHashInvalidError(request=None)
                self.authorized = True

        qr = QR()
        client = None
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'.env').write_text('TELEGRAM_API_ID=12345\nTELEGRAM_API_HASH=fixture\n')

            def create_client(*args, **kwargs):
                nonlocal client
                client = Client(*args, **kwargs)
                return client

            print_ascii = qrcode.QRCode.print_ascii

            def render(code, *args, **kwargs):
                self.assertTrue(qr.waiting, 'The scan listener must be active before showing the QR')
                print_ascii(code, *args, **kwargs)

            with patch('telegram_integration.cli.TelegramClient', side_effect=create_client), \
                 patch.dict(os.environ, {}, clear=True), \
                 patch('getpass.getpass', side_effect=passwords), \
                 patch.object(qrcode.QRCode, 'print_ascii', render), \
                 contextlib.redirect_stdout(output):
                try:
                    await run(SimpleNamespace(root=directory, mode='login-qr'))
                finally:
                    self.assertTrue(client.disconnected)
            self.assertEqual(client.session, str(root/'.local'/'telegram'))
        return client, qr, output.getvalue()

    async def test_scan_authorizes_the_existing_session_without_phone_or_code(self):
        client, qr, output = await self.exercise([True])
        self.assertTrue(client.authorized)
        self.assertTrue(client.disconnected)
        self.assertTrue(qr.waiting)
        self.assertIn('Telegram account connected', output)
        self.assertNotIn(qr.url, output)
        self.assertIn('█', output)

    async def test_expired_qr_refreshes_and_allows_scan(self):
        client, qr, output = await self.exercise([TimeoutError(), True])
        self.assertEqual(qr.refreshed, 1)
        self.assertTrue(client.authorized)
        self.assertIn('expired', output.lower())

    async def test_two_step_password_can_be_retried(self):
        client, _, output = await self.exercise(
            [SessionPasswordNeededError(request=None)], passwords=['incorrect', 'correct'])
        self.assertEqual(client.passwords, ['incorrect', 'correct'])
        self.assertTrue(client.authorized)
        self.assertTrue(client.disconnected)
        self.assertNotIn('correct', output)

    async def test_existing_login_needs_no_qr(self):
        client, _, _ = await self.exercise([], authorized=True)
        self.assertEqual(client.qr_requests, 0)
        self.assertTrue(client.disconnected)

    async def test_cancellation_disconnects_the_client(self):
        with self.assertRaises(asyncio.CancelledError):
            await self.exercise([asyncio.CancelledError()])

    async def test_repeated_wrong_passwords_end_with_a_clear_error(self):
        with self.assertRaisesRegex(ValueError, 'Password was not accepted'):
            await self.exercise([SessionPasswordNeededError(request=None)],
                                passwords=['incorrect'] * 3)
