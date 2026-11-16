# Telegram-to-Codex task integration

Status: implemented

## Problem Statement

The user keeps task instructions, discussion, and files in Telegram and wants Codex to perform that work in the correct local project. Copying messages and attachments manually loses context, makes follow-up work hard to associate with the original Codex chat, and leaves results separated from their source conversation.

The integration must preserve historical context and support a clear organization: one selected Telegram folder contains project groups, and each project group contains chat topics linked to individual Codex chats. The user wants on-demand operation first and automatic work from explicit `#codex` requests later, using the same retrieval, access, routing, and reporting rules throughout.

## Solution

Run a local integration using the user's existing Telegram account and Codex installation. The user creates a Telegram folder, initially named `Codex`, adds a group for each Codex project, enables Topics in those groups, and creates a topic for each Codex chat.

Adding a project group to the Codex folder automatically enables connector access. A new group's exact unique name match selects its existing Codex project; missing or ambiguous matches require the user to choose before work executes. The remembered assignment survives display-name changes. Removing a group disables further Telegram access, pauses queued work, and requests interruption of running work while retaining progress.

The user can select a message with its replies and attachments, select an entire topic, or search allowed groups. Manual requests retrieve task context and let Codex carry out the task. With monitoring enabled, the user prepares messages and attachments in a chat topic, then posts a fresh `#codex` request. An unlinked topic starts a Codex chat in the assigned project; a linked topic continues that chat. Explicit `#link` selection attaches an existing project chat instead.

Return a short explanation and generated Markdown files to the original Telegram message or topic. Rename the topic itself to follow its Codex chat title, and maintain an additional pinned status/reference message. Execute automatic requests one at a time, preserve queue progress locally, catch up after reconnection, and reconcile uncertain external effects before retrying them.

Deliver this in three stages, while designing the monitoring lifecycle before the first implementation stage:

1. Manual retrieval, attachment handling, task execution, and Telegram reporting in an ignored test task workspace.
2. Existing-project routing, chat linking, topic-title synchronization, and status/reference reporting.
3. Automatic monitoring, durable queueing, fresh-trigger activation, and recovery after sleep, disconnection, or restart.

## User Stories

