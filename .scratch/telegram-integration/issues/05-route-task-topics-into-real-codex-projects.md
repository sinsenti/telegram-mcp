# 05: Route task topics into real Codex projects

**What to build:** Automatically bind a project group to its existing Codex project and create or continue its topics' chats in the correct real destination.

**Blocked by:** 01: Discover existing Codex projects, 02: Run a manual text task and report its result.

**Status:** needs-info

- [ ] An exact unique group-name match selects the verified project; absent or ambiguous matches ask for explicit selection and execute no work.
- [ ] Persist group/project and topic/chat identities independently of names; topics inherit the group assignment.
- [ ] A new task creates a chat and task folder; follow-ups reuse them and use the actual returned chat identifier.
- [ ] The desktop eventually shows work under the existing project; tolerate delayed placement with bounded reconciliation and visible unresolved status.
- [ ] Do not import duplicate projects, move chats to hide failures, or silently fall back to the test destination.
- [ ] Group and topic renames do not reroute established work; production permissions and real working directories are respected.
- [ ] Verify routing/continuation at the shared interface and use preserved desktop evidence plus appropriately authorized live checks.

## Implementation and remaining acceptance

Routing is implemented and verified at the preapproved Application.handle seam with real SQLite/files and external adapters, including a subprocess Codex protocol fixture. See [routing contract and concrete live test plan](../../../docs/project-routing.md). The installed generated experimental protocol supports thread/start projectId and thread/read canonical projectId/cwd. Standalone reconciliation reports desktop visibility as unverified honestly.

No new live chats/turns or Telegram writes were authorized for ticket 05, so live routed project placement and continuation acceptance remain pending the specific plan's authorization. Earlier tickets 01–04 evidence covers their own scopes and is not presented as proof of this new route.
