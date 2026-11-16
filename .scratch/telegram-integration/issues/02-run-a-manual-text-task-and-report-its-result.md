# 02: Run a manual text task and report its result

**What to build:** Select a Telegram text message in an allowed group, run its task in the explicitly chosen ignored test task workspace, and return an explanation and Markdown result to the source.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Before coding, review the full monitoring lifecycle in the spec and retain one shared application interface for manual requests and later listener events.
- [ ] Connect the existing Telegram account, select the Codex folder by stable identity, and enforce effective membership for every resolved read and write destination.
- [ ] Historical selected text is available; requests outside allowed groups expose no content and perform no Telegram action.
- [ ] Create a task folder and Codex chat, return the explanation and generated Markdown to the original message, and retain the actual chat identifier.
- [ ] A manual follow-up reuses that task folder and chat; the ignored test destination is explicit and never a silent fallback for a requested real project.
- [ ] Respect existing production model/permission settings and surface permission or execution blockers without claiming completion.
- [ ] Provide a runnable local entry point and setup instructions without a VPS requirement; include the thin MCP transport check.
- [ ] Acceptance tests use the shared application interface with real temporary SQLite and task folders; live actions require explicit test authorization.