1. As a user, I want to connect my existing Telegram account, so that I can read historical task discussions already available to that account.
2. As a user, I want to select a Telegram folder for the integration, so that I can organize accessible project groups in one place.
3. As a user, I want one Telegram group per Codex project, so that each group's tasks have a clear project destination.
4. As a user, I want one topic per Codex chat, so that separate tasks and their follow-ups have separate conversations.
5. As a user, I want adding a group to the Codex folder to enable access automatically, so that I do not approve access separately for every project group.
6. As a user, I want the connector to reject reads, searches, downloads, and writes outside allowed groups, so that the selected folder defines its operating scope.
7. As a user, I want removal from the Codex folder to disable further reads and replies, so that folder membership continues to control access after setup.
8. As a user, I want queued work paused when its group is removed, so that it does not start after I withdraw access.
9. As a user, I want running work to receive an interruption request after group removal, so that the integration attempts to stop further work while retaining progress.
10. As a user, I want an exact unique group-name match to select my existing Codex project, so that ordinary project groups require no separate mapping command.
11. As a user, I want to choose the project when a name is missing or ambiguous, so that tasks are not sent to a guessed destination.
12. As a user, I want established project assignments to survive group and topic renames, so that display-name changes do not move my work.
13. As a user, I want topics to inherit their group's project assignment, so that I do not select a project for every topic.
14. As a user, I want a new task to create a new Codex chat, so that its work and context remain separate from other tasks.
15. As a user, I want follow-up requests in a linked topic to continue the same Codex chat, so that Codex retains the task's conversation history.
16. As a user, I want `#link` to list the assigned project's existing chats, so that I can attach a topic to work already started in Codex.
17. As a user, I want to choose an existing chat from a numbered list, so that linking does not depend on manually copying a technical identifier.
18. As a user, I want a topic initially named `New chat` to acquire its Codex chat's title, so that I can recognize it in Telegram.
19. As a user, I want later Codex chat title changes reflected in the topic name, so that the two conversations remain easy to identify.
20. As a user, I want a pinned reference showing the project, chat title, and task status, so that I can find the chat and understand its current state.
21. As a user, I want a direct Codex chat link where supported, with a searchable title and chat ID as fallback, so that I can locate the corresponding desktop conversation.
22. As a user, I want to retrieve older Telegram messages, so that tasks are not limited to messages received after the integration was installed.
23. As a user, I want a selected message to include its replies and attachments, so that later instructions attached to that message are available to Codex.
24. As a user, I want a selected topic to include its complete available history and attachments, so that Codex can use the whole discussion when I select that scope.
25. As a user, I want to select messages and topics through Telegram links, so that I can point Codex directly at the intended work.
26. As a user, I want text search within allowed groups, so that I can find tasks when I do not have their links.
27. As a user, I want to choose among multiple search matches, so that a search does not execute an arbitrary task.
28. As a user, I want retrieval to preserve complete message text and expose continuation when needed, so that long instructions are not silently truncated.
29. As a user, I want downloaded originals associated with the task folder, so that the task's source files remain available for inspection and follow-up work.
30. As a user, I want Codex to interpret text, images, PDFs, Word files, and spreadsheets, so that common task inputs can be used in the first delivery stage.
31. As a user, I want unsupported attachments preserved and identified, so that I know which inputs were not interpreted.
32. As a user, I want missing selected messages or unreadable selected attachments reported as blockers, so that incomplete work is not presented as finished.
33. As a user, I want several preparation messages and files to form task context, so that I can assemble a task before asking Codex to start.
34. As a user, I want manual reading and task execution before automatic monitoring is delivered, so that I can validate the essential workflow early.
35. As a user, I want an ignored local test task workspace inside this repository, so that trial task files remain separate from the integration's tracked source.
36. As a user, I want separate task folders for separate tasks, so that their inputs and results are not mixed.
37. As a user, I want follow-up work to reuse its task folder, so that the task retains its files across requests.
38. As a user, I want routed work to use my existing Codex project's working directory, so that tasks affect the intended project rather than always using the test destination.
39. As a user, I want the generated result sent back as a Telegram reply, so that I can see what Codex did without finding it elsewhere.
40. As a user, I want generated Markdown documents returned as files, so that the first version can deliver reusable written results.
41. As a user, I want results sent to their source message or topic, so that unrelated project conversations do not receive the output.
42. As a user, I want explicit completion or blocker reporting, so that I can distinguish finished work from work waiting for information or recovery.
43. As a user, I want a newly posted `#codex` message authored by me to start work automatically, so that I can request execution from Telegram.
44. As a user, I want ordinary unmarked messages to remain task context, so that preparing a discussion does not start work prematurely.
45. As a user, I want edits that add `#codex` to older messages to create no new requests, so that execution requires a fresh posted request.
46. As a user, I want integration-generated acknowledgments, results, and files excluded from triggering, so that the integration does not respond to itself.
47. As a user, I want duplicate delivery of the same Telegram trigger to produce one queued request, so that a reconnect does not repeat my request.
48. As a user, I want a new request queued while a task is running, so that I can submit follow-up work without interrupting the current run.
49. As a user, I want automatic requests processed one at a time in received order, so that work proceeds predictably on my laptop.
50. As a user, I want each queued request to include context only through its trigger message, so that later requests do not become instructions for an earlier request.
51. As a user, I want the current contents of that selected context read when execution starts, so that corrections made before execution are included.
52. As a user, I want a running task to keep its captured input fixed, so that new replies or edits do not silently change work already underway.
53. As a user, I want later replies and edits available to the next request, so that I can refine work through follow-up requests.
54. As a user, I want a pending request canceled if its trigger is deleted or its `#codex` is removed before execution, so that I can withdraw work that has not started.
55. As a user, I want a ready confirmation when monitoring is first enabled, so that I know when new requests can be accepted.
56. As a user, I want monitoring to wait for a fresh trigger after first activation, so that old `#codex` markers do not execute historical tasks.
57. As a user, I want newly enabled project groups to use the same ready-and-fresh-trigger rule, so that adding a group does not run its old markers.
58. As a user, I want historical messages to remain readable after activation, so that ignoring old triggers does not remove historical task context.
59. As a user, I want missed requests received after activation recovered when the laptop reconnects, so that temporary disconnection does not lose work.
60. As a user, I want saved queue and task progress to survive a process restart, so that completed work does not need to run again.
61. As a user, I want interrupted work identified and resumed only when its state is understood, so that recovery does not repeat uncertain actions blindly.
62. As a user, I want completed results and outgoing reports tracked durably, so that restarting does not unnecessarily resend results.
63. As a user, I want uncertain external outcomes reported when they cannot be reconciled, so that the integration does not silently create duplicate chats, turns, or reports.
64. As a user, I want the integration to run locally without a required VPS or hosting service, so that it works with my existing laptop setup.
65. As a user, I want tasks created by the integration to be visible in the Codex desktop app under the intended project, so that I can inspect and continue them there.
66. As a user, I want automatic monitoring planned from the start but delivered after the manual and routing stages, so that early implementation does not require replacement when monitoring is added.

