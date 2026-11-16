# 13: Reconcile uncertain Codex actions after crashes

**What to build:** Recover when Codex chat creation or execution succeeds but its acknowledgment is lost, avoiding blind duplicate chats or work.

**Blocked by:** 09: Queue requests with fixed context and withdrawal.

**Status:** claimed

- [ ] Persist outgoing operation intent and recoverable chat/turn identities around creation and execution transitions.
- [ ] Inject remote success followed by lost acknowledgment for chat creation and turn start/completion, not only ordinary failures.
- [ ] Reconcile through available Codex evidence before retrying; continue a known chat/turn instead of creating a replacement.
- [ ] Expose an unresolved recovery blocker when the outcome cannot be determined; do not claim strict exactly-once behavior.
- [ ] Demonstrate restart recovery using real durable storage and observable Codex effects through the shared interface.

## Comments

2026-11-16 implementation: durable create intent and UUID turn correlation precede
external requests; accepted turn IDs are committed before completion is awaited.
The adapter pages exact turn/item history, fetches deferred output, preserves
completed-with-unusable-result status, and dispatches interrupt requests on the
live owning connection through one stdout reader. Real SQLite reconstruction
checks cover remote-success/lost-create-ack and accepted-turn/lost-completion-ack.
Recovery entrypoint and missing-acceptance correlation scenarios are shared with
ticket 11. See `docs/codex-recovery.md`.

Live supplied-client-ID persistence and same-owner interruption/terminal readback
are pending a coordinated parent-run probe; no live clients were started by this
implementation. Schema availability and fake contracts are not live evidence.
Unknown create, absent/ambiguous correlation, and unavailable cross-process control
remain visible blockers. The pre-start active-work check is not atomic against a
concurrent desktop start.
