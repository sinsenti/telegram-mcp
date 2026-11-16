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
