# 12: Revoke folder access and pause task work

**What to build:** Removing a project group disables further Telegram operations, pauses its tasks, and requests interruption while preserving progress.

**Blocked by:** 09: Queue requests with fixed context and withdrawal.

**Status:** claimed

- [ ] Apply observed folder removal to every newly initiated read/write, including result uploads, renames, and pin updates; do not send a removal reply into that group.
- [ ] Pause queued requests and request active-turn interruption without promising instantaneous retraction of already accepted remote work.
- [ ] Keep task files, mappings, and results; pending results remain undelivered while access is disabled.
- [ ] Re-adding the group re-establishes readiness for fresh triggers and does not silently run paused requests.
- [ ] Check actual folder-update and Codex interruption contracts in authorized integration tests and exercise the complete pause/re-add flow at the shared interface.
