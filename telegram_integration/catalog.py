"""Refresh saved local projects through the installed experimental app-server API.

Server project identifiers are not legacy desktop-tool project identifiers.
No private desktop state is read and no project/chat is created.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import selectors
import subprocess
import time


class CatalogUnavailable(RuntimeError):
    """The current catalog cannot safely supply a destination."""


@dataclass(frozen=True)
class CodexProject:
    id: str
    name: str
    roots: tuple[Path, ...]


class CodexProjectCatalog:
    def __init__(self, command=None, timeout=10):
        self.command = command or ['codex', 'app-server', '--stdio']
        self.timeout = timeout

    def refresh(self) -> tuple[CodexProject, ...]:
        """Return a newly fetched complete catalog; never fall back to stale data."""
        try:
            with _CatalogConnection(self.command, self.timeout) as connection:
                connection.request('initialize', {
                    'clientInfo': {'name': 'telegram_project_catalog', 'version': '0.1.0'},
                    'capabilities': {'experimentalApi': True},
                })
                connection.send({'method': 'initialized', 'params': {}})
                projects = []
                cursor = None
                seen_cursors = set()
                while True:
                    page = connection.request('project/list', {'cursor': cursor, 'limit': 100})
                    projects.extend(CodexProject(
                        item['id'], item['name'], tuple(Path(root['path']) for root in item['roots'])
                    ) for item in page['data'])
                    cursor = page['nextCursor']
                    if cursor is None:
                        if any(not isinstance(p.id, str) or not p.id or not isinstance(p.name, str)
                               or not p.name or any(not root.is_absolute() for root in p.roots)
                               for p in projects):
                            raise CatalogUnavailable('Codex catalog contains incomplete local project metadata')
                        if len({p.id for p in projects}) != len(projects):
                            raise CatalogUnavailable('Codex catalog contains duplicate project identities')
                        return tuple(projects)
                    if cursor in seen_cursors:
                        raise CatalogUnavailable('Codex catalog pagination did not advance')
                    seen_cursors.add(cursor)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise CatalogUnavailable(f'Unable to refresh Codex project catalog: {error}') from error

    def destination(self, project_id: str) -> Path:
        """Consumer: resolve a known server project ID using current metadata."""
        matches = [project for project in self.refresh() if project.id == project_id]
        if len(matches) != 1:
            raise CatalogUnavailable('The selected Codex project is missing or ambiguous; choose again')
        roots = matches[0].roots
        if len(roots) != 1 or not roots[0].is_absolute():
            raise CatalogUnavailable('The selected Codex project needs an explicit local working directory')
        return roots[0]


class _CatalogConnection:
    def __init__(self, command, timeout):
        self.command, self.timeout = command, timeout
        self.buffer = b''
        self.number = 0

    def __enter__(self):
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        return self

    def send(self, message):
        self.process.stdin.write(json.dumps(message).encode() + b'\n')
        self.process.stdin.flush()

    def request(self, method, params):
        self.number += 1
        self.send({'id': self.number, 'method': method, 'params': params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if b'\n' not in self.buffer:
                if not self.selector.select(max(0, deadline-time.monotonic())):
                    break
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise CatalogUnavailable('Codex catalog server closed before responding')
                self.buffer += chunk
                continue
            line, self.buffer = self.buffer.split(b'\n', 1)
            message = json.loads(line)
            if message.get('id') != self.number:
                continue
            if 'error' in message:
                raise CatalogUnavailable(f'Codex catalog request {method} failed: {message["error"]}')
            return message['result']
        raise CatalogUnavailable(f'Codex catalog request {method} timed out')

    def __exit__(self, *args):
        self.selector.close()
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()
