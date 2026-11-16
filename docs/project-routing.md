# Existing project routing

`Application(database, workspace, telegram, codex, catalog=None)` retains explicit manual test mode. A caller enabling real routing injects `CodexProjectCatalog()` as `catalog`. An absent catalog blocks real routing. The catalog refreshes the installed experimental app-server `project/list`, using server IDs; desktop-tool legacy IDs are a separate namespace. See [catalog evidence](research/project-catalog.md).

Send `action=task`, `destination=project`, and the ordinary source selection. The application reads current allowed-folder membership and group metadata, matches the group's exact name against the current catalog, and remembers the unique existing project ID and its sole local working directory. It creates neither projects nor imports. Topics inherit the assignment. Renaming a group, project, or topic leaves stable identities intact. A removed project or changed root requires a new explicit selection; a same-name replacement never receives work automatically. Existing chats cannot move to a newly selected group destination.

An unresolved name returns `status=project_choice`, `choice_id`, and numbered choices. Send `action=project`, `group_id`, `choice_id`, and `choice` to assign a presented project. Choices are validated against current identities and roots before saving. `action=project` with only `group_id` discovers the current assignment or returns choices. Multiple-root projects require a future explicit root-selection capability and cannot execute here.

An unlinked topic creates one actual Codex chat and one task folder. Later `task` commands in that topic and explicit `followup` commands reuse the durable task/chat/folder. Follow-ups must stay in the same group and topic. Input/result files remain in the task folder, but Codex starts and resumes in the real project's working directory. No test-directory fallback is used. The actual returned chat ID is saved before its first turn, and its owning app-server stays alive through that first turn. Model, approval, and filesystem permission settings remain inherited.

The installed generated experimental `ThreadStartParams` supports `projectId`; `ThreadResumeParams` does not. Creation sends the catalog server ID with `cwd`; continuation resumes the saved actual chat without attempting project reassignment. `thread/read` supplies canonical `projectId`, `cwd`, and chat ID. After a completed turn, three observations bounded to five seconds each (with brief delays) reconcile this server assignment. A wrong/unknown assignment remains `placement.status=unresolved`, blocks completion, preserves the actual chat, and prevents blind re-execution. Successful server observation is explicitly `server_verified_desktop_unverified`: a standalone listener cannot call connected desktop tools or observe the sidebar cache. Task completion and desktop acceptance are separate facts.

# Verification and pending live acceptance

Application-interface tests use real SQLite and task files, mutable external Telegram/catalog adapters, and a subprocess protocol fixture for Codex. They cover dynamic names, current choices, root changes, group metadata destination mismatches, same-topic continuation after restart, real `cwd`, first-turn materialization, inherited settings, delayed server placement, and unresolved placement. Existing stage-one tests and preserved live evidence remain valid for their original scopes: tickets 01–04 proved catalog refresh, selected-context retrieval, files, reporting, and actual-chat continuation. They do not establish this newly routed live chat.

A concrete additional live test requires authorization before any writes:

1. Refresh folder 8 and verify allowed group `-1003989567415`; read only its group metadata. Refresh the existing catalog and resolve the group name, or explicitly select existing `help` server project `01a1df7d-648f-7942-a075-ae429872b8cd`, working directory `/home/user/git/personal/help`.
2. Create one new test topic in that group and a simple source instruction that asks only for a marker reply, no project file changes. Preserve topic 2 and its existing stage-one task/chat.
3. Run one routed task, saving actual chat ID, server assignment, task folder, and outgoing report IDs. Observe connected desktop placement under the existing `help` project with a bounded observer outside the listener. Do not move/import/recreate chats to force acceptance.
4. Send a follow-up in the same new topic and confirm the same actual chat ID and task folder, the same project working directory, and a second marker response. Observe the desktop again.
5. If desktop placement does not settle within the agreed bound, record the unresolved evidence and leave ticket 05 needs-info. This plan does not authorize execution; the parent chat will obtain the specific write approval after code review.

No Telegram writes, new live chats, turns, or project changes were performed while implementing ticket 05.
