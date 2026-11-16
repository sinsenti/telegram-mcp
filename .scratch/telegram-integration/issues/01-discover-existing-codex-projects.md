# 01: Discover existing Codex projects

**What to build:** Establish a verified, refreshable catalog of existing Codex project identities, names, and working directories so project groups can target real projects.

**Blocked by:** None (can start immediately).

**Status:** needs-info

- [ ] Produce reproducible evidence comparing the catalog with existing desktop projects, including updates after projects change.
- [x] Distinguish desktop saved projects from standalone experimental project records; do not create or import duplicate projects.
- [x] A setup snapshot is identified only as a development aid and does not satisfy ongoing discovery.
- [x] If no supported source can be established, record the concrete limitation and keep this ticket and dependent routing work unresolved.
- [ ] Demonstrate a consumer selecting a known project and obtaining its verified destination; preserve the successful known-directory connection evidence.

## Investigation result

2026-11-16: [Catalog evidence and reproduction](../../../docs/research/project-catalog.md). Two connected desktop catalog reads agree on 11 existing projects and the known `help` project's identity/destination. The preserved approved connection evidence is unchanged. No supported standalone listener transport to that desktop catalog, or refresh-after-change contract, has been established. Installed private runtime code maintains legacy/server identifier mappings; experimental `project/list` alone does not demonstrate desktop discovery.

No speculative adapter was added. Standalone probe initialization also requires SQLite writes outside the current sandbox, so it was stopped without broadening access. There were no live external writes.

**Remaining blocker:** establish supported read-only desktop-catalog access from a standalone process, verify identity/name/directory refresh after an authorized or naturally occurring project change, and then demonstrate an application consumer. Ticket 01 and dependent automatic routing remain unresolved. A repeated connected read or exported setup snapshot cannot satisfy these acceptance items.
