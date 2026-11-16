# 03: Read complete discussions and find tasks

**What to build:** Read a selected message with its replies or a whole topic, or search allowed groups and choose the intended task.

**Blocked by:** 02: Run a manual text task and report its result.

**Status:** claimed

- [x] Message and topic links preserve their distinct scopes and validate the actual resolved group.
- [x] Retrieve historical replies and complete topic history with full text, explicit continuation, and visible completeness; no silent truncation.
- [x] Text search exposes multiple matches for user selection before execution.
- [x] Reading a topic does not automatically add unrelated conversations; all further selections obey the same folder rule.
- [x] Demonstrate the complete read/select/execute/report workflow through the shared interface for both selections, including missing-context blockers.
- [ ] Add focused Telegram contract evidence for actual history, reply, topic, and link behavior when an authorized test account/group is available.

## Comments

Claimed on implement/ticket-03; approved application testing seam. Live test scope is read-only for the existing selected test source, replies, and topic; no further Codex turn or Telegram write is authorized.

## Implementation evidence

Implemented the shared Application.handle read/search/select/task workflow with message-plus-transitive-replies and whole-topic scopes. Full text and reply identities survive stored presentation pagination and process reconstruction. Execution rereads the complete selected scope, snapshots the run inputs, and blocks missing context, incomplete ancestry, and attachments pending ticket 04. Explicit numeric search choices are validated against presented pages, current access, and fresh retrieval before any Codex effect. Search alone never executes. Public/private links resolve actual group identity and validate explicit thread IDs; General is handled separately from non-General topics.

The adapter uses explicit raw GetReplies/GetHistory/Search pages with current folder checks before each RPC, avoiding per-buffered-message folder refresh. Raw history exhausts until an empty page, checks destination identity and pagination progress, preserves service/root messages, and filters whole-topic candidates to selected-message descendants where requested. The MCP tool schema exposes the same commands. Usage: [manual context commands](../../../docs/manual-context.md).

TDD tracer failures were observed for multi-message task execution, numbered search, unseen paginated search choices, private thread links, and General public links before their implementations. The final full hermetic suite passes 26 tests, including real temporary SQLite/task folders, full long Unicode text across restart, scope-specific task/report behavior, missing/deleted context, revoked continuation, multipage raw history, nested reply exclusion, General filtering, and peer-scoped search. Existing task02 behavior remains passing.

## Remaining acceptance

Status remains claimed. [Read-only live evidence](../discussion-read-live-test.json) verified source3 plus replies4/5, topic2 including its service message, and the private thread/message link in allowed folder8/group-1003989567415. That successful evidence used the pre-raw-pagination Telethon iterator. The final raw-page implementation's bounded read attempt failed during current folder membership revalidation (Telethon iter_dialogs: ValueError Request was unsuccessful 1 time(s), with request_retries=0). Therefore final raw-page live acceptance is still pending; the earlier read is not presented as final-adapter proof.

No additional Codex turn/chat, Telegram write, General-topic scan, public-group read, or unrelated history was performed. Nested/sibling reply fixtures, historical multi-page behavior, General, and public-link resolution are hermetic contracts rather than live fixtures. Complete execute/report for both selections is demonstrated through controlled external adapters; the already spent live one-chat authorization was not reused. Parent can run the prepared bounded read-only verification script after merge without reauthentication.
