# 14: Reconcile uncertain Telegram reporting

**What to build:** Recover source replies, file uploads, and reference updates whose external success is uncertain, without blindly resending results.

**Blocked by:** 08: Start fresh Telegram requests automatically.

**Status:** claimed

- [ ] Retain durable source destinations, outgoing operation identities, acknowledgments, and integration-generated message identities.
- [ ] Inject remote success plus lost acknowledgment for replies, uploads, and reference changes; reconcile using mechanisms verified in the Telegram adapter.
- [ ] Generated-message echoes never create requests, including when acknowledgment processing races message updates.
- [ ] Known delivered results remain delivered across restart; unknowable outcomes expose a blocker rather than blind repeated sends.
- [ ] Recheck access before every new delivery attempt; retain pending output when its group is disabled.
- [ ] Assert user-visible messages/files/status and duplication behavior through the shared interface with real persistence; attach actual authorized adapter evidence.


## Comments

Review follow-up: completed report digest is persisted before the first explanation send, then checked before new/replayed uploads and after awaited sends. Lost text acknowledgment plus local report edits now blocks conservatively across restart; restoring original bytes permits recovery. Partial legacy reports lacking original document identity block for inspection. Application delegates matching blocked reporting-request updates to Monitoring and preserves finished historical outcomes. All 110 automated tests passed. Status remains claimed pending actual authorized stable-ID adapter evidence.


Residual payload review fix: upload attempts now pass a verified immutable byte snapshot through the real adapter contract, rather than allowing the SDK to reopen a mutable journal path after awaited peer lookup. The journal retains path/digest and every retry re-reads and verifies original bytes. Application regression proves original remote bytes survive local mutation during delivery and acknowledged recovery remains correct after restart; adapter regression covers path mutation during peer lookup and upload. Installed Telethon accepts bytes with `file_name` and wraps bytes in `BytesIO`; no live client was started. All 112 worktree tests passed, and an independent review found no concrete remaining payload hole. Ticket remains claimed for real stable-ID evidence.
