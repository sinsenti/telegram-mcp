# 01: Discover existing Codex projects

**What to build:** Establish a verified, refreshable catalog of existing Codex project identities, names, and working directories so project groups can target real projects.

**Blocked by:** None (can start immediately).

**Status:** needs-info

- [ ] Produce reproducible evidence comparing the catalog with existing desktop projects, including updates after projects change.
- [x] Distinguish desktop saved projects from standalone experimental project records; do not create or import duplicate projects.
- [x] A setup snapshot is identified only as a development aid and does not satisfy ongoing discovery.
- [ ] If no supported source can be established, record the concrete limitation and keep this ticket and dependent routing work unresolved.
- [x] Demonstrate a consumer selecting a known project and obtaining its verified destination; preserve the successful known-directory connection evidence.

## Investigation result

2026-11-16: [Corrected catalog evidence, adapter usage, and remaining acceptance](../../../docs/research/project-catalog.md).

A real standalone `project/list` probe matches all 11 desktop projects exactly by name and directory. Desktop-tool and server project IDs differ; the earlier failed `project/read` with a desktop ID was insufficient evidence of separate catalogs. The installed experimental CLI protocol provides a callable source, with explicit experimental opt-in and upgrade revalidation required.

Added `CodexProjectCatalog.refresh()` and `destination(server_project_id)`; actual adapter reads selected the known `help` server ID and returned `/home/user/git/personal/help`, preserving the original connection evidence. TDD subprocess-wire checks cover pagination, refreshed changes/removal, and invalid metadata. No private desktop state or setup snapshot is used as the source.

**Remaining blocker:** demonstrate fresh catalog observations after a real desktop project change. No project writes are authorized for this investigation. The linked evidence describes a concrete temporary rename-and-restore test for review, or a naturally occurring user change can supply the missing check. Therefore ticket 01 remains `needs-info`; full automatic routing acceptance remains unresolved until that evidence exists.
