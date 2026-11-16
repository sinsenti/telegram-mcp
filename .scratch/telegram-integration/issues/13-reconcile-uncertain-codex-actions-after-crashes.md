# 13: Reconcile uncertain Codex actions after crashes

**What to build:** Recover when Codex chat creation or execution succeeds but its acknowledgment is lost, avoiding blind duplicate chats or work.

**Blocked by:** 09: Queue requests with fixed context and withdrawal.

**Status:** resolved

- [x] Persist outgoing operation intent and recoverable chat/turn identities around creation and execution transitions.
- [x] Inject remote success followed by lost acknowledgment for chat creation and turn start/completion, not only ordinary failures.
- [x] Reconcile through available Codex evidence before retrying; continue a known chat/turn instead of creating a replacement.
- [x] Expose an unresolved recovery blocker when the outcome cannot be determined; do not claim strict exactly-once behavior.
- [x] Demonstrate restart recovery using real durable storage and observable Codex effects through the shared interface.

## Comments

2026-11-16 implementation: durable create intent and UUID turn correlation precede
external requests; accepted turn IDs are committed before completion is awaited.
The adapter pages exact turn/item history, fetches deferred output, preserves
completed-with-unusable-result status, and dispatches interrupt requests on the
live owning connection through one stdout reader. Real SQLite reconstruction
checks cover remote-success/lost-create-ack and accepted-turn/lost-completion-ack.
Recovery entrypoint and missing-acceptance correlation scenarios are shared with
ticket 11. See `docs/codex-recovery.md`.

Initial checkpoint before the coordinated probes: supplied-client-ID persistence
and same-owner interruption/terminal readback were pending. The later live
evidence and final outcome are recorded under Answer below. Schema availability
and fake contracts alone are not live evidence.
Unknown create, absent/ambiguous correlation, and unavailable cross-process control
remain visible blockers. The pre-start active-work check is not atomic against a
concurrent desktop start.

The parent-run live probe exposed that turn history is unavailable on an
unmaterialized new chat. A red-first wire regression now reproduces this. The
first start on its retained creation connection uses metadata validation and
skips unavailable persisted history; subsequent/resumed starts retain full
history guards. Probe creation owner was closed without any turn being sent.

## Answer

Resolved with durable intents/accepted identities, exact paginated correlation
and result readback, and the integrated ticket-11 restart reconciler. Real SQLite
reconstruction tests cover remote create success/lost acknowledgment, accepted
turn/lost completion acknowledgment, and missing acceptance recovered by exact
UUID without replaying turn/start. Unknown create, absent/ambiguous correlation
and completed output without a usable result remain blockers, never blind retries.

[Actual adapter evidence](../codex-recovery-live-test.json) verifies supplied UUID
persistence and recovery of the same accepted turn/result. It also separates
acknowledged terminal interruption on a resumed owner from rejected fresh-owner
control and owner-shutdown artifacts. A later wire probe verified fresh-owner
interruption after the exact turn/started event; the adapter now gates control
on that event. No exactly-once or atomic concurrent-start guarantee is claimed. See [recovery behavior](../../../docs/codex-recovery.md).


Final control diagnosis: accepted turn/start response can precede actual control
readiness. Fresh same-owner interruption succeeded after turn/started, with ACK
and interrupted terminal event before owner shutdown. A red-first public wire
regression now covers this registration race; missing readiness and already
terminal turns are bounded/explicit and do not send speculative control RPCs.
Cross-process control was not attempted because the owned route succeeded.
