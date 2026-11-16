# 02: Run a manual text task and report its result

**What to build:** Select a Telegram text message in an allowed group, run its task in the explicitly chosen ignored test task workspace, and return an explanation and Markdown result to the source.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Before coding, review the full monitoring lifecycle in the spec and retain one shared application interface for manual requests and later listener events.
- [x] Connect the existing Telegram account, select the Codex folder by stable identity, and enforce effective membership for every resolved read and write destination.
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

Verification: `.venv/bin/python -m unittest discover -s tests -v` passes 18 tests (real temporary SQLite/files, external fakes, fake executable app-server wire contract, Telethon 1.45.0 TL constructor contracts, thin MCP envelope). Editable installation and CLI help were exercised. The initial application, MCP, Telegram, and app-server tracer tests failed before their implementations were added.

## Remaining acceptance

The initial implementation was validated hermetically. The approved live test below subsequently verified account login, selected-folder access, historical selected-text retrieval, and source-specific text/Markdown delivery. Routing, full-discussion retrieval, attachment interpretation, and automatic monitoring remain in their separate tickets.

Run one integration process at a time in this stage. Complete reply/topic retrieval belongs to 03; attachment interpretation to 04; routing and monitoring/reconciliation remain in their existing tickets. Interrupted or uncertain actions retain progress and block follow-up rather than retry blindly. Stable outgoing random-ID persistence/reconciliation is intentionally deferred to 14. Setup and the exact manual commands are in `README.md`.


## Review corrections

Corrected the first-turn lifecycle: `thread/start` retains its owning app-server connection while the application saves the returned chat ID, then starts the first turn on that same connection. Later turns can resume the materialized chat in a fresh process. The adapter releases owned processes on execution completion, failure, or asynchronous application shutdown. A fake wire server now rejects resume before the first turn has created a rollout, proving this regression would fail under the previous lifecycle; it also verifies later-process resume and process cleanup. Configured model and approval settings remain inherited without overrides.

Corrected selected-media classification: Telegram web previews remain text input, including previews that may expose photo/document assets. Genuine attached photos/documents and unsupported media still block the text-only slice. Constructor-contract and application-seam cases cover that distinction and the attachment blocker.

Review verification: all 18 hermetic tests passed before the live acceptance run below.

## Answer

Resolved on 2026-11-16 after the user explicitly approved one new Codex test chat and text/Markdown delivery to the selected Telegram source. [Recorded live evidence](../manual-workflow-live-test.json) identifies folder 8, group `-1003989567415`, topic 2, source message 3, the actual chat/turn IDs, and acknowledged replies 4 and 5. Both replies were read back and verified to reference source message 3 in topic 2. Downloading the uploaded Markdown yielded exactly the local result's 98 bytes and recorded SHA-256. Connected desktop readback confirmed the same completed turn in chat `01a1e427-dc70-7b23-ad61-c2782a815592`.

No extra task, follow-up turn, project rename, or unrelated Telegram write was performed. The test-owned chat and result are retained. [Decision recorded in the implementation map](../map.md#decisions-so-far).
