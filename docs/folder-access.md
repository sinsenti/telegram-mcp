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
execution must be reconciled before another turn starts.

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
