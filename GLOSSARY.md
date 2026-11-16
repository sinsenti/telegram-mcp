# Telegram task integration

Language for retrieving Telegram task context and carrying out the work in Codex.

## Language

**Telegram folder**:
A collection of Telegram chats displayed together in the user's chat list.

**Codex folder**:
The Telegram folder selected for the integration. Its project groups become accessible automatically when added to it.

**Allowed group**:
A Telegram project group made accessible to the integration through membership in the Codex folder.
_Avoid_: Approved group, permitted chat

**Project group**:
A Telegram group representing one Codex project. Its topics represent individual Codex chats.

**Task workspace**:
A local area that holds task folders and their inputs and results.
_Avoid_: Project, target repository

**Task result**:
The work returned for a Telegram task, such as a written reply or a generated file.

**Task context**:
The Telegram messages and attachments selected as input for a task.

**Telegram topic**:
A named discussion inside a Telegram group, with its own messages, replies, and attachments.
_Avoid_: Subject, category

**Task folder**:
A folder for one task's inputs and results inside the task workspace. Follow-up work on that task uses the same folder.

**Codex project**:
A project registered in Codex that identifies where task work belongs.

**Codex chat**:
A conversation in Codex containing task instructions, follow-up requests, and results.
_Avoid_: Session

**Chat topic**:
A topic inside a project group that is linked to one Codex chat. Its displayed name follows the Codex chat title.