## Implementation Decisions

### Delivery and current repository

The repository currently contains agent conventions, the domain glossary, accepted architectural decisions, requirements notes, and preserved connection-test evidence. There is no application implementation or existing automated test suite to extend.

Build a custom focused integration rather than assume the missing workflow is supplied by an existing Telegram MCP project. Use Python with Telethon for Telegram access and a local SQLite store for durable state, following the design already proposed during the interview. Keep the on-demand MCP entry point and background listener as callers of the same integration module from the beginning.

Stage one proves manual retrieval, interpretation of selected attachments, execution in the test destination, and Telegram result delivery. Stage two adds actual project routing, new and existing chat linkage, topic renaming, and pinned references. Stage three activates automatic requests, the serialized queue, and recovery. All three stages are included in this spec; completion of the first stage does not satisfy the whole scope.

Stage one's test destination is explicitly selected for trial work. It must not become a silent fallback when the user requests a real project whose assignment is unresolved.

### One application seam

Provide one deep task-integration module with a small application interface for manual commands, normalized Telegram/Codex events, pending-work dispatch, and observable task status/results. The interface owns the invariants for access, context selection, project/chat assignment, queue admission, task execution, recovery, and reporting.

The MCP entry point translates a caller's read/search/task request into this interface and returns its outcome. The listener translates account events and folder changes into the same interface. Neither caller duplicates access checks, trigger policy, project selection, or task lifecycle rules.

External Telegram and Codex adapters satisfy narrow interfaces for their actual capabilities. A project-catalog adapter supplies verified project identities, names, and working directories. Controllable time supports retry, activation, and recovery behavior. Durable local state and task folders remain inside the integration module's implementation.

### Folder access and group discovery

Select a particular Codex folder during setup and remember its stable identity. Resolve effective project-group membership from that selected folder, including additions and removals, instead of treating a folder name as a Telegram permission grant. Folder renames do not select a different folder with the same display name.

Membership enables connector access automatically. Reads, searches, historical retrieval, downloads, replies, uploads, title changes, and pinned-reference changes all use the same current allowed-group rule. Access checks cover the operation's actual resolved group, not only user-supplied display text or a link's apparent destination.

On observed removal, prevent new Telegram operations for that group, pause its pending requests, request interruption of its active Codex work, and retain local progress and mappings. Do not post a removal acknowledgment into a group whose access has just been disabled. A remote operation already accepted cannot be retracted by changing local policy.

The existing Telegram account retains its underlying account authority. The restriction is enforced by this integration and is not represented as a Telegram-enforced folder-scoped login.

### Project catalog and stable routing

Discover a new group's target using an exact unique name match against verified existing Codex projects. An absent or ambiguous match yields a project-choice outcome and blocks execution for that group until resolved. Retain the chosen project identity and working directory; subsequent group/topic renames do not reroute work.

Project-catalog discovery is an explicit early engineering task. The desktop's connected tools expose saved projects, but their tool names are not callable standalone listener methods. A separate app-server did not recognize the desktop project identifier during verification. Do not present experimental schema availability, arbitrary directory scanning, or a manually created duplicate project as proof of existing-project discovery.

Define and validate a supported catalog adapter before declaring automatic group-to-project matching complete. A setup-exported catalog can enable controlled manual development if necessary, but a one-time snapshot does not satisfy ongoing automatic discovery by itself. Unresolved catalog availability is reported explicitly; existing projects are not silently created, imported, or replaced to hide it.

### Context selection and files

Support message-link selection, topic-link selection, and text search limited to allowed groups. Return choices for ambiguous search. Preserve full text and expose continuation/completeness rather than silently limiting instructions.

A message selection retrieves that message, its reply relationships, and associated attachments. A topic selection retrieves that topic's complete available conversation and attachments. Keep these two scopes distinct even where Telegram's forum retrieval methods operate at topic level. Do not automatically scan unrelated conversations as part of a selected task; explicit further selections remain subject to the same access rule.

