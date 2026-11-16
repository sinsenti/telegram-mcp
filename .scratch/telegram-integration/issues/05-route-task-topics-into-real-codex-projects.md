# 05: Route task topics into real Codex projects

**What to build:** Automatically bind a project group to its existing Codex project and create or continue its topics' chats in the correct real destination.

**Blocked by:** 01: Discover existing Codex projects, 02: Run a manual text task and report its result.

**Status:** resolved

- [x] An exact unique group-name match selects the verified project; absent or ambiguous matches ask for explicit selection and execute no work.
- [x] Persist group/project and topic/chat identities independently of names; topics inherit the group assignment.
- [x] A new task creates a chat and task folder; follow-ups reuse them and use the actual returned chat identifier.
- [x] The desktop eventually shows work under the existing project; tolerate delayed placement with bounded reconciliation and visible unresolved status.
- [x] Do not import duplicate projects, move chats to hide failures, or silently fall back to the test destination.
- [x] Group and topic renames do not reroute established work; production permissions and real working directories are respected.
- [x] Verify routing/continuation at the shared interface and use preserved desktop evidence plus appropriately authorized live checks.

## Implementation and remaining acceptance

Routing is implemented and verified at the preapproved Application.handle seam with real SQLite/files and external adapters, including a subprocess Codex protocol fixture. See [routing contract and concrete live test plan](../../../docs/project-routing.md). The installed generated experimental protocol supports thread/start projectId and thread/read canonical projectId/cwd. Standalone reconciliation reports desktop visibility as unverified honestly.

No new live chats/turns or Telegram writes were authorized for ticket 05, so live routed project placement and continuation acceptance remain pending the specific plan's authorization. Earlier tickets 01–04 evidence covers their own scopes and is not presented as proof of this new route.

## Integration verification

The shipped CLI/MCP constructor now injects the catalog (commit 970a31d). A real production CLI `action=project` request for the allowed test group returned the existing help server ID and `/home/user/git/personal/help` without starting a chat/turn. All 63 root tests pass, including setup/QR checks. The bounded one-new-topic, one-new-chat, two-marker-turn live test is prepared; authorization has been requested but has not yet been received. Stage-one live approvals do not cover that additional test.

## Answer

Resolved after the explicitly approved routing test on 2026-11-16. [Live evidence](../routing-live-test.json) records new topic 14 in the existing allowed group, marker requests 15 and 18, one new chat `01a1e473-8c30-7821-99f1-6279e9947a2a`, two completed turns, and verified source-specific text/Markdown reports. Both requests reused task `adf97cc4bc1043d294804cf9650af812`, its task folder and chat, and executed in the existing help directory. Downloaded report bytes matched the local Markdown in both runs.

Connected desktop listing placed the same chat under existing help legacy project ID `c18094d8-b906-4609-834d-1f4a741fe843`; canonical server observations use the corresponding server project ID. No moves, imports or replacement projects were used. Desktop readback confirmed both turns completed with zero tool actions, consistent with the no-project-file-change instructions. [Decision recorded in the implementation map](../map.md#decisions-so-far).
