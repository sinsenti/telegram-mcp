# 04: Complete tasks using document and image attachments

**What to build:** Use selected attachments as real task input and return a usable Markdown result with clear handling of unsupported or missing input.

**Blocked by:** 03: Read complete discussions and find tasks.

**Status:** ready-for-agent

- [ ] Preserve originals in task folders and demonstrate interpretation of text, images, PDFs, Word documents, and spreadsheets; a download alone is insufficient.
- [ ] Use applicable Codex interpretation tools without duplicating document parsing inside the Telegram connector.
- [ ] Unreadable selected supported inputs block with a concrete explanation; unsupported inputs are preserved and identified.
- [ ] Unsupported content needed by the task, or of uncertain necessity, blocks until usable input or an explicit instruction is supplied.
- [ ] Explicitly unnecessary unsupported attachments may be preserved and reported while other work completes.
- [ ] Return the resulting Markdown and explanation to the original source; retain inputs/results for follow-up work.
- [ ] Exercise representative content assertions through the shared interface, plus authorized live attachment/download/upload contracts.
