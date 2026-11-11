# Study experience redesign

Branch: `codex/study-experience-redesign`, based on v2 commit `3e59ea6`.

## Delivered experience

Participants have Home, Conversations, Study activities, and Help & privacy navigation. Home identifies the account and next app action. Conversations have neutral session numbers, dates, visit labels, optional participant-written titles, and open/closed state. Completed transcripts can be read without reopening them or supplying them to the model. Browser back/forward and direct conversation URLs work after authentication.

Pause and leave navigates away without closing the open conversation. Returning resumes the saved messages. This does not create a new database status or preserve unsent drafts. A warning precedes navigation with a draft. End early preserves the existing terminal Stop behavior. Finish retains the existing minimum messages and post-chat questions. Rating sliders no longer silently submit 50: participants deliberately move a slider or enter a number, including 50.

Participant correction is available identically in all four conditions. It appends a separately flagged correction without counting toward the minimum messages or making a provider request. If the session received prior notes, all those source notes are excluded from future recall; original source transcripts remain. Initial reference IDs remain recorded for audit, and reply events identify notes actually supplied. A correction can therefore reduce the effective memory exposure and must be considered in fidelity reporting. It does not erase earlier model inputs or provider processing.

Researchers have Overview, Participants, Sessions, Data quality, Exports & withdrawal, and Settings & testing. Participant search and detail timelines expose saved progress; session lists include visit/date/rating status; inspection renders readable note fields with original transcripts available. The data-quality page flags missing in-app post-chat answers, pending/failed summaries, and unfinished sessions. These are record checks, not clinical monitoring or verification of external forms.

Settings accept shared schedule instructions and baseline/final questionnaire HTTPS links. Blank defaults do not invent a schedule or claim forms are complete. Do not put private booking records or secrets in these participant-visible settings.

## Connection to the proposal

The study remains Reassure/Guide × Persistent/Fresh with fixed assignments, the existing first/home/final visit types, the same rating wording/ranges, current message limits, existing model settings, and the four-field summary format. Fresh participants can reread their own saved transcripts, but the model receives no earlier notes. The archive policy is identical across arms. Opening an archive is logged and does not itself trigger a model request.

The active prompt version is `study-v6-natural-continuity-2026-11-11`. It relaxes rigid phrase/question quotas, allows necessary explanations beyond the usual short reply budget, preserves attribution and correction rules, permits appropriate human support, and adds truthful capability explanations. Examples with unsupported implications were revised. Comfort remains different from eliciting the user's own reflection. New conversations snapshot the new prompt; existing conversations retain their previous snapshot. The fixed provider safety response and keyword pause mechanism were not replaced by an unvalidated classifier.

## Pilot before using with participants

This is a new intervention version. Transcript access, correction, rating presentation, and prompt changes can influence outcomes. Do not mix versions within an active cohort without recording the deviation and reviewing its implications. Rehearse all four conditions with fictional mild topics and an appropriately reviewed human pilot. A working provider request is not proof of style separation or semantic safety.

Check perceived warmth, comfort/reflection distinction, repetition, user agency, relevance, uncertain claims, and memory accuracy using independent ratings. Include greetings, good news, vague concerns, requests for comfort, short answers, corrections, requests for an answer, and long conversations. A persistent first chat correctly has no earlier notes. A fresh chat must never receive old notes, including after reading its archive.

Test real phones, a shared-device sign-out, two simultaneous users, actual hosted persistence, and external-form reconciliation. Exercise a deliberately selected midpoint rating, a failed rating submission, pause/reload/resume, terminal end, renamed archive, wrong detail, old access-code revocation, and researcher inspection. No real participant records or API credentials are used by the automated browser fixture.

## Compatibility and release

No database migration is needed: titles and archive/correction audit use the existing events table; shared materials use existing settings. Keep private configuration and database records. Deployment is still the existing Python/Gunicorn app on Render with Supabase or local SQLite; this branch does not create a new repository or hosting service. No billable API calls were made while implementing it.

Use the existing release checklist, but substitute this branch and its final checked commit. Merge and deploy only after the pilot and hosted acceptance. Neither push nor deployment is part of the local implementation.

