# Render preparation verification — 7 November 2026

- 72 automated tests passed using the project virtual environment, including the actual Gunicorn startup command, HTTP login, remote Guide assignment, consent, demo reply, completed-chat memory generation, process restart and persisted memory/counter checks. Demo and mocked providers only; no paid API calls made for this update.
- Tests cover exact HTTPS origin/host validation, Secure cookies, denied unauthorized access, global/per-tester quotas, retries and summaries, cross-style quotas, concurrent reservations, pause persistence, missing-disk startup rejection and daily new-chat caps.
- JavaScript syntax check, Python dependency check and Git whitespace check passed.
- Deployment configuration reviewed against Render documentation. The manifest and public ZIP were regenerated after this update.
- No existing `.env` or tester database was modified, no GitHub push was performed, and no Render service was created. Existing live API capability was not re-tested here. Actual Render mounting, health checks, HTTPS behavior, mobile UI and model availability still require the acceptance checks in `DEPLOY_RENDER.md`.
- Local mode remains available. Production is one Gunicorn process with eight threads and one Render instance. Setup mode is the Blueprint default; a paid persistent disk is required.
- Automated tests do not establish research approval, clinical safety or suitability of the full participant experiment. The earlier verification history follows.

---

# Verification record

Date: 3 November 2026. Phase 1 prototype version 1.0.

## Completed

- **43 automated tests passed**, with no inherited duplicate test classes. They exercise two-style and two-tester isolation, the last-three-note window, current context, persistence/restart recovery, idempotent send/finish, failed-message retry, summary failure/retry, consent, correction, reset, deletion, limits, consistent backup/restore, stateless payload construction and live-adapter refusal/incomplete-output handling with mocks.
- Race tests verify Stop, reset and deletion during outstanding generation cannot save late replies or revive excluded/deleted notes.
- Web-boundary tests verify unauthorized export rejection, role separation, cross-origin rejection, secure cookie attributes for the local-only route, handoff and a complete send/finish/summary sequence.
- JavaScript syntax and Python compilation checks passed.
- Browser walkthrough completed researcher login, anonymous tester creation, consent, Reassure conversation/finish/new-chat recall, researcher note inspection, Guide conversation/finish/new-chat recall, switching styles with separate histories, browser reload, application restart, and the wrong-memory correction form.
- During browser testing, an event-handler issue caused by rebuilding HTML was found and fixed. Chat controls and correction controls were rechecked after the fix.
- Demo screenshots contain only fictional test topics and no access codes. The working local demo database contains scripted verification records; it is excluded from the shareable ZIP.

## Scope and limits

No API key was configured, so no billable AI calls were made. All browser replies and memory excerpts were explicitly labelled scripted practice. The real API adapter was checked through tests/mocks and official documentation, not a live account call. Live style fidelity, real summary accuracy, latency, model availability in the team's account, actual spend, participant comfort and the supervised human usability test remain to be checked by the team.

This is a local-only prototype, not a deployed participant study or a clinical support system. A real key/contact/support configuration and applicable course review are required before live human testing. The app's checks do not certify ethical review, crisis detection or psychological effects.

The shareable package excludes private `.env`, databases, exports, backups, cache files and credentials. See README and HOW_TO_USE for setup and operation. The older study-kit project has not been modified or pushed by this task.

## Context and interface update — 3 November 2026

- **49 tests passed** after the update. Added checks for the vague bad-day demo regression, distinct styles/scenarios, explicit system/user/assistant roles, unchanged user content, system/user summarization, compatibility with old saved prompt snapshots and detection of older prompts.
- Replaced the single canned demo response with clearly labelled scenario examples. This is still a simulator, not a live prompt-quality test.
- Reworked system prompts for vague requests, practical concerns, interpersonal interpretations, greetings and good news. Added style examples. Live response quality remains unverified because no key is configured.
- Browser-tested the simplified researcher page, Reassure/Guide titles and visual accents, consent, sending the user's bad-day example in both styles, finishing and starting a new chat. The previews show simulated replies and no private credentials.
- Secondary chat actions and memory correction are under More; earlier chats and researcher records/tools are collapsed. Data and secrets were preserved. Browser testing used an isolated temporary database on port 8767 and did not interrupt the user's port-8766 server.
- Restart the user's server and start a New chat to use the revised prompts. Existing conversations retain their earlier prompt snapshots.

