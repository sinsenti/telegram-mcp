# Generated result files

Status: implemented on `codex/result-files`

## Requested behavior

Tasks can return PDF, Word (DOCX), spreadsheet (XLSX/CSV/TSV), and image
(PNG/JPEG/WEBP/GIF) files alongside the existing explanation and Markdown report.
Plain text and Markdown attachments are also supported. This applies to manual
tasks, automatic requests, and same-chat follow-ups.

Codex creates and verifies requested files using its existing tools and enabled
skills, preserving its configured permissions. The connector transports generated
bytes; it does not implement document creation/conversion itself. A missing tool
or failed requested deliverable yields a blocker rather than a false success.

## File and delivery boundaries

- Each run receives a dedicated output directory inside its ignored task folder.
- Structured results list final file paths relative to that directory. No automatic
  directory scanning or arbitrary project-file uploads.
- Reject missing/nonregular files, traversal, symlinks, hardlinks, duplicate paths,
  unsupported formats, and misleading binary-file signatures/containers.
- Up to ten generated files, 50 MiB each, 100 MiB total, plus the Markdown report.
- Freeze all files into task-owned delivery copies and persist their hashes before
  sending the explanation or any file. Preserve original filenames and image bytes.
- Send files as downloadable Telegram documents to the exact source message/topic.
- Each file has its own stable delivery identity. Completion requires acknowledgment
  of the explanation, Markdown report, and every requested generated file.
- Lost acknowledgment/restart retries only missing operations using the same identity
  and frozen payload. It never reruns Codex merely to resend a file.
- Current folder access and existing paused-work rules govern every delivery.
- Existing Markdown-only tasks and saved reporting records remain recoverable.
- A follow-up uses a fresh output directory and manifest while preserving old files.

## Verification

Use the shared Application interface with real SQLite/task files and substituted
external adapters for binary delivery, partial acknowledgment/restart, mutation,
access removal, legacy results, and follow-up isolation. Supplement with focused
app-server manifest/skill contracts and file-boundary checks. Controlled live
delivery/generation uses only the previously authorized test resources, coordinates
with the user's running listener, and excludes synthetic trigger echoes.

## Acceptance

- All 228 project tests pass with locked uv dependencies, including legacy
  reporting, multi-file lost-acknowledgment recovery, revoked access, frozen bytes,
  per-run isolation, unsafe path rejection, and summary hardlink preservation.
- Independent review found no outstanding issues.
- A controlled real Codex turn generated `brief.pdf`, `letter.docx`, `budget.xlsx`
  and `chart.png` plus its Markdown summary. Telegram replies 61–66 in test topic
  59 had the exact expected filenames, MIME types and byte hashes.
- Repeated report reconciliation sent nothing and started no additional turn.
- Test clients closed, and exact generated message identities were registered in
  the main state to prevent synthetic messages becoming automatic requests.
- [Live receipt](./live-test.json). The user's listener needs a restart to load
  the new code; it was not stopped by this test.
