# Telegram integration implementation map

## Notes

Implementation branch: `integration/telegram-codex`. The approved spec and numbered tickets define the remaining task graph.

The user authorized running these controlled Telegram/Codex integration tests without per-test approval prompts on 2026-11-16. Continue bounded verification in the existing allowed test group and test-owned chats/topics; human-only actions still require user participation. This standing authorization supersedes the earlier per-test confirmation workflow.

## Decisions-so-far

- [Ticket 02](./issues/02-run-a-manual-text-task-and-report-its-result.md#answer) is resolved. The explicitly authorized live text workflow completed one Codex turn and delivered verified text and Markdown replies to the selected source topic. [Evidence](./manual-workflow-live-test.json).

- [Ticket 03](./issues/03-read-complete-discussions-and-find-tasks.md#answer) is resolved after the final raw-page adapter successfully read the selected message/replies and whole topic with correct distinct scopes and link identities. [Evidence](./discussion-read-live-test.json).

- [Ticket 04](./issues/04-complete-tasks-using-document-and-image-attachments.md#answer) is resolved after approved real five-format interpretation, original preservation and source-specific Markdown round-trip verification. [Evidence](./attachments-live-test.json). Stage 1 is complete.

- [Ticket 01](./issues/01-discover-existing-codex-projects.md#answer) is resolved after the approved desktop-origin rename and restoration were verified in both catalog views with stable identities and roots. [Evidence](./catalog-refresh-live-test.json).

- [Ticket 05](./issues/05-route-task-topics-into-real-codex-projects.md#answer) is resolved after an approved two-turn live route, same-chat/folder continuation, source-report round trip and actual desktop placement in the existing help project. [Evidence](./routing-live-test.json).

- [Ticket 06](./issues/06-attach-topics-to-existing-codex-chats.md#answer) implements explicit numbered linkage, current membership validation, stable folder reuse, and exact-message command normalization. [API and live proposal](../../docs/chat-linking.md). Live acceptance remains pending.

- [Ticket 06](./issues/06-attach-topics-to-existing-codex-chats.md#answer) is resolved after real numbered existing-chat selection, invalid-choice rejection and same-chat/folder continuation. [Evidence](./linking-live-test.json).
- [Ticket 07](./issues/07-synchronize-topic-titles-and-pinned-chat-references.md#answer) is resolved after actual desktop title observation, topic/reference/pin updates and restoration. [Evidence](./title-reference-live-test.json). Stage 2 is complete.

## Fog

- Ticket 08 listener is implemented/reviewed, 91 tests pass, and live readiness is confirmed. Waiting for the user to post a genuine Telegram #codex request to complete identity/event/automatic-continuation acceptance. Tickets 09–14 remain blocked by the graph.