## API placeholder and completion audit — 3 November 2026

- Audited the existing files and ran the earlier 49-test suite before changes. Confirmed the real adapter already existed; repeated screenshot replies were the simulator fallback.
- **56 tests passed** after the update, also with ResourceWarnings treated as errors. New coverage includes setup/no-network/no-fake-record behaviour, rejecting placeholder keys, live HTTP response parsing, actionable HTTP errors, and a successful no-key diagnostic dry run. Mocked live-adapter tests use an explicitly fake test credential so they actually exercise response parsing rather than stopping at the missing-key guard.
- Browser check on an isolated temporary setup database verified researcher sign-in, named chatbot handoff, consent, the not-connected status and disabled composer/Finish controls. Preview: docs/preview-api-setup.png. No fake AI exchange or memory was created.
- Added the private/public API-key placeholder, setup as the default, clearer preflight output, six-request opt-in synthetic API check, and audit/activation/usability-record documents. Demo remains an explicit simulator option.
- Fixed explicit resource cleanup for SQLite backups and HTTP error responses. Kept the user's researcher secret, original records and active server untouched. Setup mode uses a separate database.
- No real API key was supplied, no real OpenAI request was made, and no human findings were created. **Phase 1 remains incomplete** until the unchecked gates in docs/PHASE1_AUDIT.md are satisfied. Technical tests do not substitute for response-quality evaluation or a human usability test.

## Conversation follow-through — 3 November 2026

- Updated prompts to `phase1-context-v3-follow-through`: focused next turns, simpler prompts for uncertain/short replies, continuity after an answer, and natural closure when the tester is done. Reassure continues through comfort and feelings; Guide scaffolds the tester’s own reflection without supplying the answer. Added contextual illustrations for both styles.
- Consulted the [official OpenAI prompt-engineering guide](https://developers.openai.com/api/docs/guides/prompt-engineering) for explicit instructions and examples. The existing role-based request construction, model settings, memory rules and stored conversation snapshots were preserved.
- **56 existing automated tests passed**, with ResourceWarnings treated as errors. These verify application behaviour and payload handling; they do not establish the model’s conversational quality. No real API calls were made for this update.
- Added a short live follow-through check to HOW_TO_USE.md. Restart the server and start a New chat to test the new instructions; earlier chats retain their original prompt snapshots.

## Progress reconciliation — 4 November 2026

- Reran the existing suite: **56 tests passed** with ResourceWarnings treated as errors. No application behaviour was changed in this documentation update.
- The project owner confirmed Live AI with an API key and testing of both styles. This is explicitly recorded as owner-reported live team testing, not a new observed provider call. The owner confirmed no outside supervised usability test has been completed.
- Updated the main task guide to Version 5 and synchronized readiness text with that confirmation. Corrected obsolete instructions about the active folder/port, Phase 1 memory and visible style labels; added detailed remaining checks, experiment procedure, five-member roles, reporting and November 19 schedule.
- The latest follow-through prompt and live summary accuracy still require recorded quality checks. The six-call diagnostic receipt and exact private live model/settings were not independently verified here. No API key or personal transcript was read or reproduced, no billable calls were made and no participant findings were created.
- The main guide is also included in docs/PROJECT_TASK_GUIDE.docx with an editable Markdown copy. The earlier Version 4 guide is archived outside the public package. No Git commit/push or old study-kit change was made.
- Document QA: the updated 23-page Word guide was rendered and every page visually inspected. Four changed pages were rechecked after spacing/table refinements; the other 19 rendered pages matched the inspected images byte for byte. Exact prompt blocks and the matching packaged Word copy were checked structurally.
