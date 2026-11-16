# Telegram integration implementation map

## Notes

Implementation branch: `integration/telegram-codex`. The approved spec and numbered tickets define the remaining task graph.

## Decisions-so-far

- [Ticket 02](./issues/02-run-a-manual-text-task-and-report-its-result.md#answer) is resolved. The explicitly authorized live text workflow completed one Codex turn and delivered verified text and Markdown replies to the selected source topic. [Evidence](./manual-workflow-live-test.json).

## Fog

- Ticket 01 still needs a live project-change catalog refresh check; the pending one-chat Telegram test approval did not authorize project renaming.
- [Ticket 03](./issues/03-read-complete-discussions-and-find-tasks.md#implementation-evidence) implements discussion retrieval/search and passes hermetic application/adapter checks; final raw-page live retrieval acceptance remains pending. Attachment interpretation remains ticket 04.