Keep original attachments associated with the task folder and provide usable inputs to Codex's interpretation tools. The first stage covers text, images, PDFs, Word files, and spreadsheets. Downloading an attachment alone is not proof that its content has been interpreted. If a selected supported input cannot be retrieved or read, pause with a concrete blocker. Preserve and identify intentionally unsupported formats without claiming their contents were interpreted; if the requested work needs those contents, or their necessity is uncertain, pause and ask for usable input or an explicit instruction to proceed without them. An unsupported file whose interpretation is explicitly unnecessary can remain a preserved, reported attachment. Never present work that depends on missing input as complete.

The Telegram adapter supplies retrieval and files; Codex and the applicable document/image tools perform interpretation. Avoid copying format-specific interpretation implementations into the connector merely to return attachment metadata.

### Task destinations and Codex chats

Keep an ignored test task workspace within the integration repository, with separate task folders and reuse for follow-up work. For real routed work, use the selected existing Codex project's working directory; preserve task-specific input/result association without assuming every artifact must be a tracked project file.

Use the local Codex app-server protocol for the launcher adapter. Create an unlinked chat topic's Codex chat using the known project working directory. Persist the actual returned chat identifier and use it for all continuations; a display title or a shared session-tree identifier is not a routing key.

The approved live test demonstrated two completed turns across separate app-server processes, matching title notifications/readback, desktop visibility, and eventual placement under the existing project. Project placement was initially absent and later appeared without moving the chat or importing a project. Verify placement with bounded reconciliation and expose unresolved placement as a visible state; do not interpret an initial absent assignment as final failure or falsely report a completed project association.

Respect the existing Codex model and permission configuration in production. The read-only/no-tools constraints used for the connection test are evidence about that test, not a policy that would prevent approved project work. Requests requiring an existing Codex permission decision must retain that decision point and surface a blocker rather than silently broaden permissions.

Allow `#link` to list existing chats only from the group's assigned project and accept a numbered selection. Validate the choice against the presented project and remembered identifiers before linking. Follow-up requests reuse the selected chat and task folder; a topic is not silently rebound by text appearing in task context.

### Activation, triggers, and queue admission

First activation and newly enabled groups establish an activation point, send readiness confirmation, and wait for fresh requests. Historical markers remain context and do not become automatic jobs. Reconnection after activation recovers eligible missed requests without resetting that activation point or discarding backlog.

Only newly posted messages authored by the user containing the `#codex` hashtag create automatic task requests. Ordinary messages supply future context. An edit that adds the hashtag to an older message never creates a new request.

Exclude all integration-generated messages, including acknowledgments, pinned references, report text, and uploaded-file captions. Because the integration uses the same Telegram account as the user, sender identity or an outgoing-message flag alone cannot distinguish a human request from its own output. Persist outgoing-operation identity and reconcile echoes and uncertain sends.

Use the Telegram account/group/message identity as the durable trigger key. Duplicate delivery of the same trigger cannot create another request. Persist discovery progress and admitted requests transactionally so a restart cannot advance beyond an unrecorded trigger.

Automatic execution is globally serialized. Received order means durable admission order. During a catch-up batch, order observed requests by Telegram message creation time, with stable group/message identity as a tie-break, then assign durable admission order. Do not retroactively reorder work already admitted or running because an older message was discovered later. Recover backlog in bounded batches without silently dropping eligible requests.

### Request inputs and withdrawal

For each queued request, retain its trigger message as the upper message boundary. At execution start, read the current contents of selected messages through that boundary, validate current access and the trigger, download the required files, and save the run's input snapshot. Messages posted after the boundary belong to later requests. Edits made after the run starts cannot change that captured input.

If the trigger is deleted or its hashtag removed before execution, cancel that pending request without starting Codex. This withdraws a known queued request; it does not change the rule that edits cannot create requests. Missing required context yields a blocked request, distinct from a withdrawn trigger.

Keep paused work and completed progress when access is removed. If a previously removed group returns, re-establish readiness for fresh requests; do not silently launch its previously paused work merely because it reappeared. A fresh request can continue the remembered chat. This is an explicit operational default derived from the agreed readiness and fresh-trigger policy.

### Results, names, and status