## Remaining boundaries

- The study schedule and first/final order remain facilitator-controlled; the app does not impose the alternative two-week design proposed in the exploratory review.
- External questionnaires, unaided-task scoring, actual recruitment, delayed assessments, and debrief remain part of the existing study procedure. The UI does not certify their completion.
- The existing administrator secret remains supported. Optional named admin/facilitator accounts are configured privately through `RESEARCHER_ACCOUNTS_JSON`. Facilitator permissions are enforced by the server: neutral progress, enrollment, and code recovery only; no transcript inspection, raw export, settings, condition fields, or lab handoff. Removing an account or rotating its key invalidates its existing sessions. Researcher POST action attempts are audited without submitted text or secrets. Administrators still have condition-bearing access, and enrollment/recovery operators can see issued participant codes: these roles do not guarantee complete experimental blinding. Blind coders should remain outside the researcher account.
- The quality queue is computed from current records; it is not an incident-management service, automatic support monitoring, or background summary worker.
- Summaries remain source-conversation-linked four-field notes. They are not upgraded to a new per-claim schema, and automated shape validation does not prove truth.
- Unsent drafts and failed-submission recovery copies remain in tab memory; no sensitive browser local storage or undisclosed server draft is introduced.
- No therapeutic efficacy, dependence diagnosis, long-term resilience, or live-prompt validation is established by software tests.

The broader experiment and optional features in the design review remain research proposals. This implementation deliberately keeps the current proposal's operating structure while making it understandable and usable.

## Recorded verification

- 151 Python tests ran: 135 passed, 16 PostgreSQL integration tests skipped because `HCI_TEST_POSTGRES_URL` was not configured. Local Gunicorn start/restart checks passed using disposable records.
- 201 browser checks passed: 67 each in Chromium, Firefox, and WebKit at widths 320, 390, 768, and 1440. Checks include the participant navigation, pause/reload/resume, completed archive/title, all six researcher destinations, rating recovery, access-code replacement, request recovery, ending during a delayed reply, and server-enforced facilitator restrictions. No JavaScript errors were observed.
- JavaScript syntax and whitespace checks passed.
- Local demo screens were visually reviewed. Preview images use only synthetic fixture data: [phone home](screenshots/redesign/participant-home-phone.png), [desktop chat](screenshots/redesign/participant-chat-desktop.png), and [researcher overview](screenshots/redesign/researcher-overview-desktop.png).
- No Supabase deployment, real participant session, physical-device usability test, or billable live-model evaluation was performed.

## Configurable enrollment and reset follow-up

Admins now configure labels and enrollment caps for all four existing conditions in **Allocation**. No pre-created participant list is needed by the enrollment API/UI. Random assignment uses a privately stored shuffled variable block (one or two rounds of eligible settings); the future queue is never returned to a browser. Manual assignment is administrator-only and requires a reason. Plan versions and assignment methods are audited. Existing conditions stay locked. Targets count issued assignments, not just surviving/completing accounts. Unequal caps are not probability weights. Legacy list-import helpers remain for compatibility, but the new web enrollment does not consume their unused rows.

The allocation page provides common-scale participant bars, target/historical counts, and a filterable study-ID roster. Only administrator responses include group membership or the allocation plan. Automated checks exercise plan edits, manual assignment, membership filtering, caps, concurrency, and permission boundaries. Preview images contain only synthetic accounts.

The user explicitly confirmed clearing the configured `hci_live` schema and all three local databases. The reset removed accounts, conversations, messages, summaries, ratings, assignments, logins, usage attempts, and app-level settings. Credentials and schema/mode/model compatibility metadata were retained. Recovery backups were saved under ignored `private/`; a separate count-only check confirmed empty record tables afterward. Other Supabase schemas, external forms, and downloaded copies were outside the named reset targets.

See [the step-by-step merge and deployment guide](MERGE_AND_DEPLOY_REDESIGN.md). The code remains local until committed, reviewed, merged and deployed. The database reset is already complete; do not repeat it while deploying.
