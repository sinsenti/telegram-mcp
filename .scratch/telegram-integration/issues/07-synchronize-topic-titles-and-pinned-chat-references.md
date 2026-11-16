# 07: Synchronize topic titles and pinned chat references

**What to build:** Rename each chat topic to its Codex chat title and maintain a pinned project/chat/status reference.

**Blocked by:** 05: Route task topics into real Codex projects.

**Status:** needs-info

- [ ] A placeholder topic follows the initial Codex title when available and later Codex title changes.
- [ ] Verify desktop-origin name changes, not only launcher-origin name notifications; handle initially missing titles without replacing the chat.
- [ ] Adapt topic titles to Telegram constraints while retaining the full reference where needed; manual topic renames never change routing.
- [ ] Pinned references show project, chat title, task status, and a working direct link where supported, otherwise searchable title and chat ID.
- [ ] Topic renaming and the pinned reference are separately observable and respect current folder access.
- [ ] Check the shared-interface outcomes and actual authorized Telegram rename/pin permissions; preserve status and explain failures.

## Implementation / acceptance gap

Implemented canonical metadata polling, bounded Unicode topic names, durable independent title/reference/pin outcomes, full plain text ID/link fallback and fresh folder access checks. Shared application and narrow external-contract tests pass. See [operation and live verification scope](../../../docs/title-references.md).

No desktop chat rename, Telegram topic rename, reference send/edit or pin was authorized for this ticket, so none was performed. Actual desktop-origin name propagation and selected account rename/pin permissions remain unverified. The ticket remains needs-info until those explicitly scoped live checks are approved and completed.
