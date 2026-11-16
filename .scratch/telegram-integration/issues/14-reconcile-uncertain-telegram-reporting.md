# 14: Reconcile uncertain Telegram reporting

**What to build:** Recover source replies, file uploads, and reference updates whose external success is uncertain, without blindly resending results.

**Blocked by:** 08: Start fresh Telegram requests automatically.

**Status:** resolved

- [x] Retain durable source destinations, outgoing operation identities, acknowledgments, and integration-generated message identities.
- [x] Inject remote success plus lost acknowledgment for replies, uploads, and reference changes; reconcile using mechanisms verified in the Telegram adapter.
- [x] Generated-message echoes never create requests, including when acknowledgment processing races message updates.
- [x] Known delivered results remain delivered across restart; unknowable outcomes expose a blocker rather than blind repeated sends.
- [x] Recheck access before every new delivery attempt; retain pending output when its group is disabled.
- [x] Assert user-visible messages/files/status and duplication behavior through the shared interface with real persistence; attach actual authorized adapter evidence.


## Comments

Review follow-up: completed report digest is persisted before the first explanation send, then checked before new/replayed uploads and after awaited sends. Lost text acknowledgment plus local report edits now blocks conservatively across restart; restoring original bytes permits recovery. Partial legacy reports lacking original document identity block for inspection. Application delegates matching blocked reporting-request updates to Monitoring and preserves finished historical outcomes. All 110 automated tests passed. Status remains claimed pending actual authorized stable-ID adapter evidence.


Residual payload review fix: upload attempts now pass a verified immutable byte snapshot through the real adapter contract, rather than allowing the SDK to reopen a mutable journal path after awaited peer lookup. The journal retains path/digest and every retry re-reads and verifies original bytes. Application regression proves original remote bytes survive local mutation during delivery and acknowledged recovery remains correct after restart; adapter regression covers path mutation during peer lookup and upload. Installed Telethon accepts bytes with `file_name` and wraps bytes in `BytesIO`; no live client was started. All 112 worktree tests passed, and an independent review found no concrete remaining payload hole. Ticket remains claimed for real stable-ID evidence.


## Answer

Resolved after authorized actual Telegram adapter verification on 2026-11-16 in selected folder 8, group `-1003989567415`, topic 21. Prior stable-ID text and upload replays each preserved one remote message (38 and 39). The final immutable-payload proof captured the completed Markdown bytes, changed the source path inside each actual SDK upload hook, and verified the SDK received the original immutable bytes and filename. A lost acknowledgment was injected after the real first SendMedia response; replay with the same random ID returned the same message 40. Topic readback found exactly one matching file, and downloading it confirmed the original SHA-256 while the local source remained changed. No Codex chat or turn was created; the serialized Telegram client was disconnected and handed off before the next test.

[Final live evidence](../frozen-report-delivery-live-test.json) records both real upload attempts, matching UpdateMessageID mappings, original/downloaded hashes, the mutation hash, one-file count, and the preserved earlier text/upload replay evidence. The new receipt was saved before remote effects and left in `.local/frozen-payload-live-v1.json` to prevent blind reruns. Application tests establish restart recovery, reply/file/reference lost acknowledgments, generated echoes, held human requests, current access/account checks, unchanged/changed report recovery, conservative legacy blockers and historical queue-outcome preservation using real SQLite and task files. Actual adapter proof establishes stable same-peer random-ID replay and immutable SDK upload payloads; unknowable outcomes still block rather than claiming strict exactly-once delivery. See [recovery behavior](../../../docs/report-recovery.md).
