# 10: Catch up after sleep or disconnection

**What to build:** Recover post-activation requests missed while offline without dropping backlog or replaying old work.

**Blocked by:** 09: Queue requests with fixed context and withdrawal.

**Status:** resolved

- [x] Retain activation points across reconnects; newly enabled groups still use fresh-trigger readiness.
- [x] Fetch missed requests in bounded batches without discarding remaining eligible backlog.
- [x] Within a discovered batch order by message creation time with stable group/message ties, then retain immutable durable admission order.
- [x] Already admitted or running work is not retroactively reordered; duplicate delivery and completed requests do not execute again.
- [x] Exercise reconnection, multiple groups, batching, and a second reconnect through the shared interface and durable store.

## Answer

Implemented durable bounded catch-up through `Application.handle(monitor_catch_up)`, startup/periodic listener recovery, and scoped Telethon history pages. Original activation survives restart; re-addition resets only that group to fresh readiness. Batch admission order is immutable, atomic with page progress, and completed trigger identities remain deduplicated. Edited offline history is conservatively excluded with durable visible uncertainty; known pristine observations remain authoritative.

See [catch-up behavior](../../../docs/catchup.md). Shared application/SQLite tests cover restart, multiple groups, bounded backlog, atomic rollback, ordering, completed deduplication, edited uncertainty, and re-addition. Adapter and listener checks cover scoped RPCs/access removal and startup wiring. Live sleep/disconnect verification remains an external acceptance limitation, not claimed as performed.
