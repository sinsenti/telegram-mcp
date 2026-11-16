# 06: Attach topics to existing Codex chats

**What to build:** Use #link to choose an existing chat from the assigned project and continue it from the Telegram topic.

**Blocked by:** 05: Route task topics into real Codex projects.

**Status:** ready-for-agent

- [ ] Present a numbered selection containing only chats from the group's assigned project.
- [ ] Validate the selected identifier against the presented choices and project; reject stale or invalid choices without rebinding.
- [ ] Continue the selected chat using its stable identifier and retained task folder.
- [ ] Context text or display-name changes cannot silently relink a topic.
- [ ] Acceptance tests demonstrate linking, invalid choices, and subsequent work/results through the shared interface.
