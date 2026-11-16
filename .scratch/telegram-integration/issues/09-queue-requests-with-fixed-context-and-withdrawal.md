# 09: Queue requests with fixed context and withdrawal

**What to build:** Accept multiple requests, execute them one at a time in received order, and let the user withdraw work that has not started.

**Blocked by:** 08: Start fresh Telegram requests automatically.

**Status:** ready-for-agent

- [ ] Persist durable admission order and serialize automatic execution globally, including follow-ups submitted while busy.
- [ ] Retain each trigger as its context upper boundary; at execution start read current selected contents through that boundary and freeze the input.
- [ ] Later messages and mid-run edits affect only later requests; prior context is not silently used as a new request.
- [ ] Deleting a pending trigger or removing its hashtag cancels it without starting Codex; editing a hashtag into an old message still creates nothing.
- [ ] Revalidate current access, project assignment, trigger, and required inputs before execution.
- [ ] Demonstrate ordered distinct requests, follow-up continuity, snapshot changes, and withdrawal through the shared interface using real persistence.
