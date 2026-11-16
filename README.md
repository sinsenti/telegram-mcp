# Local Telegram → Codex integration

The initial implementation runs a manually selected historical **text message** in an explicitly selected local test workspace. It sends an explanation and a Markdown result file back to that source message. Follow-ups retain the actual Codex chat ID and task folder. Python, Telethon, SQLite, and the installed `codex app-server` run locally; no hosted service is needed.

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

Use numeric Telegram marked group IDs (`-100…` for channels/megagroups, negative IDs for basic groups). Message-link parsing, complete reply/topic selection, search, attachment interpretation, project routing, title/pin synchronization, and monitoring are subsequent tickets. A selected attachment or unsupported media blocks this text-only stage instead of being silently omitted. A URL web preview remains part of the selected text and does not count as an attachment. `destination=test` is mandatory for a new task; unresolved real projects never fall back to the test destination. Test tasks run under `<repository>/.local/tasks/<task-id>`. Run from this repository or supply `--root /absolute/path/to/telegram-mcp` before the mode.

The existing Codex login/configuration must already work. The launcher uses installed `codex app-server --stdio`, omits model, sandbox, and approval overrides, and inherits production configuration. It retains the same server connection from chat creation through the first turn while persisting the returned chat ID before execution; later turns resume that materialized chat in a new server process. Owned servers are released after execution, failures, and application shutdown. It uses the actual returned chat ID, asks for a structured completion/blocker result, and only marks a task finished after both Telegram text and Markdown delivery are acknowledged. Any interactive Codex permission request becomes a blocker requiring attention in the chat; this transport never grants permission. A finished follow-up reuses its chat and folder and reports to its newly selected source message in the same group.

## MCP

Configure your MCP client to execute `.venv/bin/telegram-codex --root /absolute/path/to/telegram-mcp mcp` with `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` in its environment. Authenticate with `login` first. The server uses newline-delimited JSON-RPC stdio, supports initialize/tools/list/tools/call, and exposes the `telegram` tool with the same command object as the CLI. Its shared `Application.handle(command)` boundary owns access and task policy; transports only translate envelopes.

## State and verification

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The suite uses real temporary SQLite stores/task folders, fake external adapters, an MCP envelope, Telethon TL constructor contracts, and a fake executable app-server wire peer. It checks historical selection, denied access, fixed task/chat identity across reconstruction, source delivery, production-policy inheritance, permission blockers, partial report uncertainty, and access removal between text and file delivery. It performs no live account/chat actions.

Actual Telegram authentication, folder state, history, and send/upload rights have **not** been validated on the user's account. The preserved approved desktop test validates known-directory Codex create/resume and eventual desktop placement; this implementation has not created another live chat. No live end-to-end acceptance is claimed.

Durable state includes stable folder choice, task/chat identity, source, snapshots, result paths, completion and acknowledged report IDs. An interrupted/blocked task cannot be blindly followed up: inspect its stored status and external chat/source first. Crash reconciliation, stable outgoing random-ID storage, automatic retries, queue recovery, and listener activation are later tickets. A remote action can succeed while acknowledgment is lost; the current stage exposes a blocker and retains progress instead of automatically repeating it. Run a single integration process at a time until the queue stage provides cross-process coordination.
