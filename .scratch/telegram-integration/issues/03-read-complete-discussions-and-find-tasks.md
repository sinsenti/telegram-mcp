# 03: Read complete discussions and find tasks

**What to build:** Read a selected message with its replies or a whole topic, or search allowed groups and choose the intended task.

**Blocked by:** 02: Run a manual text task and report its result.

**Status:** resolved

- [x] Message and topic links preserve their distinct scopes and validate the actual resolved group.
- [x] Retrieve historical replies and complete topic history with full text, explicit continuation, and visible completeness; no silent truncation.
- [x] Text search exposes multiple matches for user selection before execution.
- [x] Reading a topic does not automatically add unrelated conversations; all further selections obey the same folder rule.
- [x] Demonstrate the complete read/select/execute/report workflow through the shared interface for both selections, including missing-context blockers.
- [x] Add focused Telegram contract evidence for actual history, reply, topic, and link behavior when an authorized test account/group is available.

## Comments

Claimed on implement/ticket-03; approved application testing seam. Live test scope is read-only for the existing selected test source, replies, and topic; no further Codex turn or Telegram write is authorized.

## Implementation evidence

Implemented the shared Application.handle read/search/select/task workflow with message-plus-transitive-replies and whole-topic scopes. Full text and reply identities survive stored presentation pagination and process reconstruction. Execution rereads the complete selected scope, snapshots the run inputs, and blocks missing context, incomplete ancestry, and attachments pending ticket 04. Explicit numeric search choices are validated against presented pages, current access, and fresh retrieval before any Codex effect. Search alone never executes. Public/private links resolve actual group identity and validate explicit thread IDs; General is handled separately from non-General topics.

The adapter uses explicit raw GetReplies/GetHistory/Search pages with current folder checks before each RPC, avoiding per-buffered-message folder refresh. Raw history exhausts until an empty page, checks destination identity and pagination progress, preserves service/root messages, and filters whole-topic candidates to selected-message descendants where requested. The MCP tool schema exposes the same commands. Usage: [manual context commands](../../../docs/manual-context.md).

TDD tracer failures were observed for multi-message task execution, numbered search, unseen paginated search choices, private thread links, and General public links before their implementations. The final full hermetic suite passes 26 tests, including real temporary SQLite/task folders, full long Unicode text across restart, scope-specific task/report behavior, missing/deleted context, revoked continuation, multipage raw history, nested reply exclusion, General filtering, and peer-scoped search. Existing task02 behavior remains passing.

## Remaining acceptance

Status is **needs-info**. [Read-only live evidence](../discussion-read-live-test.json) verified source3 plus replies4/5, topic2 including its service message, and the private thread/message link in allowed folder8/group-1003989567415. That successful evidence used the pre-raw-pagination Telethon iterator. Subsequent final-adapter attempts encountered a Telegram `FloodWaitError` on `GetDialogsRequest`, then timed out at 60 seconds waiting for folder refresh via `GetDialogFiltersRequest`. Final raw-page live acceptance remains pending; the earlier read is not presented as final-adapter proof. No further immediate retries are planned.

No additional Codex turn/chat, Telegram write, General-topic scan, public-group read, or unrelated history was performed. Nested/sibling reply fixtures, historical multi-page behavior, General, and public-link resolution are hermetic contracts rather than live fixtures. Complete execute/report for both selections is demonstrated through controlled external adapters; the already spent live one-chat authorization was not reused. Parent can run the prepared bounded read-only verification script after merge without reauthentication.

## Review corrections

Review fixes reject an explicitly different follow-up group before retrieval/execution, omit `top_msg_id` for General-topic text and document replies, and refresh explicit-folder/shared-chatlist membership by resolving only included peers instead of repeatedly enumerating the entire account's dialogs. Exclusions, actual peer identity, group type, and fresh membership checks remain enforced. Dynamic group filters retain their existing evaluation.

Both review findings were rechecked after merge. The final root suite passes 37 tests, including the existing QR-login checks; the ticket implementation and review-fix worktree suite passes 31. Ticket 04 is unblocked by the final live retrieval acceptance below.

## Answer

Resolved after the bounded final-adapter read succeeded on 2026-11-16. The [current live evidence](../discussion-read-live-test.json) uses the explicit raw-page adapter: message scope returns IDs 3, 4, 5; topic scope returns IDs 2, 3, 4, 5; both are complete, and the private link resolves group/topic/source identities correctly. Earlier rate-limit/timeout attempts above are retained as history and are superseded by this successful final read. No new chat, turn, or Telegram write was needed. [Decision recorded in the implementation map](../map.md#decisions-so-far).
