# Topic names and chat references

`Application.handle({"action":"sync_reference","task_id":"…"})` reconciles a known project task's topic. `sync_references` refreshes every linked topic; the listener calls it every 30 seconds by default. New chat/link and running/completion transitions also reconcile references. Each invocation performs one bounded metadata observation. Repeated listener polls catch later desktop changes without starting or resuming Codex turns. Explicit calls also work after reopening the local database.

Codex `thread/read` with `includeTurns:false` supplies the canonical `Thread.name`. A missing name leaves `Title pending` and keeps the existing topic title. The previous known name survives a missing value or observation failure. The integration does not substitute prompt previews, rename Codex chats, create replacement chats, or alter stable project/chat/topic routing identities. Topic names are truncated at a Unicode code point boundary to 128 UTF-8 bytes. The complete title is retained in the reference.

The reference includes the current catalog project name, full chat title, task status, `codex://threads/<chat-id>`, and a plain chat ID fallback. Telegram/device handling of custom links remains unverified, so the searchable title and ID are always present. A reference exceeding Telegram's message limit produces an explicit failure rather than silently truncating it.

`status` exposes durable `reference_sync.observation`, `title`, `reference`, and `pin` outcomes independently of task execution. Telegram title readback, reference content, and the known message's pinned flag confirm writes. Access is refreshed before every operation; removal from the selected folder stops subsequent operations. Only the remembered connector reference may be edited or pinned. No unrelated messages are unpinned.

A failed rename or pin leaves the completed task intact and reports its own reason. Known message edits and pins reconcile against external readback on the next sync. Reference creation is recorded as uncertain before sending: a lost acknowledgment without a saved message ID requires inspection and is never blindly retried. Stable outgoing identities reconcile lost acknowledgments through the outgoing journal; legacy outcomes without an identity remain blocked for inspection. A missing/deleted or inaccessible saved reference is reported for inspection; the connector does not silently create another pin.

## Remaining live acceptance

No live topic rename, pin, reference send, or Codex name mutation was performed for ticket 07. The implementation suite checks the shared application boundary with real SQLite/files, a Codex wire fixture and narrow Telegram RPC contracts. Approval is still needed for an explicitly selected test chat/topic to:

1. Rename that same chat in the desktop, observe the canonical name through standalone metadata polling, and restore it if restoration is authorized.
2. Synchronize its topic name and create/edit/pin the connector reference; read back title, content, source topic and pin state.
3. Confirm partial permission failure reporting and access removal in the configured test environment where authorized.

Current proposed existing binding: chat `01a1e473-8c30-7821-99f1-6279e9947a2a`, Telegram group `-1003989567415`, topic `14`, folder `8`, task `adf97cc4bc1043d294804cf9650af812`. This identifies the proposed verification scope and grants no authorization to mutate it.

## Completed controlled live acceptance

The desktop-origin title change on the linked owned test chat was observed through canonical Thread.name, and the actual saved name propagated to the Telegram topic and full pinned project/status/chat reference. The original name was restored and both destinations verified again, reusing reference message 29. The desktop shortened the oversized requested fixture label before saving; synchronization correctly uses that actual canonical saved value. Unicode byte-limit behavior is also covered by unit/adapter checks. [Evidence](../.scratch/telegram-integration/title-reference-live-test.json). Ticket 07 is resolved. Periodic listener synchronization also confirmed a null-title chat retains its topic identity and a pending-title reference without a replacement chat.
