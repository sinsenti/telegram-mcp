# 04: Complete tasks using document and image attachments

**What to build:** Use selected attachments as real task input and return a usable Markdown result with clear handling of unsupported or missing input.

**Blocked by:** 03: Read complete discussions and find tasks.

**Status:** needs-info

- [ ] Preserve originals in task folders and demonstrate interpretation of text, images, PDFs, Word documents, and spreadsheets; a download alone is insufficient.
- [ ] Use applicable Codex interpretation tools without duplicating document parsing inside the Telegram connector.
- [ ] Unreadable selected supported inputs block with a concrete explanation; unsupported inputs are preserved and identified.
- [ ] Unsupported content needed by the task, or of uncertain necessity, blocks until usable input or an explicit instruction is supplied.
- [ ] Explicitly unnecessary unsupported attachments may be preserved and reported while other work completes.
- [ ] Return the resulting Markdown and explanation to the original source; retain inputs/results for follow-up work.
- [ ] Exercise representative content assertions through the shared interface, plus authorized live attachment/download/upload contracts.

## Comments

Implemented opaque original download/preservation, immutable per-run snapshots, existing Codex tool/skill handoff, per-input content evidence, explicit caller-only unsupported exclusions, blockers and source-specific follow-up reporting. See `docs/attachments.md` and `tests/fixtures/attachments/README.md` for boundaries and the concrete five-original live acceptance proposal.

Local application and narrow adapter contracts pass. Fixed fixture content assertions use an orchestration fake; actual interpretation is not claimed. Live interpretation/download/upload acceptance remains unverified and requires explicit authorization for the bounded existing-chat/topic follow-up. Status stays needs-info until demonstrated.
