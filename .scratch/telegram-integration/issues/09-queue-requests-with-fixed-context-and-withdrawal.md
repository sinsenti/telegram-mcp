# 09: Queue requests with fixed context and withdrawal

**What to build:** Accept multiple requests, execute them one at a time in received order, and let the user withdraw work that has not started.

**Blocked by:** 08: Start fresh Telegram requests automatically.

**Status:** resolved

- [x] Persist durable admission order and serialize automatic execution globally, including follow-ups submitted while busy.
- [x] Retain each trigger as its context upper boundary; at execution start read current selected contents through that boundary and freeze the input.
- [x] Later messages and mid-run edits affect only later requests; prior context is not silently used as a new request.
- [x] Deleting a pending trigger or removing its hashtag cancels it without starting Codex; editing a hashtag into an old message still creates nothing.
- [x] Revalidate current access, project assignment, trigger, and required inputs before execution.
- [x] Demonstrate ordered distinct requests, follow-up continuity, snapshot changes, and withdrawal through the shared interface using real persistence.

## Answer

Implemented the durable queue lifecycle through `Application.handle`: immutable admission sequence, per-state OS execution ownership across processes and manual commands, current bounded context capture, same-chat follow-ups, and cancellation for confirmed trigger deletion or marker removal. Telegram history uses the trigger boundary in each remote RPC; network/history/input failures remain blockers rather than cancellation. Request status exposes its durable task binding before external Codex effects. Running/crashed or uncertain create/execute outcomes block later execution until recovery resolves them.

All 93 automated tests passed with real SQLite/task files and external service substitutes. New scenarios cover shared-state process exclusion, process death, restart continuity, corrected/frozen input, later context exclusion, withdrawal, required-context failure and unknown Codex outcome retention. Focused adapter tests verify RPC bounds and confirmed missing versus transport error. No live Telegram client or Codex turn was started for this ticket; prior ticket 08 live acceptance is preserved. Catch-up and detailed recovery/interruption remain tickets 10–13; Telegram delivery reconciliation remains ticket 14. See [queue behavior](../../../docs/queue.md).