Deliver a short explanation and generated Markdown result files to the selected source message or topic. Record the reporting destination explicitly so retries cannot fall back to an unrelated default conversation.

After a new Codex chat obtains a title, rename the Telegram topic itself. Follow later Codex title changes in the same direction. Preserve the chat association across any display-name change, adapt titles to Telegram's constraints, and keep the full reference in the pinned status message if shortening is required. A manual topic title change does not alter the project/chat assignment or redefine the source of truth for its title.

Maintain an additional pinned reference with the project, Codex chat title, current task status, and a direct chat link where supported. Use searchable title and chat identifier when a direct link is unavailable. Naming the topic and pinning a reference are separate requirements.

Report pending, running, finished, blocked, paused, canceled, and unresolved recovery conditions using clear user-facing language. Do not label a task finished merely because retrieval, an upload, or a Codex process start succeeded; the requested work and required result delivery must be accounted for.

### Durable state and uncertain outcomes

Persist the selected folder identity, activation points, allowed-group state, project/chat mappings, task folders, trigger identities, captured inputs, ordered requests, progress, and outgoing-operation records. Save recoverable Codex chat/turn identifiers before proceeding to dependent work.

Discovery, execution, and reporting are distinct progress concerns. After a restart, reconstruct the module against durable state, recover known results, and reconcile uncertain chat creation, turn execution, and Telegram reporting before issuing another external action.

Do not claim strict exactly-once behavior across local storage, Telegram, and Codex. A remote action may succeed while its acknowledgment is lost. Use stable identities and the evidence available from each external adapter to prevent unnecessary repeats; if an outcome remains unknowable, expose a recovery blocker instead of blindly starting another chat, turn, or report.

## Testing Decisions

### Primary application seam

Test the shared task-integration module through the same application interface used by MCP requests and normalized listener dispatch. Issue user commands and external events, then assert returned context, visible task status, task-folder contents, and Telegram/Codex effects. The interface contract includes access scope, selection completeness, ordering, cancellation, recovery, and reporting.

Use a real temporary SQLite store and real temporary task folders in these tests. Substitute only the external Telegram, Codex, and project-catalog adapters and controllable time. Recovery tests must stop and reconstruct the module using the same durable files; replacing persistence with an in-memory fake would miss the behavior being verified.

Tests should remain valid if internal functions, private module structure, storage tables, or implementation call sequences change. Do not build a parallel suite that tests private methods or merely mirrors SQL/adapter calls. Focused external-adapter contract checks supplement this main seam where real protocol behavior must be established.

### Observable acceptance scenarios

1. A message selection returns its replies/files, a topic selection returns the topic, and ambiguous search returns choices. The same requests against an inaccessible group expose no content and perform no unauthorized external operation.
2. First activation and a newly discovered project group send readiness confirmation and execute no historical markers. Historical context remains retrievable, and a fresh eligible trigger is accepted afterward.
3. Exact unique project names bind automatically; absent or ambiguous matches return a choice and start no work. Renaming a group or topic preserves an established assignment.
4. A new task creates its chat and task folder in the chosen destination; follow-up work reuses both. `#link` exposes only that project's chat choices and links the selected stable chat identifier.
5. A newly posted user trigger creates one request. Duplicate delivery, integration-generated messages, messages from other senders, and edits adding a hashtag create no additional request.
6. Pending requests execute one at a time in durable received order. Bounded catch-up discovers post-activation missed requests, retains backlog, and preserves accepted ordering across restart.
7. A queued request captures current selected text/files through its trigger boundary when execution starts. Later messages and mid-run edits do not change its input; they become available to a later request.
8. Deleting a pending trigger or removing its hashtag cancels that request without starting Codex. A required attachment failure instead yields a blocker identifying the missing input.
9. Supported document/image inputs become usable task context; unsupported attachments remain available and are identified without a false claim of interpretation. Unsupported contents needed by the task, or whose necessity is uncertain, yield a blocker. Explicitly unnecessary unsupported attachments can be preserved and reported without blocking other work. Full messages and paginated history are not silently truncated.
10. Successful work sends its explanation and Markdown files to the original source, renames the topic to the Codex chat title, and maintains its pinned project/chat/status reference and link fallback.
11. Group removal stops newly initiated Telegram reads/writes, pauses queued work, requests interruption of active work, and retains progress. Results awaiting delivery remain unsent while access is disabled. Re-adding a group does not silently launch paused requests.
12. Reconstructing the module after failures at durable/external-effect transitions avoids unnecessary repeated work. A remote success with a lost acknowledgment is reconciled using recorded identity and external evidence, or exposed as an unresolved blocker instead of blindly repeated.
13. A delayed desktop project assignment and initially absent chat title are handled as pending observations. Eventual title/project metadata updates the user's reference without creating a replacement chat or switching project.

