# 01: Discover existing Codex projects

**What to build:** Establish a verified, refreshable catalog of existing Codex project identities, names, and working directories so project groups can target real projects.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Produce reproducible evidence comparing the catalog with existing desktop projects, including updates after projects change.
- [x] Distinguish desktop saved projects from standalone experimental project records; do not create or import duplicate projects.
- [x] A setup snapshot is identified only as a development aid and does not satisfy ongoing discovery.
- [x] If no supported source can be established, record the concrete limitation and keep this ticket and dependent routing work unresolved.
- [x] Demonstrate a consumer selecting a known project and obtaining its verified destination; preserve the successful known-directory connection evidence.

## Investigation result

2026-11-16: [Corrected catalog evidence, adapter usage, and remaining acceptance](../../../docs/research/project-catalog.md).

A real standalone `project/list` probe matches all 11 desktop projects exactly by name and directory. Desktop-tool and server project IDs differ; the earlier failed `project/read` with a desktop ID was insufficient evidence of separate catalogs. The installed experimental CLI protocol provides a callable source, with explicit experimental opt-in and upgrade revalidation required.

Added `CodexProjectCatalog.refresh()` and `destination(server_project_id)`; actual adapter reads selected the known `help` server ID and returned `/home/user/git/personal/help`, preserving the original connection evidence. TDD subprocess-wire checks cover pagination, refreshed changes/removal, and invalid metadata. No private desktop state or setup snapshot is used as the source.

**Historical blocker, now resolved below:** demonstrate fresh catalog observations after a real desktop project change. No project writes are authorized for this investigation. The linked evidence describes a concrete temporary rename-and-restore test for review, or a naturally occurring user change can supply the missing check. Therefore ticket 01 remains `needs-info`; full automatic routing acceptance remains unresolved until that evidence exists.

## Answer

Resolved after the approved desktop-origin rename and restoration on 2026-11-16. [Live catalog evidence](../catalog-refresh-live-test.json) shows both connected desktop and fresh standalone reads observing `help catalog refresh check`, then `help`, with unchanged corresponding IDs, working directory, and 11-project count. This demonstrates real refresh rather than a setup snapshot. The user performed the desktop UI steps because saved-project renaming is not exposed by connected tools.

An earlier server-origin test also refreshed the server catalog and was restored, but did not update the desktop cached label. Installed desktop code explains the direction: desktop edits update both server and desktop cache; server edits do not rewrite that cache. The final desktop-origin test verifies the actual source flow. The experimental adapter remains version-specific and uses server IDs rather than legacy desktop IDs. [Decision recorded in the implementation map](../map.md#decisions-so-far).
