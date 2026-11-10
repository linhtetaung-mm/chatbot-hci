# Team guide

This is the operating guide for the current software. It does not change the approved study protocol. The current code distinguishes `first`, `home` and `final` chats; the team follows its approved schedule and questionnaires outside the app. Earlier project documents contain different schedules and sample targets. Do not infer a new decision from this engineering update.

## 1. Know who does what

The following is a practical allocation of work, not a new experimental procedure. Combine tasks if needed; keep coders blind to conditions.

| Member | Responsibility | Handover evidence |
|---|---|---|
| Member 1 | Coordination, approved materials, bookings and issue log | Current protocol/material versions; session checklist |
| Member 2 | App, hosting, private settings and database operation | Working version; settings checklist without secrets; recovery contact |
| Member 3 | Session facilitation and participant support | Session completion log; deviations and follow-up through the approved procedure |
| Member 4 | Data reconciliation, private exports and analysis preparation | Checked IDs, missing-data table, securely stored original exports |
| Member 5 | Blind-coding coordination and report assembly | Coding rubric/materials, independent scores, reconciled results and report |

Any person who has seen condition-bearing records should not act as a blind coder for those records. The coordinator arranges the two independent coders required by the existing plan without exposing the allocation key.

## 2. Prepare the software

1. Open the project folder and follow [README](../README.md) to install and run it. Existing users keep their current `.env` and database.
2. Run `python tools/preflight.py`. It checks configuration without contacting OpenAI. It does not prove database/API access or approval.
3. For Supabase, follow [SUPABASE_SETUP](../SUPABASE_SETUP.md). Use the Session pooler, the correct schema and verified certificate settings. Do not disable TLS verification to fix a connection error.
4. Use a development/pilot schema for practice. Stop other apps and administrative command-line tools that use that same schema. The app deliberately permits only one owner per schema.
5. Set actual contact details, the deletion date and the existing review settings according to the approved materials. These are private configuration entries; do not invent approval by changing a flag.
6. For a hosted copy, enter values in the hosting service's Environment settings and upload the certificate using its secret-file mechanism. Mac certificate paths do not exist on the host. Redeploy/restart when nobody is chatting.
7. Open `/admin`, sign in and check the displayed mode, storage, backend and model. Persistent storage is required for study records. `/health` alone cannot confirm that the database works.

Never share the researcher secret with participants or distribute the OpenAI key to each tester. Participants need only their own access code and link.

## 3. Rehearse the complete flow

Use test accounts in the pilot environment, with fictional mild topics.

1. In **Test accounts**, create one account for each of the four style/memory combinations. Record these as tests, not study participants.
2. Use a separate private browser window to sign in with a test code. Give the researcher and tester separate windows so signing out does not unexpectedly replace the researcher session.
3. Practice `/?visit=first`, `/` and `/?visit=final`, following the existing session instructions. Complete the pre-chat slider, message requirement and three post-chat ratings.
4. Complete more than one finished conversation. Inspect summaries and the next chat's frozen memory references. Fresh must have no references; Persistent can use eligible ready notes from that account only. No previous notes are expected on the first chat.
5. Check response style against the team's existing prompt-validation cases. A working request does not establish that the AI behaves correctly. Do not change prompts during collection.
6. Check a failed request, **Try again**, **Stop**, sign-out and a return visit. Confirm one retry does not duplicate the saved exchange. Do not deliberately enter crisis content in a participant account; use the existing synthetic safety-test procedure and test accounts.
7. Try two devices at once, including a real phone. Confirm each sees its own messages and neither sees the assignment.
8. Download synthetic records, run the [data workflow](DATA_GUIDE.md), and reconcile accounts, chats and ratings before using real records.
9. Record device/browser, version, date, pass/fail and any issue. A human pilot still needs the applicable consent/review process.

## 4. Run a participant session

Use this checklist alongside the approved facilitator script and information sheet. The app does not replace either.

**Before the session**

1. Check the deployed version, persistent storage, database access, API availability and remaining request allowance. Avoid deploying while participants are chatting.
2. Open the approved forms and correct session link. The coordinator supplies the approved dates and reminders policy; this guide does not set them.
3. Check the participant information, consent, privacy, support and withdrawal materials are available and have the required review. The last status established in this conversation was proposal feedback, not participant-procedure approval; record any later approval separately.

**First session**

