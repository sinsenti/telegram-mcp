# 14: Reconcile uncertain Telegram reporting

**What to build:** Recover source replies, file uploads, and reference updates whose external success is uncertain, without blindly resending results.

**Blocked by:** 08: Start fresh Telegram requests automatically.

**Status:** ready-for-agent

- [ ] Retain durable source destinations, outgoing operation identities, acknowledgments, and integration-generated message identities.
- [ ] Inject remote success plus lost acknowledgment for replies, uploads, and reference changes; reconcile using mechanisms verified in the Telegram adapter.
- [ ] Generated-message echoes never create requests, including when acknowledgment processing races message updates.
- [ ] Known delivered results remain delivered across restart; unknowable outcomes expose a blocker rather than blind repeated sends.
- [ ] Recheck access before every new delivery attempt; retain pending output when its group is disabled.
- [ ] Assert user-visible messages/files/status and duplication behavior through the shared interface with real persistence; attach actual authorized adapter evidence.
