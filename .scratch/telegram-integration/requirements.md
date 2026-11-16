# Telegram integration: interview notes

These notes capture agreed requirements and verification findings. They are not an implementation spec. The workflow interview is complete; the approved Codex desktop connection test below has now passed for the existing `help` project directory.

The confirmed implementation specification is published in [spec.md](./spec.md) with status `ready-for-agent`. It includes the user-confirmed shared application testing seam and is the source for subsequent ticket decomposition.

## Current structure: folder, project groups, chat topics

Use a Telegram folder named `Codex`, containing one group per Codex project, with one topic per Codex chat inside each group. For example: folder `Codex` -> group `help` -> topic `New chat`. This supersedes the earlier single-group layout and project-name topic prefixes.

Telegram folders organize chats and are represented as dialog filters in the API; they are not a folder-scoped Telegram login grant. See [dialog folders](https://core.telegram.org/api/folders). Adding a project group to the selected folder enables connector access automatically. An exact unique group-name match selects the existing Codex project; otherwise the user chooses. Removing the group disables further reads and replies, pauses queued tasks, and requests that running work stop while preserving progress.

A project assignment belongs to the group, and topics inherit it. Chat-topic titles follow the Codex chat title without repeating the project name. No Telegram configuration or access permissions have actually been changed; these are requirements for the planned integration.

## Agreed requirements

- Start with on-demand retrieval and task execution through Codex.
- Historical messages are required, not only messages received after setup.
- Support both task-context selections: a message with its replies and attachments, or a whole Telegram topic with its messages and attachments when the user selects that topic.
- Accept message/topic links and text search within allowed groups. If search has several matches, the user chooses which task to use.
- Restrict connector access to project groups in the selected Codex folder. Adding a group automatically enables access, replacing the original one-group scope.
- Run locally on the user's laptop, without requiring a VPS or a paid hosting service.
- Keep a subdirectory of this repository, excluded from Git, as a test task workspace. Each task gets its own folder; follow-up work on the same task reuses its folder.
- Support routing tasks to existing Codex projects and their own folders. This expands Q2's original test-workspace-only scope; the ignored workspace remains a test destination.
- Use one Telegram group per Codex project and one topic per Codex chat inside each project group. Topic names follow chat titles; group names identify projects.
- New tasks normally create new Codex chats; follow-up requests continue the same chat. The user can explicitly attach a task to an existing chat.
- Match a newly discovered project group to an existing Codex project by an exact unique name match. If no unique match exists, ask the user to choose before executing work. Remember the resulting assignment independently of display names and let topics inherit it.
- Removing a group from the Codex folder disables further reads and Telegram replies, pauses its queued tasks, and requests that running work stop. Preserve saved progress. A stop request is not a guarantee that already-running external work stops instantaneously.
- In a linked chat topic, a new user `#codex` request continues the linked Codex chat. Queue it if a run is active; unmarked messages supply context for the next request.
- Topic names follow Codex chat title changes. A lasting title change is made in Codex and mirrored to Telegram. The earlier project prefix is no longer necessary because the group identifies the project.
- A new topic can start as `New chat`; rename the topic itself when its Codex chat receives a title, and keep following later Codex title changes. A pinned status/reference message complements this title synchronization.
- Support `#link` to present a numbered list of the assigned project's existing Codex chats and let the user explicitly attach one to the topic.
- Each queued `#codex` request has a context boundary at its trigger message. Read the current contents of messages up to that boundary when work starts, then keep the run's input fixed. Later messages belong to the next request.
- If the trigger is deleted or its `#codex` is removed before execution, cancel that queued request. Editing an old message to add a hashtag still does not create a new request.
- On first activation, including a newly enabled project group, send a ready confirmation and wait for a fresh trigger. Older messages remain readable as context, but historical markers are not automatically executed. Reconnection catches up on requests received after activation.
- Each linked topic has a pinned status/reference message showing project, Codex chat title, task status, and a direct chat link where supported; otherwise show a searchable title and chat ID.
- Support reporting back through Telegram in the first version, including replies and uploading a generated Markdown file as a task result.
- Return results to their source: reply to the selected message, or post in the selected topic, with a short explanation and the result files.
- The first version generates Markdown documents. PDF generation is deferred.
- In the first version, interpret text, images, PDFs, Word files, and spreadsheets. Audio/video transcription is deferred; preserve other attachments and report contents that cannot be read.
- A running task uses the task context read at its start. New replies or edits become part of the next requested update in the same task folder.
- If a selected attachment cannot be opened or selected conversation content cannot be retrieved, pause the task and report what is missing instead of presenting an incomplete task result as finished.
- Use the user's existing Telegram account, with the selected-folder membership rule enforced by the connector. The underlying Telegram session retains the account's authority.
- Later monitoring and automatic Codex chat creation are required capabilities, even if delivered after the first version.
- For explicitly configured triggers, future automation should start work automatically and report completion or a blocker. The launch mechanism remains to be verified.
- The initial automatic trigger is a message posted by the user that contains `#codex` in an allowed group. Additional trigger rules may follow later.
- Only newly posted trigger messages create requests. Editing an older message to add `#codex` does not start work.
- Future monitoring catches up after sleep or disconnection, handles missed requests once, preserves progress, and reports interrupted tasks that cannot continue. Avoid repeated completed work and duplicate task results.
- Initially, automatic tasks run one at a time in received order, with separate task files.
- Agreed delivery order: manual reading/execution/reporting in the test workspace; existing-project routing/chat linking/topic naming; then automatic monitoring/queueing/recovery. The monitoring architecture must be decided upfront, not left until the third delivery step.

## Remaining technical verification

- The approved standalone-to-desktop lifecycle test passed for `help`: create a chat by working directory, complete a turn, stop the server, resume the same chat in a new server, complete a second turn, and mirror the test title into desktop metadata. Project association appeared after a delay without a manual move or import.
- Determine how the standalone listener obtains the saved desktop project catalog for automatic group-name matching. The known-directory execution path is verified, but standalone `project/read` still does not recognize the desktop's project ID.
- Verify observing manual desktop-side chat renames through a concurrently running listener, active-run interruption, and concurrent desktop/listener behavior during integration testing; these were outside the two-turn connection test.
- Confirm direct Telegram-to-Codex chat link support; the accepted fallback is searchable title plus chat ID.
- Validate folder updates, topic rename/pin permissions, selected-context retrieval, and recovery with the actual Telegram account during integration testing. No Telegram login or connected end-to-end test has occurred yet.

The current workflow decisions through Q31 are accepted. A local app-server adapter using known project directories and persisted thread IDs is now supported by a successful lifecycle test. Project catalog discovery and the remaining Telegram integration checks still belong in the implementation plan.

## User answers and subsequent revisions

Earlier answers below are historical when explicitly superseded by the current structure.

- Q1: accepted both selections: a message with its replies and attachments, or the whole topic when a topic is selected.
- Q2: use an ignored subdirectory of this repository from the beginning.
- Q3: Telegram replies and returning files belong in the first version; Markdown first, PDF may follow.
- Q4: accepted the existing Telegram account with connector-level restrictions.
- Q5: accepted automatic work for explicitly configured triggers, with reporting when finished or blocked.
- Q6: accepted message/topic links and text search; the user selects from multiple search matches.
- Q7: accepted separate task folders, with folder reuse for follow-up work on the same task.
- Q8: accepted sending results back as a reply to the source message or inside the source topic, with a short explanation and result files.
- Q9: accepted Markdown documents in the first version and PDF generation later.
- Q10: accepted automatic starts on the user's own messages containing `#codex` in the allowed group.
- Q11: accepted documents and images in the first version, with audio/video transcription later and unreadable attachments reported.
- Q12: accepted starting-context snapshots, with later replies and edits handled by the next requested update.
- Q13: accepted pausing and reporting missing task context instead of claiming completion.
- Q14: accepted catch-up, saved progress, and prevention of repeated work or duplicate results after reconnection.
- Q15: accepted running automatic tasks one at a time, in received order.
- Q16: accepted routing work to real existing Codex projects and their folders, keeping the ignored workspace as a test destination.
- Q17: accepted one Telegram topic per Codex chat with the title `Project · Chat title`.
- Q18: accepted a new Codex chat for a new task, continuing that chat for follow-ups, plus explicit attachment to an existing chat.
- Q19: accepted explicit project selection for a chat topic, remembering the assignment across topic renames.
- Q20: accepted continuing the linked chat for new `#codex` requests, queueing if busy, and treating unmarked messages as context.
- Q21: accepted topic title synchronization following initial and later Codex chat renames, preserving the project prefix.
- Q22: accepted the three delivery steps. Subsequent clarification requires designing the monitoring mechanism before implementation begins.
- Subsequent structure clarification: use a Telegram folder containing project groups, with chat topics inside each group. This supersedes Q17's single-group layout, Q19's topic-level project selection, and Q21's project-prefix display rule; the title-synchronization intent remains.
- Folder access choice: adding a project group to the selected Codex folder automatically enables access. No separate per-group access approval is required.
- Q25: accepted matching a group to an existing Codex project by exact unique name, remembering the match, and asking the user if missing or ambiguous.
- Q26: accepted disabling further reads/replies and pausing queued tasks on group removal, requesting running work stop, and preserving progress.
- Q27: accepted new-message-only triggers; editing an old message to add `#codex` does not start work.
- Q28: accepted `#link` and choosing an existing chat from a numbered list for the group's project.
- Q29: accepted a trigger-message context boundary, current contents read at execution start, fixed running input, and cancellation if the trigger is deleted or its hashtag removed before execution.
- Q30: accepted readiness confirmation and a fresh-trigger requirement for initial activation/new groups; historical context remains readable and reconnect catch-up remains enabled.
- Q31: accepted a pinned status/reference message, with direct link if supported and searchable title/chat ID fallback. Explicitly reaffirmed that the topic itself must also be renamed after its Codex chat receives a title.

## Project and chat routing

Use one project group per Codex project and one topic per Codex chat. Real-project destinations coexist with the test workspace. Use a temporary topic name such as `New chat`, then rename the topic itself to mirror initial and later Codex chat titles. Group/project and topic/chat assignments are remembered independently of display names. The initial group-to-project match is by exact unique name, with explicit user selection for missing/ambiguous matches. Use `#link` to choose an existing chat from the group's assigned project. The pinned reference/status message is additional to topic renaming.

## Proposed automatic-monitoring design

This section is a concrete proposal, not yet a fully confirmed implementation plan.

- Select a Telegram folder, for example `Codex`; create project groups such as `help`, add them to that folder, and enable Topics in each group. Create chat topics such as `New chat` inside the relevant group.
- Discover groups through the selected folder and enable access automatically. Resolve each group's target Codex project before starting work; topic-level `#project help` commands are no longer the proposed default.
- The user adds instructions and attachments, then posts a fresh `#codex` message. In an unlinked topic, create a Codex chat in the bound project; in a linked topic, continue that chat. Return results and title updates to the same topic.
- Use a local long-running Python/Telethon service for Telegram updates, sharing access checks and retrieval code with on-demand MCP tools. The MCP interface and event listener are separate entry points into the same services.
- Persist selected-folder identity, group/project mappings, topic/chat mappings, source-message IDs, retrieval progress, task queue state, and outgoing-message records in SQLite. Use stable IDs for established identities and titles only for display.
- Enqueue only explicit requests from the user in allowed groups. Exclude service-generated acknowledgments and reports even though they use the same Telegram account.
- Store the trigger message as the queued-request context boundary. Save the current contents of the selected messages up to that boundary when a run starts, then keep its input fixed. Later messages belong to the next request. Check trigger deletion/hashtag removal before execution and cancel the pending request if either occurred.
- Use a serialized worker and a Codex launcher adapter. Known-directory chat creation, continuation, desktop visibility, eventual project placement, and protocol-side title events passed the approved test. Saved-project catalog discovery and desktop-origin rename subscriptions remain integration work.
- Advance discovery watermarks transactionally with queued requests. Reconcile uncertain external actions after a crash instead of blindly repeating chat creation, execution, or reporting.
- Accepted first-enable policy: send a ready confirmation, then wait for fresh triggers instead of executing historical `#codex` messages. Apply this to newly enabled groups too. After activation, recover missed requests in batches without silently discarding backlog. Historical messages remain available as task context.
- Telegram group/topic creation can happen now; binding and trigger commands remain inert until the integration is implemented, configured, and enabled.

## Current project and launcher check

- The connected Codex app confirms an existing local project `help`, ID `c18094d8-b906-4609-834d-1f4a741fe843`, at `/home/user/git/personal/help`.
- A normally initialized separate `codex app-server --stdio` returned `project not found` for that ID. It did not create or change any projects or chats.
- The supported `codex app-server proxy` route could not connect because its default existing-daemon control socket was absent. No daemon was started or restarted.
- Shared persisted chat storage was confirmed by the read-only checks below. Live execution and eventual existing desktop-project association were subsequently confirmed by the approved lifecycle test. The app's injected project/chat tools establish capabilities within this conversation, not a standalone listener API.

### Read-only desktop connection verification: 2026-11-16

- Installed CLI is `0.169.0`. Connected app tools still see the existing `help` project under the same ID and directory.
- A temporary standalone stdio server read this exact desktop chat's metadata through `thread/read` with `includeTurns: false`: ID `01a1d63d-6b7b-7bb1-b2ef-c5ef4f322b9f`, title `Set up Matt Pocock skills`, cwd `/home/user/git/personal/telegram-mcp`. The returned ID, title, and directory match the desktop's current metadata.
- The same metadata-only check succeeded for the existing `help` chat `AI Helper`, ID `01a1df7f-8ac9-7452-962e-16d3232d2647`, cwd `/home/user/git/personal/help`. Its ID, title, and directory match connected desktop metadata.
- Both standalone responses return `projectId: null` although connected desktop metadata assigns the existing project IDs. A fresh `project/read` for `help` returns `-32602 project not found`. Shared persisted threads are therefore established; equal project-registry views are not.
- A fresh normally permitted `codex app-server daemon version` finds no default control socket. Targeted runtime metadata checks also found no reachable Codex daemon socket. No daemon was started, restarted, or reconfigured.
- `xdg-mime query default x-scheme-handler/codex` returns `chatgpt.desktop`. The documented existing-chat URL is `codex://threads/<thread-id>`. Actual URL opening was not invoked. See [desktop deep links](https://learn.chatgpt.com/docs/app/commands#deep-links).
- A new-chat deep link populates a composer and does not automatically submit the prompt, so that route alone does not implement automatic execution.
- No existing chat was messaged, resumed, renamed, or otherwise modified. No test chat has been created. All temporary probe server processes have stopped.
- At the end of the read-only stage, the lifecycle plan at `/tmp/telegram-desktop-connection-test-plan.json` awaited explicit authorization for one test chat. The user subsequently approved it, and the live test below completed. No project import or manual chat move was used to conceal automatic project-association failures.

### Approved live connection verification: 2026-11-16

The user explicitly approved the prepared one-chat test. Results are saved in [desktop-connection-test-result.json](./desktop-connection-test-result.json).

- Created exactly one durable test chat through a standalone `codex app-server --stdio`, with cwd `/home/user/git/personal/help`, read-only sandbox, and network disabled for project tools. The inherited configured model was `gpt-6.1-sol`.
- Test thread ID: `01a1e17d-73b4-7150-a085-70d68488bc88`. Initial title: `Telegram connection test`. Final title: `Telegram connection test - verified`.
- The first turn returned exactly `TELEGRAM_CONNECTION_OK_1`. After stopping that server process, a second standalone server resumed the same thread ID and returned exactly `TELEGRAM_CONNECTION_OK_2`.
- Both turns completed without tool actions. No project files were changed. No existing chat was messaged, renamed, moved, or modified.
- Both initial and final `thread/name/set` operations produced `thread/name/updated` notifications and matching protocol readback. Connected desktop metadata also reports the final title and both completed replies for the same ID.
- Desktop history initially reported no project assignment, then associated the test chat with the existing `help` project ID `c18094d8-b906-4609-834d-1f4a741fe843`, without any project import or manual chat move. The exact reconciliation trigger was not isolated; placement checks must tolerate a delay.
- All test-owned server processes stopped. The test chat remains available for user review; no archive or delete operation was performed.
- This proves the local launch/resume/persistence/title path for a known existing project directory. It does not establish a working standalone saved-project catalog API, live desktop-origin rename subscriptions, or an implemented Telegram monitor.

## Project/chat routing feasibility findings

- Telegram forum topics cannot contain nested message threads. A named project topic with named chat subtopics is therefore not a supported hierarchy. A project topic can contain ordinary task messages, or each Codex chat can have its own topic with the project name in its title. See [forum topics](https://core.telegram.org/api/forum).
- Telegram topic titles can be changed, subject to topic ownership or topic-management permissions. See [topic edits](https://core.telegram.org/method/messages.editForumTopic).
- Codex app-server documents reading chat titles and observing `thread/name/updated`; an initial chat may not yet have a title. This can support later display-name synchronization. See [app-server](https://learn.chatgpt.com/docs/app-server).
- The installed CLI's experimental schemas expose project listing, project roots, and project-associated chat creation. The approved live test now proves desktop visibility and eventual placement by known project directory. The standalone project registry still does not resolve the desktop project ID; schema availability alone does not prove shared registry behavior.
- Established project/chat/topic mappings use stable IDs; names remain display labels so later renames do not change an existing assignment. This follows the accepted routing decisions.

## Automation feasibility findings

- Local non-interactive work has a documented route through `codex exec`; saved CLI authentication can be reused if valid. No authenticated run was performed during this investigation. See [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).
- The app-server documents programmatic thread and turn creation. A thread created by a separate server does not by itself establish that it appears as a new chat in this desktop app. See [app-server](https://learn.chatgpt.com/docs/app-server).
- Visible desktop chat creation, same-ID resume, and eventual existing-project placement passed the approved live app-server test. A working Telegram trigger, project catalog source, and full monitor lifecycle remain to be implemented and tested.
