# Issue tracker: Local Markdown

Issues and specs live as Markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`.
- The spec is `.scratch/<feature-slug>/spec.md`.
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`.
- Triage state is a `Status:` line near the top of each issue file. Use the role strings in `triage-labels.md`.
- Append comments and conversation history under a `## Comments` heading.

## Skill operations

- "Publish to the issue tracker": create the relevant file under `.scratch/<feature-slug>/`.
- "Fetch the relevant ticket": read the referenced ticket file.

## Wayfinding operations

- Map: `.scratch/<effort>/map.md`, holding Notes, Decisions-so-far, and Fog.
- Child ticket: `.scratch/<effort>/issues/NN-<slug>.md`, with the question in the body and a `Type:` of `research`, `prototype`, `grilling`, or `task`.
- Dependencies: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every listed blocker is `resolved`.
- Frontier: select the first numbered open, unblocked, unclaimed ticket.
- Claim: set `Status: claimed` and save before starting work.
- Resolve: append an `## Answer`, set `Status: resolved`, and add a summary and link to the map's Decisions-so-far.
