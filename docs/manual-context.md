# Reading and selecting manual task context

Use the existing `command` or MCP entry point. Every command reaches `Application.handle`; the selected Telegram folder is checked again for reads, search, continuation, execution, and reporting.

Select a message and its transitive replies:

```json
{"action":"read","group_id":-1003989567415,"message_id":3,"scope":"message","page_size":50}
```

Select its complete available topic instead:

```json
{"action":"read","group_id":-1003989567415,"message_id":3,"scope":"topic"}
```

Alternatively supply `link` instead of group/message IDs. Public `https://t.me/name/message`, private `https://t.me/c/channel/message`, and their `/thread/message` variants are supported, as is `?thread=...`. A topic-creation message (or General topic ID 1) defaults to whole-topic scope. An ordinary message link stays a message selection even when its path includes a thread. Explicit `scope` overrides this default. The actual peer and owning topic are validated; comment redirects and unsupported parameters are blocked.

The response preserves full message text, message IDs, immediate reply IDs, topic IDs, and attachment presence. `complete` describes whether retrieval exhausted available history without a known gap; deleted historical messages cannot be recovered. `page_complete` describes whether all retrieved messages have been presented. When `continuation` is present, request the next stored page:

```json
{"action":"read","continuation":"TOKEN_FROM_PREVIOUS_RESPONSE"}
```

Pages and choices survive a process restart. No text is shortened. Page size is 1–100 messages, so a single long message is still returned in full. Search and history fetch every available remote page, checking current access before each page request; only presentation is bounded. General topic history is filtered from group history because `getReplies(1)` does not represent complete General history.

Search one allowed group, or omit `group_id` to explicitly search all currently allowed groups:

```json
{"action":"search","group_id":-1003989567415,"query":"checklist","page_size":50}
```

Search returns `search_id` and numbered `choices`, and starts no task. Choose a result already shown on a returned page:

```json
{"action":"read","search_id":"SEARCH_ID","choice":2,"scope":"message"}
```

After reviewing a selection, execute it in the explicitly chosen test destination:

```json
{"action":"task","selection_id":"SELECTION_ID","destination":"test"}
```

A task can also use the explicit link/group source or a presented `search_id` and numeric `choice` directly. Search text alone never starts work. Task execution rereads the selected scope, blocks missing/incomplete context, and stores the full captured text and message relationships in its task folder. Follow-ups may supply the same source forms while retaining the original group, task folder, and Codex chat. Context containing attachments remains blocked until attachment handling is implemented in ticket 04. Task02's source-specific explanation and Markdown delivery remain the reporting workflow.

Acceptance evidence and current live-verification limitations are recorded in ticket 03. No automatic execution or monitoring is enabled by these commands.
