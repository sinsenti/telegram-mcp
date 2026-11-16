# Folder removal and returning groups

The selected folder remains the access boundary. Raw Telegram folder updates
normalize to `folder_changed` at the Application interface; periodic refresh and
operation-time membership checks also detect changes. A removal durably disables
the group before further group work, pauses queued/running requests and unfinished
tasks, and preserves task folders, chat/topic mappings and known results. Status
commands remain local and work while an execution is active.

Each removal advances a durable access epoch. An execution finishing from an older
epoch retains its known result but cannot replace paused state or initiate result
reporting. Remote operations accepted before observation cannot be retracted.

Known running chat/turn identities receive an interruption request through the
owning Codex adapter. Its acknowledgment records only that the request was
accepted, not that the turn stopped. A turn accepted after removal receives the
same check through the accepted-turn callback. Missing identities or unavailable
connection ownership cannot be represented as a successful interruption.

Re-addition sends readiness and establishes a new fresh-message cutoff. Previously
paused requests remain paused across restarts. A fresh request can continue the
remembered chat once its previous execution has a known terminal result. Uncertain
execution must be reconciled before another turn starts. An explicit
`reconcile_reports` command after readiness can deliver a preserved known result;
this never restarts Codex work or unpauses old queued requests.

## Controlled live verification

Only use the already authorized test group and test-owned topic/chat. Snapshot
that group's membership in the selected folder, start a controlled active turn,
remove only that membership, deliver the actual raw folder-update envelope, and
observe paused local state plus accepted-ID interruption. Confirm no newly
initiated group read/reply/upload/rename/reference/pin follows removal. Retain a
known result locally if completion races interruption. Re-add only the test group,
verify readiness and a fresh cutoff, and confirm old requests do not run. A fresh
request must continue the remembered chat. Restore only the test group's original
membership; preserve all other folder properties and concurrent user changes.


## Actual Telegram verification (2026-11-16)

The controlled folder-8/group test passed with real Telegram and isolated durable
Application state; see the saved folder-revocation live receipt. Telegram rejects
an explicit folder whose last include is removed, and overlapping include/exclude
entries did not remove the included test group. The authorized test therefore
used Saved Messages as a temporary non-group include while removing the only
project group. It enabled no additional project group. The test restored the
original group membership and removed the sentinel by editing a fresh folder
readback, preserving other current properties.

The original request remained paused across reconstruction and re-addition;
reads/search were blocked while disabled, readiness established a new cutoff,
and a fresh actual request was admitted without starting Codex. No Raw folder
self-echo arrived within four seconds of the account's own folder RPC, so the
receipt distinguishes actual membership-refetch observation from Raw delivery.
The listener's periodic refresh remains necessary for changes without an event.


The active acceptance used the real catalog and public numbered link interface to
attach the existing test-owned help chat, then dispatched a real fresh request.
The accepted callback durably saved the exact turn ID before the actual folder
change. Removal paused the request and recorded an interruption acknowledgment;
a separate authoritative readback of that same turn reported `interrupted`.
While the execution owner was still active, read/search returned `busy`, initiating
no content operation; the Telegram-only disabled test separately returned
`blocked`. All test clients closed and folder membership/sentinel were restored.

The active Application receipt proves the resumed existing-chat owner route.
Ticket 13 subsequently verified fresh owned-turn interruption after waiting for
the exact `turn/started` event and added that readiness gate. Both fresh and resumed
owned connections support interruption; an acknowledgment still requires terminal
observation. Cross-process control remains unverified and is never a fallback.
Historical rejected pre-readiness attempts remain in the receipts.

All exact synthetic Telegram identities from these probes (41–51) were registered
in the main state's durable generated-message ledger before any listener restart.
The separately verified frozen-document fixture 40 was registered too. This keeps
synthetic `#codex` sources from becoming future main-listener work; cutoff 32,
human message 35, queue, task and discovery state were preserved.
