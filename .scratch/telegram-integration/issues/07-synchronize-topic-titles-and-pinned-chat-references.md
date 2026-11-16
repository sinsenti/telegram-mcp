# 07: Synchronize topic titles and pinned chat references

**What to build:** Rename each chat topic to its Codex chat title and maintain a pinned project/chat/status reference.

**Blocked by:** 05: Route task topics into real Codex projects.

**Status:** ready-for-agent

- [ ] A placeholder topic follows the initial Codex title when available and later Codex title changes.
- [ ] Verify desktop-origin name changes, not only launcher-origin name notifications; handle initially missing titles without replacing the chat.
- [ ] Adapt topic titles to Telegram constraints while retaining the full reference where needed; manual topic renames never change routing.
- [ ] Pinned references show project, chat title, task status, and a working direct link where supported, otherwise searchable title and chat ID.
- [ ] Topic renaming and the pinned reference are separately observable and respect current folder access.
- [ ] Check the shared-interface outcomes and actual authorized Telegram rename/pin permissions; preserve status and explain failures.
