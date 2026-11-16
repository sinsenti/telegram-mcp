# 11: Recover known task progress after restart

**What to build:** Restart the local integration and continue known queued, captured, completed, and awaiting-report work without rerunning completed tasks.

**Blocked by:** 09: Queue requests with fixed context and withdrawal.

**Status:** ready-for-agent

- [ ] Reconstruct against the same real SQLite store and task folders; retain project/chat IDs, input snapshots, queue order, and progress.
- [ ] Known completed Codex work is not rerun merely because reporting was unfinished.
- [ ] Known unsent results go to their original source after access revalidation; already acknowledged deliveries are not repeated.
- [ ] Running or interrupted work is reconciled against known chat/turn identity before continuing, with clear blocked status when continuation is unavailable.
- [ ] Tests restart the module at lifecycle transitions and assert visible progress and external effects rather than private schema or call order.
