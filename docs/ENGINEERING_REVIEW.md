# Engineering review — 11 November 2026

The cleanup starts from the latest fetched `origin/v2`, commit `f0d9247`, on the separate branch `codex/clean-study-workflow`. Changes are local for review; no commit, push or deployment was performed by this cleanup.

## Changes

| Issue | Improvement |
|---|---|
| A failed request could remove the typed message from the interface | Keep a recovery copy in the current tab's memory and retry with the original request ID. Failed rating submissions also retain the chosen answers, and failed starts retain the pre-chat slider value. Reconcile against saved messages before displaying a retry. No browser local-storage transcript is created. |
| Host errors could produce confusing JSON-parser messages | Friendly network/server notices, an initial reconnect screen and handled sign-out/refresh errors |
| Repeated clicks during a request could trigger extra actions | Busy-state guards for sign-in, enrollment, test-account changes, code replacement, start and ratings. Stop remains usable during a reply. Overlapping operations keep the busy state until both finish. |
| A slow/unavailable database could replace the entire page with an API error | Static interface files load independently of the database; the interface can show its connection error and retry control. Host checks remain in place. |
| There was no recovery for a lost access code | Researcher-only **Replace a lost access code** with typed confirmation. It replaces the code and revokes old sign-ins, retaining the existing assignment and records; no second enrollment is created. |
| Temporary RAM storage allowed study enrollment | Enrollment is blocked in temporary mode, with a clear researcher-screen explanation. Test accounts still support team previews. |
| Direct API calls could bypass the participant screen's pending-rating step | The backend also requires the pending post-chat questions before a locked participant starts another chat. Existing question wording/ranges are unchanged. |
| Resuming a chat could unnecessarily retry failed summaries | Check consent and an existing open chat first. New-chat summary retry policy remains the same. Corrected the misleading claim that synchronous retries never delay a participant. |
| Researcher lists and chat exports made a query for each account/chat | Grouped database queries gather counts once. A lookup map replaces repeated browser searches for account labels. |
| Mobile tables, inputs and rating scales were inconsistent | Contained table scrolling, flexible forms/composer, aligned seven-point controls, 16-pixel inputs, touch-sized buttons and checkbox labels, visible keyboard focus, safe-area notice positioning and reduced motion |
| Researcher usage limits appeared as a raw settings object | Readable labels and values inside the existing collapsed usage section |
| Branched scenario answers could be omitted | The blinding tool accepts separate matching answer columns and checks one non-empty answer per person. Ambiguity stops with an explanatory error. |
| A repeat blinding run silently replaced the coding key | Refuse to overwrite existing coding files; protect new derived CSV files with private file permissions. |
| Zero-chat participants disappeared from the combined table | Optional enrolled roster from the app's JSON/CSV; retain zero-chat and form-only IDs without inventing unknown conditions. |
| Open chats were counted as stopped | Separate open and stopped/discarded counts |
| Fractional coder scores were truncated, and kappa was reported as 1 with no variation | Validate integer 0–3 scores; report undefined kappa correctly; reject duplicate/unknown coding keys and label descriptive summaries accurately. |
| Main instructions mixed historical and current behaviours | New README, separate team/participant/data guides, measurable success criteria and historical-guide notices |
| Packaged downloads omitted the newer study instructions | Include the study guides and handover in the regenerated public archive and file manifest. Private settings and records remain excluded. |

The active `app/prompts.json`, model defaults, condition assignment logic, rating wording, minimum/maximum message settings and `first/home/final` visit types are preserved. No database migration or credential change is required for this cleanup. Existing deployment and certificate settings still apply.

## Verified locally

- **136 Python tests passed, none skipped**, with a disposable loopback PostgreSQL database and synthetic provider. Includes SQLite/RAM behaviour, PostgreSQL integration, actual Gunicorn start/restart, assignment/memory isolation, deletion, quotas, failed-request handling and the new data-preparation regressions.
- **75 browser checks passed: 25 each in Chromium, Firefox and WebKit**, with no JavaScript errors. These are engine/emulation checks on this Mac, not measurements from physical phones.
- Browser checks run using **Playwright 1.65.0** against an isolated demo fixture. It constructs its own settings, never loads `.env`, never connects to Supabase and never calls OpenAI.
- The browser suite checks login, consent, chat, ratings and expanded researcher pages at **320, 390, 768 and 1440 pixels**; checks horizontal overflow, input size, rating alignment and JavaScript errors; exercises all four test-account conditions.
- Additional browser checks cover failed rating submissions with retained answers, access-code replacement, an HTML host error before a message is saved, a lost response after saving, initial reconnection and Stop while a reply is delayed.
- JavaScript syntax checks and public-package integrity checks are part of the final verification. GitHub Actions now includes independent Chromium, Firefox and WebKit browser jobs; those remote jobs will run after a push and have not been executed from this local cleanup.

