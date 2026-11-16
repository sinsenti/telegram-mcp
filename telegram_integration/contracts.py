from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

class Blocked(Exception):
    """An action cannot proceed safely; caller receives the reason."""

@dataclass(frozen=True)
class Message:
    group_id: int
    message_id: int
    text: str
    has_attachment: bool = False
    topic_id: int | None = None

@dataclass(frozen=True)
class RunResult:
    explanation: str
    markdown: str
    turn_id: str

class TelegramAdapter(Protocol):
    async def allowed_groups(self, folder_id: int) -> set[int]: ...
    async def message(self, group_id: int, message_id: int) -> Message: ...
    async def send_text(self, group_id: int, message_id: int, text: str, topic_id: int | None) -> str: ...
    async def send_document(self, group_id: int, message_id: int, document: Path, topic_id: int | None) -> str: ...

class CodexAdapter(Protocol):
    async def create_chat(self, cwd: Path) -> str: ...
    async def run(self, chat_id: str, cwd: Path, prompt: str) -> RunResult: ...
