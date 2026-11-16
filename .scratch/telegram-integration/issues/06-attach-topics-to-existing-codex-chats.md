# 06: Attach topics to existing Codex chats

**What to build:** Use #link to choose an existing chat from the assigned project and continue it from the Telegram topic.

**Blocked by:** 05: Route task topics into real Codex projects.

**Status:** needs-info

- [x] Present a numbered selection containing only chats from the group's assigned project.
- [x] Validate the selected identifier against the presented choices and project; reject stale or invalid choices without rebinding.
- [x] Continue the selected chat using its stable identifier and retained task folder.
- [x] Context text or display-name changes cannot silently relink a topic.
- [x] Acceptance tests demonstrate linking, invalid choices, and subsequent work/results through the shared interface.


## Answer

Implemented project-only numbered chat choices and explicit topic linkage through the shared application interface, with exact-source Telegram command normalization. Selection and every subsequent run revalidate folder access, project identity, and current chat membership. A stable existing chat and task folder survive restart; duplicate topic ownership, stale/invalid choices, ordinary context text, and foreign canonical project IDs cannot rebind. Unassigned legacy chats require a uniquely catalog-owned exact cwd, with a distinct honest placement status.

Nine application tests and a scoped paginated subprocess adapter contract pass. See [chat linking](../../../docs/chat-linking.md) for the API, membership basis, limitations, and concrete live proposal. Acceptance boxes describe automated evidence; live Telegram selection/continuation remains unperformed and this ticket stays needs-info pending explicit live authorization and evidence.

## Review regression fix

Explicit follow-ups now verify that the saved task still owns its current topic binding and that the linked chat has no foreign topic owner before retrieving source context or invoking Codex. A shared-interface regression reproduces chat A moving from topic 2 to topic 9 after topic 2 switches to chat B: the superseded task ID is rejected without a Codex action, and later ordinary tasks continue B in topic 2 and A in topic 9. Live acceptance remains pending.