### Focused external-adapter verification

Verify actual Telegram folder resolution and updates, selected historical/reply/topic retrieval, attachments, sender identity, and the account's reply/upload/topic-rename/pin permissions. Validate the mechanisms actually available for identifying generated outgoing messages and reconciling uncertain sends. Use controlled fixtures and explicitly configured test groups rather than broad account history.

For Codex, use the preserved approved lifecycle test as prior evidence for known-directory creation, same-chat resume, protocol title events, and eventual desktop project placement. Before accepting the full routing/monitoring stages, verify the saved-project catalog source, observing desktop-origin title changes, active-turn interruption, and concurrent desktop/listener behavior. Do not substitute schema inspection for these live checks.

Add one thin MCP transport check and one thin listener-dispatch check to establish that their real envelopes reach the shared interface. Do not repeat the complete application acceptance suite through each entry point.

Live external tests create or change real chats/groups only within explicit test authorization and clean up only test-owned processes/resources as authorized. The already approved one-chat Codex test does not authorize unrelated test chats or Telegram actions.

### Existing evidence and acceptance of delivery

There is no pre-existing application test suite. Prior art is the approved desktop connection test performed on 2026-11-16 with Codex CLI 0.169.0: one persistent chat, two fixed replies across separate server processes, matching title events/readback, no tool actions in either turn, and eventual association with the existing project without a manual move/import.

Each delivery stage must demonstrate a complete user-visible workflow and the appropriate acceptance scenarios for that stage. Final acceptance requires all three stages, actual allowed-folder behavior, source-specific Telegram results, stable project/chat routing, and demonstrated recovery behavior; a working manual MCP alone is insufficient.

## Out of Scope

- A hosted execution platform, VPS requirement, or mandatory additional hosting service.
- Account-level Telegram isolation or a guarantee that the existing account's underlying session can access only the Codex folder.
- Reading or writing groups outside the selected folder, or executing requests from other Telegram users.
- Replacing the chosen folder/project-group/chat-topic structure with the superseded single-group/project-prefix layout.
- Automatic execution merely because a topic, ordinary message, historical hashtag, or hashtag-adding edit exists.
- Creating duplicate Codex projects to make existing-project lookup appear successful.
- PDF document generation and audio/video transcription in these three delivery stages; preserving their source attachments remains in scope where applicable.
- General Telegram moderation or unrelated account administration.
- Parallel automatic task execution in the initial monitor.
- Silent mid-run steering from new Telegram messages or edits.
- Strict exactly-once distributed execution, instantaneous interruption, or silently retrying unknowable external outcomes.
- Reimplementing document-format interpretation inside the Telegram connector when Codex's applicable tools can perform it.

## Further Notes

The active architectural decision is ADR-0002: folder → project groups → chat topics, with automatic access on folder inclusion and access removal on exclusion. ADR-0001's single-group/project-prefix model is superseded.

The project catalog is the principal unresolved engineering dependency. The connection test establishes a usable known-directory execution path, not a complete saved-project discovery solution. Make catalog validation an early investigation with a visible acceptance result before routing tickets depend on it. Desktop-origin rename events, interruption, and Telegram account integration are also verification work rather than already-proven capabilities.

The queue ordering tie-break and re-addition policy above are explicit operational defaults derived from the agreed received-order, readiness, pause, and fresh-trigger rules. They fill implementation detail without changing the accepted trigger or access model.

Primary technical references are Telegram's [folder model](https://core.telegram.org/api/folders), [forum topics](https://core.telegram.org/api/forum), and [topic editing](https://core.telegram.org/method/messages.editForumTopic), plus the [Codex app-server protocol](https://learn.chatgpt.com/docs/app-server) and [desktop chat deep links](https://learn.chatgpt.com/docs/app/commands#deep-links). The preserved local test evidence is authoritative for what was actually verified on this installation.

The user confirmed the shared application testing seam. This spec is implemented through the fourteen local tickets. Their acceptance evidence and documented production protocol limits are linked from tickets.md.
