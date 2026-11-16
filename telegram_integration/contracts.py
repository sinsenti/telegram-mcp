from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

class Blocked(Exception):
    """An action cannot proceed safely; caller receives the reason."""

@dataclass(frozen=True)
class GroupMetadata:
    group_id: int
    name: str

@dataclass(frozen=True)
class Attachment:
    media_id: str
    original_name: str
    mime_type: str | None = None
    size: int | None = None

@dataclass(frozen=True)
class TaskInput:
    input_id: str
    source_group_id: int
    source_message_id: int
    media_id: str
    original_name: str
    mime_type: str | None
    path: str
    family: str
    sha256: str
    size: int
    explicitly_unnecessary: bool = False

@dataclass(frozen=True)
class InputEvidence:
    input_id: str
    outcome: str
    evidence: str

@dataclass(frozen=True)
class Message:
    group_id: int
    message_id: int
    text: str
    has_attachment: bool = False
    topic_id: int | None = None
    reply_to_id: int | None = None
    is_topic_root: bool = False
    attachment: Attachment | None = None

@dataclass(frozen=True)
class Context:
    messages: tuple[Message, ...]
    complete: bool = True
    reason: str | None = None

@dataclass(frozen=True)
class RunResult:
    explanation: str
    markdown: str
    turn_id: str
    input_evidence: tuple[InputEvidence, ...] = ()
    status: str = "completed"

class TelegramAdapter(Protocol):
    async def topic_title(self, group_id: int, topic_id: int) -> str: ...
    async def rename_topic(self, group_id: int, topic_id: int, title: str) -> None: ...
    async def create_reference(self, group_id: int, topic_id: int, text: str) -> str: ...
    async def reference(self, group_id: int, topic_id: int, message_id: str) -> dict: ...
    async def edit_reference(self, group_id: int, topic_id: int, message_id: str, text: str) -> None: ...
    async def pin_reference(self, group_id: int, topic_id: int, message_id: str) -> None: ...
    async def group_metadata(self, group_id: int) -> GroupMetadata: ...
    async def allowed_groups(self, folder_id: int) -> set[int]: ...
    async def message(self, group_id: int, message_id: int) -> Message: ...
    async def context(self, group_id: int, message_id: int, scope: str) -> Context: ...
    async def download(self, group_id: int, message_id: int, attachment: Attachment, file) -> None: ...
    async def resolve_link(self, link: str) -> Message: ...
    async def search(self, group_id: int, query: str) -> tuple[Message, ...]: ...
    async def send_text(self, group_id: int, message_id: int, text: str, topic_id: int | None) -> str: ...
    async def send_document(self, group_id: int, message_id: int, document: Path, topic_id: int | None) -> str: ...

class CodexAdapter(Protocol):
    async def list_chats(self, project_id: str, cwd: Path) -> list[dict]: ...
    async def observe_chat(self, chat_id: str, cwd: Path) -> dict: ...
    async def aclose(self) -> None: ...
    async def create_chat(self, cwd: Path, project_id: str | None = None) -> str: ...
    async def run(self, chat_id: str, cwd: Path, prompt: str, inputs: tuple[TaskInput, ...] = ()) -> RunResult: ...
