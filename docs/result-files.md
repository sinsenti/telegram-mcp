# Generated result files

Ask for the formats you need in your task message, for example:

> #codex Create a one-page PDF summary and an Excel budget. Include a PNG chart.

The result includes a short explanation, the usual Markdown summary, and the
requested generated files as replies in the original topic. Images are sent as
downloadable original files to preserve their bytes and filenames.

Supported output types are PDF, Word DOCX, Excel XLSX, CSV/TSV, PNG, JPEG, WEBP,
GIF, Markdown and plain text. Each run can return up to ten generated files,
50 MiB per file and 100 MiB total, in addition to its Markdown summary. Larger
deliverables need to be reduced or split in a new request.

Codex uses its enabled creation tools and skills to create and check the files.
The connector does not convert Markdown automatically into every format. A task
asking for no extra formats still returns its ordinary Markdown report. Missing
tools, required permissions, unavailable files or invalid generated formats block
the task instead of producing a misleading completion.

## Preserved files and delivery recovery

Each run has a separate `artifacts/<run>` directory in its ignored task folder.
The structured Codex result explicitly lists finished deliverables relative to
that directory. The integration does not scan the whole project for files.
Paths outside the run directory, links and unsupported files cannot be uploaded
as generated results. File headers/Office container checks establish the promised
format; they do not replace the creation skill's content and visual checks.

Before sending the result explanation, the connector copies all listed files to
`deliverables/<run>`, records their original names, sizes and SHA-256 hashes, and
stores the complete delivery manifest. Task status exposes this as `result_files`.
The existing `document` field remains the Markdown summary; `report_ids` contains
the explanation followed by Markdown and generated-file acknowledgments.

Each file uses a separate durable Telegram operation identity and immutable upload
bytes. Restart recovery sends only missing deliveries with the same identity and
payload. It does not run Codex again to recover an upload. Changed or missing
delivery copies block further sends; changing Codex's source output after freezing
cannot change the delivered file. Completion requires every file acknowledgment.
Folder removal retains output and pauses delivery under the existing access rules.
See [report recovery](report-recovery.md) for reconciliation commands.

A follow-up retains the chat and task folder, uses a fresh output directory and
manifest, and preserves prior runs' files. Saved Markdown-only tasks retain their
existing reporting behavior and remain recoverable.

## Verification

The automated suite covers multi-file lost-acknowledgment recovery with real
SQLite/task files, frozen source/delivery mutations, access removal, unsafe paths,
format/size limits, legacy reports and same-chat follow-ups. A controlled live
Codex task generated PDF, DOCX, XLSX and PNG outputs; downloading all five result
files (including Markdown) verified original names, MIME types and matching bytes.
Repeating reconciliation produced no new sends. [Live evidence](../.scratch/result-files/live-test.json).
