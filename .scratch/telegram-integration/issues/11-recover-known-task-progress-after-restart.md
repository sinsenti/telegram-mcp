# 11: Recover known task progress after restart

**What to build:** Restart the local integration and continue known queued, captured, completed, and awaiting-report work without rerunning completed tasks.

**Blocked by:** 09: Queue requests with fixed context and withdrawal.

**Status:** resolved

- [x] Reconstruct against the same real SQLite store and task folders; retain project/chat IDs, input snapshots, queue order, and progress.
- [x] Known completed Codex work is not rerun merely because reporting was unfinished.
- [x] Known unsent results go to their original source after access revalidation; already acknowledged deliveries are not repeated.
- [x] Running or interrupted work is reconciled against known chat/turn identity before continuing, with clear blocked status when continuation is unavailable.
- [x] Tests restart the module at lifecycle transitions and assert visible progress and external effects rather than private schema or call order.


## Answer

Implemented `recover` through the shared Application boundary and exposed it in the MCP action schema. Recovery holds the existing OS execution ownership, reconstructs the same store/files, preserves queue admission sequence and task binding, validates captured snapshots/originals, and resumes only captured work without an unresolved external intent. A durably acknowledged chat creation continues the same chat; unknown creation never creates a replacement.

Completed results are persisted before placement/reporting. Known turns are observed by exact identity, or correlated using the saved client UUID after a lost start response. Completed malformed output stays terminal and blocked. Running/unknown work blocks new execution; interrupted/failed work retains explicit terminal progress. Result output is retained even when a changed original temporarily blocks validation. Paused work can be observed without reporting or resuming authority.

Reports delegate to ticket 14's durable operation journal and current access checks. Matching queue outcomes are updated through Monitoring helpers without changing historical runs. Already acknowledged reports remain delivered and original reply destinations remain fixed.

Validation: 144-test integrated suite passed with final ticket 12/13 branches and root `30f7a65` reporting fix; after the final observed-result preservation slice, all 17 restart tests and the thin MCP transport test passed. Restart tests use real SQLite/task folders and substitute external adapters only, covering captured original files/evidence, queue order, task/chat/project identities, partial reports, worker ownership, accepted/lost turn responses, missing create response, malformed completion, paused known turns and terminal result persistence. [Operational behavior and limits](../../../docs/known-recovery.md).

No new live Telegram client or Codex turn was started for this ticket. Production observation is integrated with ticket 13's paginated adapter; live caller-UUID persistence and desktop-owned interruption remain the explicitly documented adapter limitations rather than claimed guarantees.
