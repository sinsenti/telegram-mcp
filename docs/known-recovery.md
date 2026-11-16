# Recover known task progress

Call the shared Application boundary with `{"action":"recover"}` after reopening the same SQLite database and task workspace. An optional `task_id` limits the pass to one task. The listener runs one recovery pass after readiness and catch-up, before starting its dispatch worker. Recovery takes the same operating-system execution lock as dispatch and manual execution: another live worker makes it return `busy`, even from another process.

Pending requests retain their original admission sequence and are dispatched by `dispatch_pending` after recovery. A worker claim that never bound a task is returned to pending; task binding is durable before any task effect. Captured requests retain their task/project/chat identities, run number, downloaded originals and bounded context. A fully captured snapshot can continue only after validating saved hashes, current access and destination. Interrupted input capture is blocked rather than recaptured from edited Telegram history.

Completed execution and Telegram delivery are separate milestones. The structured result is saved before project-placement checks and reporting. Recovery uses that saved result or observes the exact known Codex turn. It never starts another turn merely to obtain output for a completed task. Completed turns with malformed final output remain terminal and blocked. Known interrupted and failed turns retain a clear blocker; in-progress or unknown observations retain their unresolved execution identity.

A lost turn-start acknowledgment can be correlated using the original durable client request UUID. A missing or ambiguous match is blocked and never replayed. A lost chat-create acknowledgment has no authoritative caller identity and remains blocked without creating a replacement chat.

Reporting delegates to `reconcile_reports` and its durable Telegram operation journal. It retains the original group, source reply, topic, payload identity and confirmed message IDs. Each new operation revalidates access. An acknowledged explanation or document is never repeated. Report recovery updates only the request for that exact task run, leaving earlier queue outcomes intact.

Access-paused tasks remain paused after restart or re-addition. Recovery can observe their known Codex turn and save a terminal result without starting work or sending Telegram reports. It does not restore authority to resume them. After readiness is re-established, a fresh request may continue the remembered chat following an observed terminal interruption or failure.

## Verification and limits

`tests/test_known_recovery.py` reconstructs Application against real SQLite and task folders, exercising captured snapshots, queue order and task binding, execution ownership, accepted turn identity, lost start/create responses, terminal result persistence, malformed output and partial reports. External Telegram/Codex adapters are controlled fixtures. Production history parsing and operation correlation are also covered by adapter wire tests in ticket 13; Telegram reporting uses ticket 14's journal and immutable payload handling.

These hermetic restart tests do not establish cross-process interruption of desktop-owned Codex work or global uniqueness of caller UUIDs; live adapter evidence is recorded separately in ticket 13. Recovery conservatively blocks where authoritative readback is unavailable. No new live Codex turn or Telegram client was started for this ticket's implementation checks.
