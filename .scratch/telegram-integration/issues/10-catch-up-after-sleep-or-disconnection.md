# 10: Catch up after sleep or disconnection

**What to build:** Recover post-activation requests missed while offline without dropping backlog or replaying old work.

**Blocked by:** 09: Queue requests with fixed context and withdrawal.

**Status:** claimed

- [ ] Retain activation points across reconnects; newly enabled groups still use fresh-trigger readiness.
- [ ] Fetch missed requests in bounded batches without discarding remaining eligible backlog.
- [ ] Within a discovered batch order by message creation time with stable group/message ties, then retain immutable durable admission order.
- [ ] Already admitted or running work is not retroactively reordered; duplicate delivery and completed requests do not execute again.
- [ ] Exercise reconnection, multiple groups, batching, and a second reconnect through the shared interface and durable store.
