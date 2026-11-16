# Link a topic to an existing Codex chat

The shared application boundary accepts `action=link`, `group_id`, and `topic_id`. It refreshes folder access, the group's existing project assignment, and all available chat metadata pages. The response has `status=chat_choice`, a `choice_id`, and numbered `choices` containing chat IDs and titles. An unnamed chat uses its stable ID as a searchable fallback; the adapter does not expose previews or conversation contents.

Select with the same `action=link`, `group_id`, `topic_id`, `choice_id`, and integer `choice`. The presented list must still be the current list for this exact topic. The application refreshes membership before saving. Invalid choices, a missing chat, a changed destination, a foreign project, or revoked group access block without changing the topic binding. A chat already bound to another topic cannot be selected; transferring it is outside this command.

For Telegram, the normalized `action=chat_command`, `group_id`, `message_id`, and `text` accepts an exact `#link` or a numbered reply to the topic's pending list. It reads the current source message, validates the text, and derives the actual topic from that message. Caller-supplied topic IDs are ignored. The listener must first enforce fresh human-author eligibility and generated-message exclusion. The command returns choices or a link confirmation for the listener to report to that topic. Other text returns `ignored`; task-context text never invokes this path.

Linking creates no Codex chat and starts no turn. It retains the selected stable ID, a task folder, and the group/topic destination in SQLite. Later `task` commands with `destination=project` in that topic continue the selected chat in its project's working directory and report results normally. Reopening the application preserves this binding and folder. Relinking to a previously used chat in the same topic restores its original task folder and run counter. Unfinished work blocks relinking.

## Current membership and legacy chats

The installed experimental schema exposes `ThreadListParams.projectId`, exact `cwd`, cursor pagination, `archived`, and `Thread.projectId`, `cwd`, and `name`. The adapter lists active canonical members and separately unassigned chats with the exact project working directory. It does not read turns, use preview text as instructions, create/import projects, move chats, or assign a project to repair legacy metadata.

A non-null canonical project ID is authoritative: a foreign value always excludes the chat, even with a matching directory. An unassigned legacy chat is eligible only when its exact directory is owned by precisely one root in the freshly fetched complete project catalog. Shared roots, nested paths, missing identities, and ambiguous directories provide no legacy proof. The same membership check runs again before each linked task starts. Listings cover active ordinary interactive chats exposed by the server; archived chats and attached/subagent chats are outside this selection.

After a legacy chat's completed turn, the bounded metadata observer reports `legacy_cwd_verified_desktop_unverified` when its canonical project remains null and its cwd still matches. Canonical members report `server_verified_desktop_unverified`. Neither status claims to observe the independently cached desktop sidebar. Canonical foreign IDs or changed directories block placement completion.

## Verification and live acceptance

Application tests exercise real temporary SQLite and files through `Application.handle`: listing/filtering, numbered selection, restart and same-chat/folder execution, invalid/stale/cross-topic choices, folder revocation, current membership changes, legacy proof, and exact command normalization. A subprocess adapter contract verifies both scoped queries, pagination, fallback titles, and foreign-ID exclusion without any content reads or writes.

The actual read-only assigned-project adapter check returned three eligible chats: one canonical member and two legacy null-project chats with a uniquely owned exact cwd. It included both the routed test chat and the known presentation chat. [Metadata evidence](../.scratch/telegram-integration/linking-metadata-live-test.json). This verifies real listing/schema behavior, while explicit selection and continuation still need live acceptance.

Live acceptance still requires explicit authorization. A minimal plan is to use existing allowed group `-1003989567415`, assigned help server project `01a1df7d-648f-7942-a075-ae429872b8cd`, and topic 14. Read current choices, explicitly select the already routed chat `01a1e473-8c30-7821-99f1-6279e9947a2a`, submit a deliberately invalid number and confirm the binding is unchanged, then request one marker-only follow-up with no project edits. Verify the original task/chat/folder and source reports. A separate legacy-chat selection would require a new topic and explicit approval for that topic, continuation turn, and Telegram writes. No live writes were performed for this implementation.

## Completed controlled live acceptance

Under the user’s standing authorization, topic 21 was linked by a real numbered choice to the earlier owned connection-test chat, with an invalid choice rejected first. One marker follow-up completed in that same existing chat and retained task folder; the source-specific Markdown download matched the local result. [Evidence](../.scratch/telegram-integration/linking-live-test.json). Ticket 06 is resolved. No presentation/user-work chat was selected or changed.
