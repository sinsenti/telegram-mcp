# 08: Start fresh Telegram requests automatically

**What to build:** Run a local listener that announces readiness and turns a fresh eligible #codex message into one automatic task and source-specific result.

**Blocked by:** 03: Read complete discussions and find tasks, 05: Route task topics into real Codex projects.

**Status:** needs-info

- [ ] First activation and newly enabled groups persist activation state, send readiness, and wait for fresh user requests; old markers remain readable context only.
- [ ] Only new user-authored hashtag requests in allowed groups trigger; other authors, ordinary messages, and hashtag-adding edits do not.
- [ ] Duplicate trigger deliveries admit one request; integrate durable admission with discovery progress transactionally.
- [ ] Exclude generated acknowledgments, reports, references, and file captions despite their sharing the user account; sender/outgoing flags alone are insufficient.
- [ ] An unlinked topic creates a project chat and a linked topic continues it; run the task and return its result through the shared module.
- [ ] Include a runnable local listener entry point, status visibility, one thin listener-envelope check, and authorized Telegram update/identity contract verification.

## Implementation evidence

Implemented on `implement/ticket-08` through the shared `Application.handle` seam: durable per-group readiness/cutoffs, self-human original-message eligibility, atomic trigger admission/discovery progress, restart deduplication, generated-message identities and uncertain-send holds, execution ownership separate from admission/status, real-project automatic dispatch, and the runnable `python -m telegram_integration.listener` entry point. Ticket 06 fresh `#link`/number commands and ticket 07 reference creation use the same eligibility/generated-message policy.

Eight focused acceptance checks exercise real SQLite/task folders with substituted external adapters, including admission/status during a blocked Codex turn, manual busy behavior, trigger-bounded context, automatic linked continuation, new-group readiness, source-specific generated report/reference echo exclusion, and a thin listener-envelope translation. Full combined suite and final integration-tip validation are recorded in the implementation handoff.

### Remaining acceptance and proposed live test

No live monitoring activation, readiness write, or automatic Codex turn has been authorized or performed. The authorized Telegram identity/update contract verification remains open, so the ticket stays `needs-info` and acceptance boxes remain unchecked until live evidence exists. See [monitoring operation and limits](../../../docs/monitoring.md).

After code review, request approval for this concrete test: use the already selected folder 8 / group -1003989567415 and its approved linked topic 14, enable readiness without adding groups, inspect the durable cutoff/status, have the user post a fresh human-authored `#codex` message, observe one continuation in the existing help project/chat and its source-specific result, and replay the identical normalized envelope locally to prove no second turn. Do not post a simulated human marker through a connector. Stop the listener after this one test. Do not silently treat adapter substitutes as live identity, update-delivery, or desktop-visibility evidence.

Queue/recovery details remain assigned to tickets 09–14. Uncertain sends hold candidates visibly for ticket 14; running requests left after exit are retained rather than restarted blindly. The current deployment precondition is one Application process per state directory; the listener has process ownership protection, while a separate CLI/MCP instance must not share that database concurrently.
