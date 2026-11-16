# Working preferences

## Delegation

- Proactively delegate independent work to subagents when doing so is likely to improve speed or quality.
- Give each subagent a concrete task and expected result. Coordinate edits to shared files and combine the results before reporting back.
- Use as many agents as the task benefits from. Keep tightly dependent steps together.

## Dictation

- The user often dictates messages. Expect transcription errors, misspellings, missing punctuation, and similar-sounding words, especially in technical names.
- Infer obvious corrections from the surrounding context and continue without asking about every typo.
- When multiple interpretations would materially change the action, ask one concise clarification. Pay particular attention to ambiguous names, paths, numbers, and scope.

## Agent skills

### Issue tracker

Specs and tickets live as local Markdown files under `.scratch/`. Before reading or writing specs or tickets, read `docs/agents/issue-tracker.md`.

### Triage labels

Local ticket status values use the default triage labels. Before triaging or changing a ticket's status, read `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: a root `GLOSSARY.md` and `docs/adr/`, created as terms and decisions are resolved. Before exploring domain concepts or making design decisions, read `docs/agents/domain.md`.
