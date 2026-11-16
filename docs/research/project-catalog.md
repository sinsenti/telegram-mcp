# Existing Codex project catalog investigation

Verified on 2026-11-16 with Codex CLI 0.169.0. A callable, refreshable **experimental** catalog is available through standalone app-server `project/list`. Ticket 01 is resolved after the desktop-origin rename and restoration check below.

## Corrected identity finding

An earlier investigation inferred that a failed read using a desktop-tool project ID meant the standalone registry was separate. A real `project/list` probe disproved that inference: all 11 saved desktop projects match the standalone catalog exactly by display name and working directory, with no missing or extra projects. The identifiers differ between the desktop tool and the app-server protocol.

| Field | Connected desktop tool | Standalone app-server |
| --- | --- | --- |
| Project name | `help` | `help` |
| Project ID | `c18094d8-b906-4609-834d-1f4a741fe843` | `01a1df7d-648f-7942-a075-ae429872b8cd` |
| Working directory | `/home/user/git/personal/help` | `/home/user/git/personal/help` |

This is an observed name/path correspondence, not a guaranteed public legacy-ID mapping algorithm. Do not pass desktop-tool identifiers directly to `project/read`, or derive protocol IDs from names. Persist the actual server ID returned by the catalog. Removed projects must be selected again; do not redirect to a same-name replacement silently.

The [preserved connection test](../../.scratch/telegram-integration/desktop-connection-test-result.json) remains unchanged and establishes known-directory execution and eventual desktop placement. Its desktop-ID `project/read` failure is consistent with the different identifier namespaces above; it does not disprove current project discovery.

## Supported surface and operational limits

The installed CLI generates the `project/list` request/response schema with:

```sh
codex app-server generate-ts --experimental --out /tmp/telegram-catalog-protocol
```

Inspect `v2/ProjectListParams.ts`, `ProjectListResponse.ts`, `Project.ts`, and `ProjectReadParams.ts`. The project methods are experimental. The [official app-server protocol documentation](https://learn.chatgpt.com/docs/app-server) explains initialization and experimental API opt-in; its examined API overview does not document this project catalog. Therefore this adapter depends on the verified installed CLI protocol, with explicit `capabilities.experimentalApi: true`, and should be revalidated on CLI upgrades. It does not claim a stable cross-version desktop catalog API.

Read-only installed runtime inspection additionally found desktop legacy/server identity maps (`legacyProjectIdsByServerId`, `serverProjectsByLegacyId`, and `APP_SERVER_PROJECT_ID_BY_LEGACY_PROJECT_ID_BY_HOST`) in `/usr/lib/chatgpt/resources/app.asar`, `.vite/build/early-bootstrap-226-2f6bd181558008cf.js`. This explains the observed mismatch; production code does not parse the archive, desktop global state, or these private maps.

The existing control-socket symlink was inspected and `codex app-server proxy` attempted. Its target is absent and the proxy reports ENOENT. No daemon was started or reconfigured. Standalone stdio works and is the adapter's verified transport.

Normal app-server startup requires access to its runtime SQLite databases. The initial sandbox attempt could not open `memories_1.sqlite`; the authorized follow-up used ordinary local runtime access outside that filesystem sandbox. No auth file was read, and desktop configuration was not changed.

## Adapter and consumer

`telegram_integration.catalog.CodexProjectCatalog.refresh()` launches a short-lived `codex app-server --stdio`, opts into the experimental API, and retrieves every catalog page. Each call rereads the source; it keeps no stale setup snapshot. It rejects invalid protocol metadata and repeated pagination cursors, and closes only its own process. Project records carry server identity, display name, and all roots.

`destination(server_project_id)` is the narrow consumer: it refreshes, finds the selected identity, and returns its sole absolute local working directory. Missing identities, malformed data, and multiple/no roots produce a visible `CatalogUnavailable` rather than a guessed destination. Automatic Telegram group-name matching and durable routing are subsequent application work.

Verified real consumer output:

```python
from telegram_integration.catalog import CodexProjectCatalog
catalog = CodexProjectCatalog()
projects = catalog.refresh()  # 11 observed projects
known = next(project for project in projects if project.name == 'help')
assert known.id == '01a1df7d-648f-7942-a075-ae429872b8cd'
assert str(catalog.destination(known.id)) == '/home/user/git/personal/help'
```

A separate comparison of the connected desktop snapshot against actual adapter results confirmed exact name/path equality for all 11 projects. This checks the source, not arbitrary filesystem scanning. The tests use a subprocess wire fixture to verify paging, updated destinations after a source change, removal, and invalid metadata. They do not establish real desktop propagation after project changes.

Run the contract checks with:

```sh
python3 -m unittest discover -s tests -p 'test_catalog.py'
```

## Original acceptance gap (resolved below)

At the initial investigation stage, no project had been changed. Repeated unchanged real reads and a fixture mutation do not demonstrate refresh after a real desktop project change, including server-to-desktop propagation. The consumer and experimental source are usable now, but ticket 01 remains unresolved until this check passes.

A concrete reversible test, pending explicit authorization, would temporarily rename existing `help` server project `01a1df7d-648f-7942-a075-ae429872b8cd` to `help catalog refresh check` with `project/update` specifying only `projectId` and `name`, read both the refreshed standalone catalog and connected desktop catalog with bounded reconciliation, and restore the exact original name `help` in a `finally` step. Roots, metadata, project count, and chats would remain unchanged. A naturally occurring user rename could alternatively supply this evidence without an agent project write.

No chats/projects were created or imported, no turns were started, and no live project updates were performed. A connected-tool setup export remains only a development aid and is not used by the production adapter.

The server-origin request subsequently used in the approved diagnostic test was:

```json
{"id":10,"method":"project/update","params":{"projectId":"01a1df7d-648f-7942-a075-ae429872b8cd","name":"help catalog refresh check"}}
```

The compensating restore request must be issued on every path after the rename attempt, and its readback verified:

```json
{"id":11,"method":"project/update","params":{"projectId":"01a1df7d-648f-7942-a075-ae429872b8cd","name":"help"}}
```

## Completed live acceptance

The [recorded final test](../../.scratch/telegram-integration/catalog-refresh-live-test.json) starts with the desktop Edit project action, not a raw server rename: the user changed only `help` to `help catalog refresh check`, then restored `help` after verification. Both connected desktop and fresh standalone reads observed each saved name. Corresponding desktop/server IDs, the existing working directory, and the 11-project count stayed unchanged. This verifies ongoing source refresh and resolves ticket 01.

The earlier approved server-origin name update was also restored. Eight bounded desktop observations retained the old label because the installed desktop deliberately keeps a separate cache: its own `renameLocal` calls the server `project/update` and then updates that cache, while server record ingestion does not rewrite cached project names. This directionality was confirmed by read-only inspection of the installed application, not by introducing a private-state production adapter. The current catalog uses only the verified experimental server protocol and must still be revalidated on CLI upgrades.
