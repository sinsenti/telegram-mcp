# Fresh-request monitoring

The local listener and manual transport call the same `Application.handle` boundary. Use one application process per state directory. The listener prevents a second listener from owning its state directory; do not run a separate manual CLI/MCP application against that database while it runs. In-process manual execution returns `busy` while the automatic worker owns execution. Admission and observable status remain available during a Codex turn, and only the execution owner closes its Codex connections.

After connecting the existing Telegram account and selecting the intended folder, the runnable entry point is:

```sh
uv run --locked --env-file .env python -m telegram_integration.listener --state-directory .local --folder-id 8
```

Starting this command enables monitoring, writes readiness messages in newly enabled groups, and permits real Codex work from fresh requests. Do not start it merely to inspect configuration. `--sync-references` additionally permits periodic linked-topic title/reference updates. The state directory must be the directory containing the authorized account's `telegram.session` and `state.sqlite`; selecting a different directory does not migrate them. Credentials come from `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`. No changes were made to the existing manual CLI setup/login flow.

## Application commands

- `monitor_enable` and `monitor_refresh`: refresh current folder membership; establish readiness for new/re-added groups. They perform Telegram writes.
- `monitor_status`: expose durable group readiness, request states/outcomes, discovery progress, and held uncertain echoes. It performs no remote operations.
- `telegram_event`: normalized original-new-message evidence, including connected account, actual author, actual group/message identity, text, edit and forwarding evidence. The listener alone translates envelopes; Application owns eligibility.
- `dispatch_pending`: execute the earliest pending request through the existing real-project topic workflow. A linked topic follows its chat; an unlinked topic creates its project chat.

Each activation records a Telegram message cutoff before sending readiness and advances the cutoff through the confirmed readiness message. Historical markers remain readable context, while only a fresh unedited, unforwarded message authored by the connected user can create work. Edits and historical observations never supply original posting evidence. Ordinary text remains context. Requests use topic context bounded by their trigger's message ID; later text and attachments are excluded. Execution rechecks that the trigger still exists and retains its marker.

Trigger identity and discovery progress commit in one SQLite transaction. Duplicate delivery across restart does not create another request. Discovery progress is application state, distinct from Telethon's own update cursor. NewMessage handlers are registered before readiness and `catch_up`; handlers admit work promptly while the worker executes separately.

All integration-generated text/documents/references must pass through Application's generated-send wrapper. It persists a pending send before invoking Telegram, then records the successful message ID and confirmation in one transaction. RPC responses are parsed for the matching random-ID mapping because Telethon does not dispatch its own outgoing RPC results as ordinary updates. Sender identity and outgoing flags alone are insufficient because this integration uses the same account as the human. While a send is pending, fresh candidates wait with their original event evidence. After normal command completion, up to 100 held events are revisited in source order for groups with no unresolved sends. Confirmed generated identities are discarded, eligible human markers are admitted once through the same current-access/readiness/dedup policy, and ordinary context or edits never become tasks. This admission does not acquire execution ownership or close an active worker's connection. Listener dispatch ticks continue bounded draining, including known holds surviving restart. Status inspection remains local and does not drain holds. An uncertain send conservatively holds self-authored candidates for that group, preserving their envelopes in status instead of executing them. Ticket 14 must reconcile/release these held candidates and uncertain sends; this implementation deliberately never retries an uncertain send with a fresh identity.

## Delivery limits and live acceptance

This ticket supplies the admission and basic worker foundation. Ticket 09 completes queue withdrawal/order/input lifecycle behavior; 10 supplies paginated application catch-up; 11–14 supply crash/task/action/report reconciliation and interruption. In particular a request left `running` at process exit is retained and does not restart automatically. Removing a group pauses pending requests and prevents further Telegram operations through current access checks; running-turn interruption is ticket 12. Offline edited history cannot prove that the original message had a marker and is conservatively excluded with a visible reason. Readiness with an uncertain response remains unresolved rather than being resent or resetting the activation cutoff silently.

No live activation, readiness message, or automatic turn was performed for ticket 08. The automated checks use real SQLite and task files with external Telegram/Codex substitutes, including admission during a deliberately blocked turn and a thin Telethon-envelope translation check. The real account's identity/update behavior and desktop-visible automatic continuation still need an explicitly approved live test. Proposed test: activate only the already selected folder/group, inspect its readiness message and durable cutoff, have the user post a new human-authored `#codex` in the approved existing linked topic, observe one continuation and source-specific report, then replay the same envelope locally to confirm no second turn. A connector must never post the human marker on the user's behalf to simulate eligibility.

## Current live check

The user has authorized these controlled integration tests without per-test approval prompts. A scoped listener using the existing account/folder/group has announced readiness at cutoff message 32, admitted no historical requests, and synchronized test-owned references. One genuine human-authored Telegram trigger is required to finish live update/identity/automatic-continuation acceptance. Do not manufacture it through the connector; use the actual Telegram client. Stop the controlled listener once that verification and duplicate-delivery check complete.

## Completed first live trigger

The [human-trigger live check](../.scratch/telegram-integration/monitoring-live-test.json) passed: source 35 followed readiness cutoff 32, ran once in the existing linked chat, interpreted its preserved context input, and delivered verified replies 36–37 in the source topic. Replaying the same event returned duplicate; dispatch remained idle. The controlled listener stopped after this verification. Ticket 08 is resolved; full queue, catch-up and uncertain-outcome recovery remain the subsequent tickets.
