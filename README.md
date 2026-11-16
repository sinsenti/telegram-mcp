# Local Telegram → Codex integration

Run Telegram tasks locally in Codex using your existing Telegram account and saved Codex projects. A selected Telegram folder contains project groups, and each group’s topics link to individual Codex chats. Manual selections or fresh user-authored `#codex` requests supply historical discussion and attachments; results return as a short reply and Markdown file in the source conversation. Follow-ups retain their actual Codex chat ID and task folder. Python, Telethon, SQLite, and the installed `codex app-server` run locally; no hosted service is needed.

## Setup

From this repository, use Python 3.11 or newer:

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
export TELEGRAM_API_ID='your Telegram application ID'
export TELEGRAM_API_HASH='your Telegram application hash'
.venv/bin/telegram-codex login
.venv/bin/telegram-codex folders
```

Get the API values from your account's [Telegram developer application](https://my.telegram.org). Login uses your existing account and prompts interactively for the phone, code, and two-factor password when required. `login` is the only interactive authentication path; MCP never asks for credentials on its protocol stream. Keep the resulting `.local/telegram.session` private: it represents account access. The `.local/` directory, session, SQLite state, and task inputs/results are ignored by Git. The directory is created with owner-only permissions.

Create your Telegram folder and project groups yourself, enable Topics where desired, then choose the returned stable folder ID. Renaming the folder does not select another folder. This connector restricts its operations; the account itself retains normal Telegram authority. Folder membership is evaluated before reads and each send/upload using explicit include/pin/exclude precedence and supported group filters. A filter relying on inherited mute settings is blocked when effective membership cannot be verified; use explicit included groups for that setup.

```sh
.venv/bin/telegram-codex command '{"action":"configure","folder_id":7}'
.venv/bin/telegram-codex command '{"action":"read","group_id":-1001234567890,"message_id":42}'
.venv/bin/telegram-codex command '{"action":"task","group_id":-1001234567890,"message_id":42,"destination":"test"}'
.venv/bin/telegram-codex command '{"action":"status","task_id":"returned-task-id"}'
.venv/bin/telegram-codex command '{"action":"followup","task_id":"returned-task-id","message_id":43}'
```

Use numeric Telegram marked group IDs (`-100…` for channels/megagroups, negative IDs for basic groups). Run from this repository or supply `--root /absolute/path/to/telegram-mcp` before the mode. `destination=test` explicitly selects the ignored local test workspace. Use `destination=project` for real work: an exact unique group-name match selects an existing Codex project, while absent or ambiguous matches return numbered project choices. No unresolved project falls back to the test destination. Task inputs and results stay under `<repository>/.local/tasks/<task-id>`; routed Codex work runs in the selected project’s working directory. See [project routing](docs/project-routing.md) for assignment commands and placement checks.

[Manual context selection](docs/manual-context.md) supports message links, a message with its replies, complete available topic history, and text search with explicit result choices. Long text is preserved with paginated presentation. [Attachment handling](docs/attachments.md) preserves originals and gives Codex usable text, image, PDF, Word, and spreadsheet inputs. Missing required input or failed interpretation blocks completion; unsupported files remain preserved and require an explicit exclusion when their contents are unnecessary. URL previews remain selected text.

Use `#link` in a project topic to list that project’s existing chats and choose one by number, or use the [linking commands](docs/chat-linking.md). Chat titles synchronize to Telegram topic names, with a pinned project/chat/status reference and searchable chat ID fallback. See [topic references](docs/title-references.md).

The existing Codex login/configuration must already work. The launcher uses installed `codex app-server --stdio`, omits model, sandbox, and approval overrides, and inherits production configuration. It retains the same server connection from chat creation through the first turn while persisting the returned chat ID before execution; later turns resume that materialized chat in a new server process. Owned servers are released after execution, failures, and application shutdown. It uses the actual returned chat ID, asks for a structured completion/blocker result, and only marks a task finished after both Telegram text and Markdown delivery are acknowledged. Any interactive Codex permission request becomes a blocker requiring attention in the chat; this transport never grants permission. A finished follow-up reuses its chat and folder and reports to its newly selected source message in the same group.

## Automatic requests

After authenticating and selecting the folder, start the local listener:

```sh
.venv/bin/python -m telegram_integration.listener --state-directory .local
```

Starting it enables monitoring and sends readiness messages to newly enabled groups. Prepare context in a project topic, then post a fresh `#codex` request yourself. Historical markers, edits adding the marker, forwarded messages, other authors, and generated integration output do not start work. Requests execute one at a time in durable admission order; current context is captured only through each trigger’s message ID. Deleting a pending trigger or removing its marker cancels that request. The listener maintains topic titles and pinned references, catches up in bounded batches, and retains queue progress across restarts. See [monitoring](docs/monitoring.md), [queue behavior](docs/queue.md), and [catch-up](docs/catchup.md).

## MCP

Configure your MCP client to execute `.venv/bin/telegram-codex --root /absolute/path/to/telegram-mcp mcp` with `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` in its environment. Authenticate with `login` first. The server uses newline-delimited JSON-RPC stdio, supports initialize/tools/list/tools/call, and exposes the `telegram` tool with the same command object as the CLI. Its shared `Application.handle(command)` boundary owns access and task policy; transports only translate envelopes.

## State and verification

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The suite uses real temporary SQLite stores/task folders, substituted external adapters, MCP/listener envelopes, Telethon TL contracts, and an executable app-server wire fixture. It checks selection completeness, attachments, routing, source delivery, permission blockers, serial queue ownership, frozen inputs, withdrawal, folder revocation, and restart/lost-acknowledgment recovery. Running this suite performs no live account/chat actions.

Controlled live checks recorded in the [local tracker evidence](.scratch/telegram-integration/) cover authentication, folder-scoped historical retrieval, five input formats, source replies/uploads, existing-project routing and desktop placement, chat linking, desktop-origin title synchronization and pinning, and one genuine human-triggered automatic continuation with duplicate suppression. [Catch-up evidence](.scratch/telegram-integration/catchup-history-live-test.json) verifies bounded real Telegram pagination; it does not establish automatic execution after a live sleep/reconnect. The [known-state restart checks](.scratch/telegram-integration/issues/11-recover-known-task-progress-after-restart.md) use reconstructed local state and controlled external adapters. Committed [frozen report recovery evidence](.scratch/telegram-integration/frozen-report-delivery-live-test.json) verifies real source delivery with acknowledged and lost-acknowledgment outcomes. Active folder-removal interruption and uncertain Codex start recovery retain their specific acceptance limits in tickets 12–13; hermetic tests alone do not prove server behavior.

SQLite retains folder/readiness state, project/topic/chat mappings, ordered request identities, captured inputs, task progress, and outgoing-operation identities. Known outcomes are recovered without repeating completed Codex work. Unknown chat creation or turn outcomes block further execution until reconciled. Telegram report recovery reuses the original destination, payload, account and random ID; it never replaces an unknown send with a fresh identity. Use `status` or `monitor_status` first, then the documented [known-state restart recovery](docs/known-recovery.md), [Codex recovery](docs/codex-recovery.md) and [report recovery](docs/report-recovery.md) paths. There is no strict exactly-once guarantee across Telegram, Codex, and local storage.

A shared execution lock serializes manual and automatic work using the same state database; admission and local status remain responsive. One listener owns a state directory. Keep the listener and desktop from starting work concurrently in the same Codex chat: the protocol’s idle check is not atomic with turn start. Removing a group disables further connector operations, pauses its work and requests interruption using known active identities. Re-addition establishes readiness for fresh requests while old paused requests remain paused; see [folder access](docs/folder-access.md).
