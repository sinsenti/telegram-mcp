# 12: Revoke folder access and pause task work

**What to build:** Removing a project group disables further Telegram operations, pauses its tasks, and requests interruption while preserving progress.

**Blocked by:** 09: Queue requests with fixed context and withdrawal.

**Status:** resolved

- [x] Apply observed folder removal to every newly initiated read/write, including result uploads, renames, and pin updates; do not send a removal reply into that group.
- [x] Pause queued requests and request active-turn interruption without promising instantaneous retraction of already accepted remote work.
- [x] Keep task files, mappings, and results; pending results remain undelivered while access is disabled.
- [x] Re-adding the group re-establishes readiness for fresh triggers and does not silently run paused requests.
- [x] Check actual folder-update and Codex interruption contracts in authorized integration tests and exercise the complete pause/re-add flow at the shared interface.


## Answer

Implemented durable folder-access epochs at Application and the resolved-peer
adapter boundary. Observed removal pauses pending/active work before requesting
interruption, gates every new group operation, preserves known output and prevents
stale completion from replacing paused state. Re-addition requires readiness and
a fresh cutoff; old requests stay paused. Explicit selected reporting may deliver
a preserved known result after readiness, without restarting Codex.

Validation: 128 complete hermetic tests passed, followed by 21 monitoring tests
after the final batch-removal ordering change. Controlled real Telegram removal,
SQLite reconstruction, restoration/readiness, old-paused/fresh-pending admission,
and real resumed-chat App interruption passed. Exact turn readback reported
`interrupted`; acknowledgment alone was not treated as terminal proof.
[Actual receipts](../folder-revocation-live-test.json),
[behavior and contract limitations](../../../docs/folder-access.md).

Telegram rejects an empty explicit folder, so the authorized test temporarily used
Saved Messages as a non-group sentinel, restoring only its and the test group's
membership components from a fresh folder read. No extra project group became
allowed. No Raw self-echo appeared within four seconds of the account's own folder
RPC; membership refetch exercised the normalized observation. Fresh owned-turn interruption was subsequently verified by ticket 13 after
waiting for the exact `turn/started` event, with a corresponding production
readiness gate. Both owned routes are supported; cross-process control remains
unverified and is never used as fallback. All exact synthetic fixture identities
were registered in the main generated-message ledger without advancing the
activation cutoff or changing human/queue/discovery state.
