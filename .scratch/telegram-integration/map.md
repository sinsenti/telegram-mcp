# Telegram integration implementation map

## Notes

Implementation branch: `integration/telegram-codex`. The approved spec and numbered tickets define the remaining task graph.

## Decisions-so-far

- [Ticket 02](./issues/02-run-a-manual-text-task-and-report-its-result.md#answer) is resolved. The explicitly authorized live text workflow completed one Codex turn and delivered verified text and Markdown replies to the selected source topic. [Evidence](./manual-workflow-live-test.json).

- [Ticket 03](./issues/03-read-complete-discussions-and-find-tasks.md#answer) is resolved after the final raw-page adapter successfully read the selected message/replies and whole topic with correct distinct scopes and link identities. [Evidence](./discussion-read-live-test.json).

## Fog

- Ticket 01 still needs a live project-change catalog refresh check; the pending one-chat Telegram test approval did not authorize project renaming.
- Ticket 04 attachment interpretation is now unblocked.
