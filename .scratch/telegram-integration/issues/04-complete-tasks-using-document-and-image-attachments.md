# 04: Complete tasks using document and image attachments

**What to build:** Use selected attachments as real task input and return a usable Markdown result with clear handling of unsupported or missing input.

**Blocked by:** 03: Read complete discussions and find tasks.

**Status:** resolved

- [x] Preserve originals in task folders and demonstrate interpretation of text, images, PDFs, Word documents, and spreadsheets; a download alone is insufficient.
- [x] Use applicable Codex interpretation tools without duplicating document parsing inside the Telegram connector.
- [x] Unreadable selected supported inputs block with a concrete explanation; unsupported inputs are preserved and identified.
- [x] Unsupported content needed by the task, or of uncertain necessity, blocks until usable input or an explicit instruction is supplied.
- [x] Explicitly unnecessary unsupported attachments may be preserved and reported while other work completes.
- [x] Return the resulting Markdown and explanation to the original source; retain inputs/results for follow-up work.
- [x] Exercise representative content assertions through the shared interface, plus authorized live attachment/download/upload contracts.

## Comments

Implemented opaque original download/preservation, immutable per-run snapshots, existing Codex tool/skill handoff, per-input content evidence, explicit caller-only unsupported exclusions, blockers and source-specific follow-up reporting. See `docs/attachments.md` and `tests/fixtures/attachments/README.md` for boundaries and the concrete five-original live acceptance proposal.

Initial application and narrow adapter checks used substitutes; the actual five-format interpretation and Telegram round trip were subsequently verified in the approved live test below.

## Answer

Resolved after the explicitly approved five-file live test on 2026-11-16. [Recorded evidence](../attachments-live-test.json) contains preparation message 6, five original uploads 7–11, one follow-up turn in the existing chat, and verified explanation/Markdown replies 12–13 in the same topic. The task reused chat `01a1e427-dc70-7b23-ad61-c2782a815592` and its existing task folder. All five preserved originals match their independent source bytes, and downloading the delivered report matched the local Markdown exactly.

Actual Codex tool readback confirmed text reading, PDF extraction, Word interpretation, image viewing, and spreadsheet inspection/calculation from the preserved originals. Independent assertions checked the text token, image shapes/counts, PDF and Word phrases/locators, and spreadsheet total 18; all five inputs had interpreted evidence. No answer table was supplied or read. The connector contains no document-format parser. Reviewed failure paths cover unreadable/unsupported inputs, explicit unnecessary exclusions, retained partial results, and safe manual continuation after known input blockers. All 51 root tests passed. [Decision recorded in the implementation map](../map.md#decisions-so-far).