1. Follow the approved consent and baseline procedure. Once consent permits enrollment, press **Enroll next participant** once. Keep the ID available for the baseline form before its submission.
2. Save the displayed study ID, access code and final-scenario letter in the restricted booking record. The access code is displayed only once. Do not put codes in a public spreadsheet or screenshot.
3. Give the participant their code and `https://YOUR-APP/?visit=first`. Give the plain `https://YOUR-APP/` link for use between sessions. Do not give them `/admin`.
4. Ask them to read the on-screen consent statements, choose their pre-chat rating, chat, press **Finish chat**, and submit all three questions. The current first/final minimum is six answered participant messages; home chats require one. Stop remains available at any time.
5. Confirm completion in the researcher table without discussing the condition. Record technical interruptions separately from study outcomes. Do not create another enrollment to solve a login problem.

**Between sessions**

Use the approved contact, monitoring and usage instructions. The chatbot is not monitored live. Researchers can inspect saved transcripts and summary status, but should limit access to what their responsibilities require. Failed memory summaries can be retried through **Inspect → Retry summary**; check them before the next planned session. Automatic retries before a new chat can take time.

**Final session**

1. Give `https://YOUR-APP/?visit=final` and the existing access code. Complete the chat and all three ratings.
2. Follow the approved final form, assigned scenario, no-AI task, next-step choice and debrief sequence. The app does not deliver or score those external tasks.
3. Keep the chatbot closed during a task that must be completed without AI. Record session and form completion in the private log.

Dates and first/final visit order are facilitator-controlled: changing the URL changes the chat type. The app does not automatically enforce the visit calendar or prevent every repeated final visit. Use the approved booking record and flag deviations; do not silently change or delete records to make them fit.

## 5. Finish and preserve the data

1. Download the chat CSV and all-records JSON to restricted storage. Download the form CSVs separately. Use dated folders and retain untouched originals.
2. Follow [DATA_GUIDE](DATA_GUIDE.md) to retain zero-chat participants, check missing ratings/forms and prepare blind-coding files. The JSON is an export, not an automated database restore.
3. Withdrawal: use **Data downloads and deletion**, select the correct person, verify their ID privately and type the displayed confirmation. Deletion is irreversible. Also remove the corresponding external forms, booking entries and copies/exports according to the approved withdrawal rules. The app cannot delete those services for you.
4. Keep contact details separate from transcripts. Fresh transcripts are still research data and require the same privacy handling as Persistent transcripts.
5. Carry out the approved retention/deletion plan across the database, forms, exports and backups. Do not upload them to GitHub.

## 6. Common problems

| What you see | What to do |
|---|---|
| Invalid/lost code | Check the original code first. If lost, verify the person privately, use **Replace a lost access code**, type `REPLACE CODE`, and save the new code. Old codes and sessions stop working; the condition and saved records stay intact. Do not enroll again. |
| API not connected / setup | The operator checks host settings and restarts. Local `.env` edits do not update Render. |
| Temporary storage | Use test accounts only. Switch to the already planned persistent configuration before enrollment. |
| Network error / no reply | Keep the page open; check the connection, then use **Try again** for the same message. The retry identifier prevents a duplicate saved exchange. Unsaved recovery text is held only in that tab and can be lost if it is closed/reloaded. |
| Server is unavailable | Wait briefly and retry. If it persists, the operator checks host logs and configuration without sharing secrets. |
| Finish is unavailable | Wait for the current reply, resolve an unanswered message, or reach the displayed minimum. Stop remains available. |
| Three questions remain | Submit the pending ratings before the next chat. Do not invent responses for someone who withdraws. |
| Paused account | Follow the approved support/escalation procedure. Do not re-enroll or reset the person to bypass the pause. |
| AI request limit | Check pause state, remaining allowances and provider billing privately. An app attempt limit is not an exact currency cap; retries and summaries also consume attempts. |
| Database ownership error | Stop the other app/tool using that schema. Do not remove the lock or add Gunicorn workers. |
| Free-host startup delay | Open and check the hosted app before sessions. A database can persist while the web service sleeps. |

## 7. Hand over to another teammate

Provide the code version, app link, operator guide, approved material versions, non-secret configuration checklist, issue log and status of the last tested pilot. Transfer secrets through the team's approved private channel. Confirm who can access the host, database, forms and API project. Never claim the real hosted app passed checks merely because local automated tests passed.
