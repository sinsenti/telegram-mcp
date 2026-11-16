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

Ticket 02 is resolved; ticket 01 remains `needs-info`:

- 01: the experimental standalone catalog matches all 11 existing desktop projects by name and directory. A controlled real-project change still needs to demonstrate live refresh; see [catalog evidence](../../docs/research/project-catalog.md).
- 02: the approved live manual text task completed in one real Codex chat, and its text/Markdown replies were verified in the original Telegram topic, including a byte-for-byte file comparison; see [evidence](./manual-workflow-live-test.json).

Ticket 03 is now unblocked. Tickets 03–14 remain unimplemented. The approved test created one Codex chat and two source replies; it did not authorize project renaming or unrelated test tasks. Stage 1 still requires tickets 03 and 04.
