# Telegram integration tickets

Status: implementation started on `integration/telegram-codex`; live acceptance pending.

[Implementation spec](./spec.md)

## Delivery gates

- Stage 1: tickets 02–04.
- Stage 2: tickets 01 and 05–07.
- Stage 3: tickets 08–14.

These are delivery gates. Implementation may proceed on any ticket whose blockers are complete.

## Tickets

| Ticket | Blocked by | Spec user stories |
| --- | --- | --- |
| [01: Discover existing Codex projects](./issues/01-discover-existing-codex-projects.md) | None | 10, 11, 38, 65 |
| [02: Run a manual text task and report its result](./issues/02-run-a-manual-text-task-and-report-its-result.md) | None | 1, 2, 5, 6, 22, 34, 35, 36, 37, 39, 40, 41, 42, 64, 66 |
| [03: Read complete discussions and find tasks](./issues/03-read-complete-discussions-and-find-tasks.md) | 02 | 23, 24, 25, 26, 27, 28, 33 |
| [04: Complete tasks using document and image attachments](./issues/04-complete-tasks-using-document-and-image-attachments.md) | 03 | 29, 30, 31, 32, 40 |
| [05: Route task topics into real Codex projects](./issues/05-route-task-topics-into-real-codex-projects.md) | 01, 02 | 3, 4, 10, 11, 12, 13, 14, 15, 38, 65 |
| [06: Attach topics to existing Codex chats](./issues/06-attach-topics-to-existing-codex-chats.md) | 05 | 16, 17, 15, 37 |
| [07: Synchronize topic titles and pinned chat references](./issues/07-synchronize-topic-titles-and-pinned-chat-references.md) | 05 | 18, 19, 20, 21, 42 |
| [08: Start fresh Telegram requests automatically](./issues/08-start-fresh-telegram-requests-automatically.md) | 03, 05 | 43, 44, 45, 46, 47, 55, 56, 57, 58, 64, 66 |
| [09: Queue requests with fixed context and withdrawal](./issues/09-queue-requests-with-fixed-context-and-withdrawal.md) | 08 | 48, 49, 50, 51, 52, 53, 54 |
| [10: Catch up after sleep or disconnection](./issues/10-catch-up-after-sleep-or-disconnection.md) | 09 | 49, 56, 57, 58, 59, 60 |
| [11: Recover known task progress after restart](./issues/11-recover-known-task-progress-after-restart.md) | 09 | 60, 61, 62, 42 |
| [12: Revoke folder access and pause task work](./issues/12-revoke-folder-access-and-pause-task-work.md) | 09 | 7, 8, 9, 60, 61 |
| [13: Reconcile uncertain Codex actions after crashes](./issues/13-reconcile-uncertain-codex-actions-after-crashes.md) | 09 | 14, 15, 60, 61, 63 |
| [14: Reconcile uncertain Telegram reporting](./issues/14-reconcile-uncertain-telegram-reporting.md) | 08 | 39, 40, 41, 42, 46, 62, 63 |

## Initial frontier

Tickets 01 and 02 can start independently. Ticket 01 must establish a supported ongoing project catalog before routing can proceed; an unsupported result leaves that dependency unresolved.

## Current implementation status

Tickets 01–08 are resolved; stages 1–2 and fresh automatic triggering are verified:

- 01: the desktop-origin rename and restoration were observed in both catalog views with stable IDs and directories; see [live evidence](./catalog-refresh-live-test.json).
- 02: the approved live manual text task completed in one real Codex chat, and its text/Markdown replies were verified in the original Telegram topic, including a byte-for-byte file comparison; see [evidence](./manual-workflow-live-test.json).

Ticket 03 is resolved after successful bounded live reads using the final raw-page adapter. Both message-with-replies and whole-topic scopes, completeness, and private-link identities were verified; see [evidence](./discussion-read-live-test.json).

Ticket 04 is resolved after the approved five-file live test: actual Codex interpretation, unchanged originals, same-chat/folder follow-up, source-specific replies and downloaded Markdown equality all passed. [Evidence](./attachments-live-test.json). All 51 root tests pass. Ticket 05 is resolved after its approved live test verified the new topic/chat, two-turn continuation, source delivery and existing help desktop project placement. [Evidence](./routing-live-test.json). Tickets 06–07 passed real selection/continuation, desktop-name observation, topic synchronization and pinned-reference checks. [Link evidence](./linking-live-test.json), [reference evidence](./title-reference-live-test.json). Ticket 08 passed real human-trigger admission and source-specific automatic continuation. Duplicate event replay produced no new work; the controlled listener is stopped. [Evidence](./monitoring-live-test.json). Tickets 09 and 14 are now unblocked; tickets 09–14 remain to implement. No additional new chat was created; the attachment test used exactly one follow-up in the existing test chat.