Synthetic demo previews: [phone](screenshots/chat-phone.png) and [desktop](screenshots/chat-desktop.png). Remaining limits are recorded below. No live hosted performance, actual Supabase state, billable API responses or participant outcomes are claimed by these local checks.

## Repeat the checks

From the project folder:

```sh
.venv/bin/python -m unittest discover -s tests -v
node --check app/static/app.js
```

Without `HCI_TEST_POSTGRES_URL`, the PostgreSQL integration tests skip. To exercise them, supply a disposable loopback PostgreSQL URL through your shell environment, never the study database URL. The fixture's explicit local-test connection option is restricted to loopback; production TLS verification remains enabled.

Browser tooling is optional and is not needed to run the app. Install it outside this project:

```sh
npm install --prefix /tmp/hci-browser-check playwright@1.65.0
/tmp/hci-browser-check/node_modules/.bin/playwright install chromium firefox webkit
NODE_PATH=/tmp/hci-browser-check/node_modules HCI_BROWSER=chromium node tools/browser_check.cjs
NODE_PATH=/tmp/hci-browser-check/node_modules HCI_BROWSER=firefox node tools/browser_check.cjs
NODE_PATH=/tmp/hci-browser-check/node_modules HCI_BROWSER=webkit node tools/browser_check.cjs
```

The default interpreter is `.venv/bin/python`. Set `HCI_TEST_PYTHON` if your test Python is elsewhere. Optional `HCI_UI_ARTIFACTS` writes screenshots of synthetic demo data to a chosen folder. Linux browser tooling may require Playwright's `install --with-deps` option.

## Still relevant before collection

1. **Hosted acceptance:** deploy during a quiet period and rehearse the actual API, verified TLS connection, schema permissions, restart persistence, two simultaneous devices, exports and consented human usability. Local tests do not establish that the previously reported pilot-schema issue is resolved.
2. **Study materials and approval:** record the applicable participant-procedure review and actual consent/privacy/support materials, including the OpenAI processing and the hosting/database services actually used. An environment flag or proposal feedback is not approval evidence.
3. **Scheduling:** the facilitator selects the existing first/home/final links; the app does not enforce visit dates or all stage ordering/repetition. Historical schedules and sample targets differ. This cleanup makes no decision between them; keep the approved record authoritative and document deviations.
4. **Memory failures:** automatic summary retries are synchronous and can involve up to three provider requests before a new chat. Provider delays can therefore be long. Inspect/retry failed summaries in the pilot and before planned sessions. Moving this to a background queue would need a separately reviewed implementation because note availability affects the memory manipulation.
5. **Hosting/capacity:** keep one Gunicorn worker and one owner per schema. The shared PostgreSQL connection serializes brief database operations; this is appropriate to test for the expected study load, not a claim of unlimited scalability. Free-host sleep and account quotas require a hosted rehearsal. Technical caps/outages can constrain voluntary use and must be documented when interpreting reliance.
6. **Analysis:** the helper creates tables and descriptive summaries; it is not the full approved statistical analysis or external questionnaire scoring. Raw CSV free text should be imported as text in spreadsheet software. Missing scenario answers need review rather than an invented score.
7. **Support limits:** existing keyword/model safety handling is not a comprehensive distress detector. Use the approved support procedure and verified contact settings. Stopping a chat retains stored records; withdrawal/deletion is separate and must also cover forms and downloaded copies.
8. **Device evidence:** browser engines and mobile emulation are useful checks, not a test of every physical device, assistive technology or mobile keyboard. Include real phones in the human rehearsal.

## Project definition of done

Use [SUCCESS_CRITERIA.md](SUCCESS_CRITERIA.md). Software reliability, usable and traceable data, faithful implementation, privacy/consent arrangements and an honest report define success. Statistical significance is not an acceptance criterion.
