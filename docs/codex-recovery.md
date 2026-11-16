# Codex action recovery

Every chat creation and turn start has a durable intent before its external request.
The turn intent includes a fresh UUID sent as `clientUserMessageId`; this is a
correlation value, **not an idempotency key**. The accepted turn ID is committed
before the adapter waits for completion. Follow-ups clear only the new run's
identities, preserving prior run artifacts.

The Codex adapter exposes `TurnObservation(turn_id, status, result, reason)` through
`observe_turn` and `find_turn`. History readback follows all turn/item pages,
fetches deferred output explicitly, and uses the same structured-result parser as
live completion. A completed turn whose result cannot be recovered stays completed
with a result blocker; it must never be run again merely to obtain reporting text.
An absent or ambiguous client ID cannot prove that a start failed.

A lost chat-creation response can remain unresolved: the protocol offers no caller
thread ID or creation idempotency key. Project, title, working directory and time
similarity do not prove ownership. An unknown create is blocked, never replaced.

Before starting, the adapter checks current metadata and paginated turns on the
owned/resumed connection for active work. A brand-new chat retained on its
creation connection has no persisted history before its first user message;
only that first owned start skips turn-history readback, while retaining the
metadata guard. Resumed chats never inherit this exception. `notLoaded` and direct-input capability
are not proof of idleness. There is no atomic expected-idle start operation; a
concurrent desktop start after this check remains a protocol limitation. Do not
operate the listener and desktop on the same chat concurrently.

Interruption uses the exact accepted chat/turn on its currently owned live
connection. One stdout reader dispatches correlated responses and events, allowing
an interrupt while completion is awaited. An interrupt acknowledgment is not a
terminal-status observation. After restart, interruption without a live owner
blocks because cross-process control remains unverified.

## Evidence and remaining live checks

Hermetic subprocess contracts exercise accepted-ID persistence, paginated/deferred
history, exact client-ID matching, malformed completed output, and concurrent
owned-connection interruption. Application tests use real SQLite/task folders.
These checks establish integration behavior, not production-server guarantees.

Read-only installed-server evidence in
`/tmp/telegram-implementation-research/codex-recovery-readonly-probe.json` recovered
a completed structured result through paginated turn/item history. That existing
user message had a null client ID. A real supplied-client-ID persistence test and
owned-connection interruption/terminal-observation test remain required. No schema
inspection or fake response is proof of those capabilities. Coordinate live probes
with the parent task so they cannot overlap another listener or Codex test.
