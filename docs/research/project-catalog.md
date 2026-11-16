# Existing Codex project catalog investigation

Verified on 2026-11-16 with installed Codex CLI 0.169.0. Ticket 01 remains unresolved: no supported, refreshable desktop catalog callable by the standalone listener has been established.

## What was verified

Two read-only calls to the connected desktop `list_projects({})` tool returned the same 11 saved projects. The known project selected from each response was:

| Field | Observed value |
| --- | --- |
| projectId | `c18094d8-b906-4609-834d-1f4a741fe843` |
| label | `help` |
| projectKind / hostId | `local` / `local` |
| path | `/home/user/git/personal/help` |

This identity and destination exactly match the [preserved connection test](../../.scratch/telegram-integration/desktop-connection-test-result.json). That test establishes known-directory execution and eventual desktop association; it explicitly records that standalone `project/read` did not recognize this desktop identifier. The connection evidence remains unchanged.

The connected tool can be called again by an assistant in this desktop conversation. Its availability here does not establish a callable transport for an independent Telegram listener. A setup export of its response would be a development snapshot, not ongoing automatic discovery.

## Protocol and runtime evidence

- `codex app-server generate-ts --experimental --out /tmp/telegram-catalog-protocol` exposes `project/list` (`cursor`, `limit`, sorting) and `project/read` (`projectId`). Generated schema proves request shape, not correspondence to desktop projects.
- The [official app-server protocol documentation](https://learn.chatgpt.com/docs/app-server) describes initialization, experimental opt-in, thread operations and transports. The examined page contains no `project/list` catalog contract for desktop saved projects. Absence from this page does not prove no supported integration exists; it means this investigation has not established one.
- Read-only inspection of installed `/usr/lib/chatgpt/resources/app.asar`, entry `.vite/build/early-bootstrap-226-2f6bd181558008cf.js`, found `listProjects` paging through `project/list`, and `storeProject` maintaining `legacyProjectIdsByServerId` and `serverProjectsByLegacyId`. The desktop also uses `APP_SERVER_PROJECT_ID_BY_LEGACY_PROJECT_ID_BY_HOST` to look up a server identity before `project/read`. This private implementation distinguishes desktop identity from the raw server identity; it is diagnostic evidence, not a supported adapter contract.
- `codex app-server proxy --help` offers a control-socket proxy. Neither this help nor the inspected public documentation establishes that its registry has the desktop's saved-project identities and refresh behavior. No control socket was contacted.
- A fresh standalone read-only probe could not initialize in the current filesystem sandbox: opening `/home/user/.codex/memories_1.sqlite` failed with SQLite code 14. No database/config permission was broadened to hide that limitation. The existing approved test remains the live evidence of registry mismatch.

No chats or projects were created/imported, no desktop configuration was changed, and no secrets were read. No project-change test was performed, because desktop project writes are outside this investigation's authorization. Repeated unchanged reads are not evidence of refresh after a project change.

## Reproduction and remaining acceptance

1. From a desktop-connected assistant, call `list_projects({})` and select `help` by returned identifier; compare its path with the preserved connection test above.
2. Generate the installed experimental protocol bindings using the command above; inspect `v2/ProjectListParams.ts`, `v2/ProjectListResponse.ts`, and `v2/ProjectReadParams.ts`.
3. Establish a documented or explicitly supported read-only transport callable by a standalone process that returns the actual desktop identity, display name, and working directory. Document how to refresh it and handle removed/renamed projects. Do not parse private global state or scan directories as a substitute.
4. Under separate explicit authorization, compare that source with connected desktop results before and after a controlled project change, including identifier mapping if needed. A supported naturally occurring update could also supply this evidence.
5. Only then implement and test a catalog adapter and application consumer, demonstrate selecting this known project's verified destination, and unblock automatic routing.

No production adapter or consumer is added: doing so now would make an unsupported transport or stale setup snapshot appear ready. The remaining blocker is both the supported standalone catalog access contract and evidence of refresh after real project changes. A further read-only API reference or supported desktop bridge could resolve the access question without new project writes.
