# Recovering Telegram reports

Completed Codex work and Telegram delivery have separate durable progress. Query
`status` with the task ID first. For a task in `reporting`, call the shared
Application command `{"action":"reconcile_reports","task_id":"…"}`. This never
starts a Codex turn. It delivers only missing explanation/file operations, reusing
the exact stored Telegram random ID and original destination/payload. Known
acknowledged results remain delivered. `reconcile_reports` without a task ID
reconciles already journaled sends and exposes legacy uncertainty; use the task
command afterwards to finish any file not yet journaled.

The completed result's document digest is committed with the task as soon as the result file is written, before the explanation's first remote call. Recovery verifies those original bytes before new or replayed uploads and after awaited sends. A local edit after a lost explanation acknowledgment therefore blocks upload rather than defining a new report payload; restoring the original bytes permits recovery. Partial legacy reports missing that original document identity require manual inspection.

Each new send commits its kind, group, source message/topic, payload, Telegram
account (when supported by the adapter), random ID and document digest before
sending. Document bytes must remain unchanged. Acknowledgment and generated
message identity commit together, including mappings observed before RPC return.
The adapter parses the RPC response for the matching random ID; the listener also
accepts recovered UpdateMessageID mappings. Ordinary RPC updates are not assumed
to reach Telethon Raw handlers.

The Telegram mechanism is same-account, same-peer random-ID deduplication, described
in [Telegram's outgoing update contract](https://core.telegram.org/api/updates#updatemessageid-updates).
Text equality, timestamps and outgoing direction are never delivery proof. A
retry that remains unknown (including RANDOM_ID_DUPLICATE without a mapping)
remains blocked; it never replaces the random ID. Self-authored candidate events
remain held until all unknown sends to their group resolve. Generated echoes are
excluded; actual human requests are admitted once through the existing policy.

Run `monitor_refresh` to reconcile uncertain readiness using its original cutoff
and send identity. Run `sync_reference` with the task ID to reconcile reference
creation using its original identity. Existing reference edits, pin changes and
topic renames read current remote state before deciding whether another operation
is necessary. Their successful effects survive a lost response without creating
another reference.

Every remote attempt rechecks current folder access. Disabled groups retain local
results and pending sends; restore access explicitly before recovery. This does
not resume a paused queue request. Older confirmed generated-sends rows remain
confirmed. Older uncertain rows have no reconstructible payload/random ID and
remain blockers requiring manual inspection. An older task left mid-reporting also
blocks when its missing reports cannot be associated with known identities, even
if an old unassociated send row says confirmed. Completed task report IDs remain
valid. An adapter without stable-ID support
can complete its first send but cannot replay an uncertain send.

## Validation

Application tests use real SQLite and task files with external Telegram/Codex
substitutes: replies and files accepted remotely before a lost response, restart,
repeat recovery, edited reports after lost text acknowledgments, mutations during sends, missing legacy document identity, historical queue-outcome preservation, revoked access, account changes, early echoes and held human
requests. Reference tests cover lost creation, edit, rename and pin acknowledgments.
Focused adapter tests verify stable IDs and matching UpdateMessageID extraction.
Live adapter evidence is recorded separately after the controlled allowed-group
text/upload replay fixture; local substitutes alone do not prove server dedup.
