"""Local app-server launcher. Configured model and permission policy are inherited."""
import asyncio
from collections import deque
from contextlib import asynccontextmanager
import json
from pathlib import Path

from .contracts import Blocked, RunResult


_RESULT_SCHEMA = {
    'type': 'object',
    'properties': {
        'status': {'type': 'string', 'enum': ['completed', 'blocked']},
        'explanation': {'type': 'string'},
        'markdown': {'type': 'string'},
    },
    'required': ['status', 'explanation', 'markdown'],
    'additionalProperties': False,
}


class _Connection:
    def __init__(self, process, timeout):
        self.process = process
        self.timeout = timeout
        self.counter = 0
        self.events = deque()

    async def send(self, message):
        self.process.stdin.write((json.dumps(message) + '\n').encode())
        await self.process.stdin.drain()

    async def receive(self):
        try:
            line = await asyncio.wait_for(self.process.stdout.readline(), self.timeout)
        except TimeoutError as exc:
            raise Blocked('Codex timed out; its external outcome needs inspection before retry.') from exc
        if not line:
            raise Blocked('Codex disconnected; its external outcome needs inspection before retry.')
        try:
            message = json.loads(line)
        except (ValueError, UnicodeDecodeError) as exc:
            raise Blocked('Codex returned an invalid protocol response.') from exc
        if 'method' in message and 'id' in message:
            # This local transport has no interactive human approval surface. Never grant
            # permission implicitly or replace the configured policy to avoid a prompt.
            if message['method'].endswith('/requestApproval'):
                await self.send({'id': message['id'], 'result': {'decision': 'cancel'}})
            else:
                await self.send({'id': message['id'], 'error': {
                    'code': -32601, 'message': 'Interactive request requires human attention'}})
            reason = message.get('params', {}).get('reason') or message['method']
            raise Blocked(f'Codex requires human attention: {reason}. Inspect this chat before continuing.')
        return message

    async def request(self, method, params):
        self.counter += 1
        request_id = self.counter
        await self.send({'id': request_id, 'method': method, 'params': params})
        while True:
            message = await self.receive()
            if message.get('id') == request_id:
                if 'error' in message:
                    raise Blocked(f"Codex rejected {method}: {message['error'].get('message', 'unknown error')}")
                return message['result']
            self.events.append(message)

    async def next_event(self):
        return self.events.popleft() if self.events else await self.receive()


class CodexAppServer:
    def __init__(self, command=None, timeout=600):
        self.command = command or ['codex', 'app-server', '--stdio']
        self.timeout = timeout

    @asynccontextmanager
    async def _connect(self, cwd):
        try:
            process = await asyncio.create_subprocess_exec(
                *self.command, cwd=str(cwd), stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                limit=16 * 1024 * 1024,
            )
        except OSError as exc:
            raise Blocked(f'Cannot launch Codex: {exc}') from exc
        connection = _Connection(process, self.timeout)
        try:
            await connection.request('initialize', {
                'clientInfo': {'name': 'telegram-task-integration', 'version': '0.1.0'},
            })
            await connection.send({'method': 'initialized'})
            yield connection
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), 5)
                except TimeoutError:
                    process.kill()
                    await process.wait()

    async def create_chat(self, cwd: Path) -> str:
        async with self._connect(cwd) as connection:
            result = await connection.request('thread/start', {'cwd': str(cwd)})
            return result['thread']['id']

    async def run(self, chat_id: str, cwd: Path, prompt: str) -> RunResult:
        async with self._connect(cwd) as connection:
            await connection.request('thread/resume', {'threadId': chat_id, 'cwd': str(cwd)})
            result = await connection.request('turn/start', {
                'threadId': chat_id,
                'input': [{'type': 'text', 'text': prompt}],
                'outputSchema': _RESULT_SCHEMA,
            })
            turn_id = result['turn']['id']
            final_text = None
            while True:
                event = await connection.next_event()
                params = event.get('params', {})
                if params.get('threadId') != chat_id:
                    continue
                if event.get('method') == 'item/completed' and params.get('turnId') == turn_id:
                    item = params.get('item', {})
                    if item.get('type') == 'agentMessage' and item.get('phase') != 'commentary':
                        final_text = item.get('text')
                if event.get('method') == 'turn/completed' and params.get('turn', {}).get('id') == turn_id:
                    turn = params['turn']
                    if turn.get('status') != 'completed':
                        raise Blocked(f'Codex turn {turn_id} {turn.get("status")}: {turn.get("error")}')
                    break
            try:
                output = json.loads(final_text or '')
                if output['status'] == 'blocked':
                    raise Blocked(output['explanation'])
                if output['status'] != 'completed' or not isinstance(output['markdown'], str):
                    raise ValueError('invalid result')
                return RunResult(explanation=output['explanation'], markdown=output['markdown'], turn_id=turn_id)
            except (ValueError, TypeError, KeyError) as exc:
                raise Blocked(f'Codex turn {turn_id} finished without a usable structured result; inspect the chat.') from exc
