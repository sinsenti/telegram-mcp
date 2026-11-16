# 02: Run a manual text task and report its result

**What to build:** Select a Telegram text message in an allowed group, run its task in the explicitly chosen ignored test task workspace, and return an explanation and Markdown result to the source.

**Blocked by:** None (can start immediately).

**Status:** needs-info

- [x] Before coding, review the full monitoring lifecycle in the spec and retain one shared application interface for manual requests and later listener events.
- [ ] Connect the existing Telegram account, select the Codex folder by stable identity, and enforce effective membership for every resolved read and write destination.
- [x] Historical selected text is available; requests outside allowed groups expose no content and perform no Telegram action.
- [x] Create a task folder and Codex chat, return the explanation and generated Markdown to the original message, and retain the actual chat identifier.
- [x] A manual follow-up reuses that task folder and chat; the ignored test destination is explicit and never a silent fallback for a requested real project.
- [x] Respect existing production model/permission settings and surface permission or execution blockers without claiming completion.
- [x] Provide a runnable local entry point and setup instructions without a VPS requirement; include the thin MCP transport check.
- [x] Acceptance tests use the shared application interface with real temporary SQLite and task folders; live actions require explicit test authorization.

## Comments

Claimed on implement/ticket-02. Base verified as integration/telegram-codex. Reviewed the monitoring lifecycle before implementation: manual and future event callers share the application boundary; durable task/chat/report identities are retained. Live Telegram actions and new Codex test chats are not authorized.

## Implementation evidence

Implemented the manual text slice in `telegram_integration/`, with `Application.handle(command)` as the shared application boundary. SQLite and task folders are real; folder identity, task/chat IDs, source destinations, input snapshots, results, and acknowledged report IDs survive reconstruction. MCP and CLI call this same boundary. `configure`, `read`, `task`, `followup`, and `status` are supported; tasks require explicit `destination=test`.

Telethon resolves stable folder IDs, effective group membership, and actual peers; both explanation and document effects independently recheck current access, including after file upload. Raw reply requests carry source and topic identity. The Codex stdio adapter creates/resumes actual chat IDs without overriding configured model/permission settings. Permission requests and execution blockers surface as blocked outcomes; execution blockers are also sent to the source while access remains.

Verification: `.venv/bin/python -m unittest discover -s tests -v` passes 12 tests (real temporary SQLite/files, external fakes, fake executable app-server wire contract, Telethon 1.45.0 TL constructor contracts, thin MCP envelope). Editable installation and CLI help were exercised. The initial application, MCP, Telegram, and app-server tracer tests failed before their implementations were added.

## Remaining acceptance

Status remains **needs-info** because actual account login, selected-folder behavior, historical reads, and Telegram source reply/Markdown upload have not been exercised with explicit live authorization. No Telegram messages or Codex chats were created during implementation. The preserved desktop test remains prior evidence only. Checked implementation items above describe hermetic behavior, not live acceptance.

Run one integration process at a time in this stage. Complete reply/topic retrieval belongs to 03; attachment interpretation to 04; routing and monitoring/reconciliation remain in their existing tickets. Interrupted or uncertain actions retain progress and block follow-up rather than retry blindly. Stable outgoing random-ID persistence/reconciliation is intentionally deferred to 14. Setup and the exact manual commands are in `README.md`.
