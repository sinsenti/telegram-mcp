# 08: Start fresh Telegram requests automatically

**What to build:** Run a local listener that announces readiness and turns a fresh eligible #codex message into one automatic task and source-specific result.

**Blocked by:** 03: Read complete discussions and find tasks, 05: Route task topics into real Codex projects.

**Status:** claimed

- [ ] First activation and newly enabled groups persist activation state, send readiness, and wait for fresh user requests; old markers remain readable context only.
- [ ] Only new user-authored hashtag requests in allowed groups trigger; other authors, ordinary messages, and hashtag-adding edits do not.
- [ ] Duplicate trigger deliveries admit one request; integrate durable admission with discovery progress transactionally.
- [ ] Exclude generated acknowledgments, reports, references, and file captions despite their sharing the user account; sender/outgoing flags alone are insufficient.
- [ ] An unlinked topic creates a project chat and a linked topic continues it; run the task and return its result through the shared module.
- [ ] Include a runnable local listener entry point, status visibility, one thin listener-envelope check, and authorized Telegram update/identity contract verification.
