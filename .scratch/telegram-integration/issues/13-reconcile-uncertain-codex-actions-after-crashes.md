# 13: Reconcile uncertain Codex actions after crashes

**What to build:** Recover when Codex chat creation or execution succeeds but its acknowledgment is lost, avoiding blind duplicate chats or work.

**Blocked by:** 09: Queue requests with fixed context and withdrawal.

**Status:** claimed

- [ ] Persist outgoing operation intent and recoverable chat/turn identities around creation and execution transitions.
- [ ] Inject remote success followed by lost acknowledgment for chat creation and turn start/completion, not only ordinary failures.
- [ ] Reconcile through available Codex evidence before retrying; continue a known chat/turn instead of creating a replacement.
- [ ] Expose an unresolved recovery blocker when the outcome cannot be determined; do not claim strict exactly-once behavior.
- [ ] Demonstrate restart recovery using real durable storage and observable Codex effects through the shared interface.
