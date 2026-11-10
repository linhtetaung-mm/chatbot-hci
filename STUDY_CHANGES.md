# Study version: what changed

> Historical record. For the current software, use the [team guide](docs/TEAM_GUIDE.md), [participant guide](docs/PARTICIPANT_GUIDE.md) and [engineering review with verified results](docs/ENGINEERING_REVIEW.md). Approved study materials remain authoritative for protocol decisions.

Branch `study-version`, changes made on 10 November 2026, compared with the previous version (`master`, commit `43a8399`).

**Why:** the previous app was a team prototype with two named chatbots. The study needs a 2×2 between-participant experiment: each participant gets one fixed condition (support style Reassure/Guide × memory Persistent/Fresh), sees the same neutral chatbot as everyone else, chats as often as they like for a few days between two guided sessions, and rates every chat.

All 118 automated tests pass locally (one PostgreSQL test needs the `psycopg` driver installed; the 17 real-PostgreSQL tests run in GitHub Actions). A full participant flow was also run end to end in demo mode (enroll, consent, first chat, home chats, final chat, ratings, CSV export).

## 1. Neutral chatbot for everyone

| Before | Now |
|---|---|
| Page title and header "Reassure or Guide" | "Study Chatbot" |
| Chat heading "Reassure" or "Guide", a subtitle explaining the style, and a different colour for each | Heading "Chatbot", no subtitle, one colour for all conditions |
| Each bot message labelled with the style name | Labelled "Chatbot" |
| Prompt said "The style's name is visible in the interface" and began "You are Reassure" / "You are Guide" | Prompt says not to name or describe the style; styles are described as "comfort and reassurance" and "guided reflection" |

Files: `app/static/index.html`, `app/static/app.js`, `app/static/style.css`, `app/prompts.json`, `app/chatbot.py` (`state()` no longer sends the style to participants).

## 2. Fixed, concealed 2×2 assignment

- New `assignments` table holds a pre-randomized list of study IDs (P01, P02, ...). Every block of 4 IDs contains each of the 4 conditions once, in random order. Final-form scenario A/B alternates within each condition.
- New tool `tools/assignments.py`: `generate` (writes a private CSV, never overwrites), `load` (puts it in the database), `status` (IDs used/left).
- New researcher button **Enroll the next participant**: takes the next unused ID in list order, creates the participant with that condition **locked**, and shows the study ID, a short access code, the scenario letter and the three links. The condition itself is not shown on screen.
- Locked participants cannot be switched to another style or memory condition, and their memory cannot be reset. The old "assign"/"handoff"/"reset" tools now only work for **test accounts**.
- Test accounts (for the team and the pilot) are created separately with a chosen style and memory, and are marked as test accounts in the data.

Files: `app/storage.py`, `app/migrations/002_study.sql`, `app/chatbot.py` (`load_assignments`, `enroll`, `assign`, `handoff`, `reset`), `app/server.py`, `app/static/app.js`, `tools/assignments.py`.

## 3. Memory condition (IV2)

- Each participant has `memory = persistent` or `fresh`.
- **Persistent:** as before, the notes from the last three finished chats are given to the model.
- **Fresh:** the model never receives earlier notes. Notes are still written after every chat for all participants, so data handling is equal.
- The note IDs actually used for each chat are still saved (`memory_refs`) and now appear as `notes_used` in the CSV export.

Files: `app/chatbot.py` (`start()`).

## 4. Chat types and in-app ratings

- Every chat is tagged `first`, `home` or `final`. The type comes from the link: `/?visit=first`, `/` (home, any time) or `/?visit=final`.
- **Before each chat:** "How upset do you feel about it right now?" (0–100 slider). Required for study participants.
- **After Finish:** "How upset do you feel about the situation now?" (0–100), "The chatbot gave me the kind of support I needed." (1–7), "I felt understood by the chatbot." (1–7). Saved once per chat.
- **Minimum length:** the first and final guided chats need at least 6 participant messages before Finish (setting `MIN_GUIDED_MESSAGES`). Home chats have no minimum. Stop is always allowed.
- No fixed days or "see you on Day X" messages: participants can come back any time.

Files: new `chat_meta` table (`app/storage.py`, `app/migrations/002_study.sql`), `app/chatbot.py` (`start`, `finish`, `rate`, `state`), `app/server.py`, `app/static/app.js`.

## 5. Simpler participant screen

Removed for participants: list of previous chats, "Correct a remembered detail" form (it only appeared for people with memory, so it revealed the condition), Discard, New chat inside a chat, and the "earlier prompts" note. Participants now see only: consent → how upset (slider) → chat with **Send**, **Finish chat** and **Stop** → three questions → thank-you. Support contacts are shown on every screen.

## 6. Home chats are never blocked by a failed memory note

Before: if any of the last three summaries had failed, a new chat could not start until a researcher retried it. Now the app retries failed notes automatically before a new chat; if one still fails, the chat starts with the notes that are ready and the event `memory_not_ready_skipped` is logged.

Files: `app/chatbot.py` (`retry_pending_summaries`, `start`).

## 7. Safety message works without a researcher present

The exact safety reply now reads: "I'm glad you told me. This sounds beyond what this chatbot can support. Please contact the Thailand Mental Health Hotline 1323 (24 hours) or AIT student counselling now, and let the research team know." The keyword stop and account pause work as before. Set the real AIT counselling contact in `SUPPORT_CONTACTS`.

Files: `app/prompts.json`, `app/provider.py`, `.env.example`.

## 8. Sign-in on a phone

- Access codes are now 8 characters like `K7MP-Q2XA` (no 0/O or 1/I/L). Upper/lower case, spaces and the dash are ignored when typing.
- A sign-in lasts 7 days (`SESSION_HOURS=168`), so participants do not have to retype the code during the week.
- Old long codes still work.

Files: `app/chatbot.py` (`new_code`, `login`, `token`), `app/server.py`, `app/config.py`.

## 9. Usage limits raised for the study

| Setting | Before | Now |
|---|---|---|
| `GLOBAL_TOTAL_API_LIMIT` | 500 | 3000 |
| `GLOBAL_DAILY_API_LIMIT` | 250 | 800 |
| `TESTER_DAILY_API_LIMIT` | 50 | 80 |
| `TESTER_MINUTE_API_LIMIT` | 3 | 6 |
| `TESTER_DAILY_CHAT_LIMIT` | 4 | 6 |

Still set a monthly spending limit in the OpenAI dashboard. Files: `app/config.py`, `app/limits.py`, `.env.example`, `render.supabase.yaml`.

## 10. Data export for analysis

New researcher download **One row per chat (CSV)** (`/api/admin/export_chats`): study_id, test_account, style, memory, chat_type, status, start/end time, minutes, user_messages, notes_used, pre/post distress, distress_change, support_needed, felt_understood, safety_stop, prompt_version, model. The full JSON export now also includes `chat_meta` and `assignments`. Both contain conditions: never give them to the blind coders.

## 11. Database changes (schema version 2)

- SQLite (local): upgraded automatically when the app starts; existing records are kept.
- Supabase/PostgreSQL: new schemas are created at version 2 by `python3 tools/database.py init`. An existing version-1 schema must be upgraded once with `python3 tools/database.py migrate` (keeps all records); the app refuses to start on an old schema and says so.
- `server_role_optional.sql` now includes policies for the two new tables.

## Tests

- New `tests/test_study.py` (9 tests): list-order enrollment and locking, Fresh gets no notes while Persistent does, required/validated ratings, guided-chat minimum, neutral participant view, forgiving short codes, CSV export, in-place SQLite upgrade, balanced assignment blocks.
- Updated 5 existing tests that expected the old behaviour (style name on screen in two tests, blocked chats after a failed summary, prompt wording, 8 → 10 PostgreSQL tables).

## Not changed / still to do

- Prompts were not re-tested with the live model after these wording changes. Run the prompt check (both styles, several runs) and freeze the prompts before the pilot.
- The candidate v4 prompts in `experiment-readiness-2026-11-09/` are still not active.
- The PostgreSQL changes could not be run here (no database driver offline); they are covered by the GitHub Actions tests and by `tools/database.py self-test`. Run both before deploying.
- Supabase + Render deployment, Google Forms (baseline/final), consent approval and the pilot are separate tasks.

---

# Update, 10 November 2026 (evening): less repetitive chatbot and analysis tool

## 12. Prompts version 5 (`study-v5-variety-2026-11-10`)

**Why:** in testing, replies felt scripted: every reply acknowledged a feeling, then commented, then asked a question, at the same length each time, and sentences from the built-in examples came back word for word.

| Before | Now |
|---|---|
| "Normally offer one specific follow-up" in every reply | A question in at most about half of the replies; never questions in three replies in a row; an observation or gentle invitation also keeps the chat going |
| 2–4 sentences, under 80 words | Match the user's length: 1–2 sentences for a short message, never more than 3 sentences or about 60 words (shorter replies also arrive faster) |
| No rule against repetition | New VARIETY rule: no two replies opening the same way, no reused sentence or question in a chat, acknowledge a feeling only when it is new or important, never copy the example wording |
| Reassure: one fixed pattern (acknowledge, comfort, ask) | Rotates between kinds of comfort: validate, normalise, acknowledge described effort, warmth and presence, one small comfort to do now, gentle encouragement |
| Guide: a short checklist (other explanation, evidence, control, next step) | Rotates between reflective moves: reflect their words, notice something, another possible explanation, what they would tell a friend, what helped before, what is in their control, one small next step; after two questions in a row, a short summary without a question |
| 6 examples per style on bad day / exam / friend not replying, with the same openings in both styles | 3 examples per style on roommate noise, a group project, homesickness; each style opens differently; some replies have no question |
| A Guide example practised "what else might explain the delay?" for a friend not replying, almost the same as final Scenario A | Removed, so the chatbot does not rehearse the test scenarios (Scenario A: friend not replying; Scenario B: supervisor feedback) |
| One fixed greeting every chat | One of four greetings picked at random; the same set for every condition, and none mentions earlier chats |

Unchanged: what makes the styles different (Reassure never asks the user to rethink and never agrees that the other person was wrong; Guide never supplies the answer), memory rules, safety reply. Replies over 60 words are now flagged `over_60_words` in the records.

**Before the pilot:** repeat the prompt check with the four test accounts (2–3 chats each), then freeze this version.

Files: `app/prompts.json`, `app/chatbot.py`.

## 13. Analysis tool `tools/combine_data.py`

Combines the chatbot download with the two Google Forms into two tables that open in Excel:

- `blind`: makes the coders' file from the Final form (random code, scenario letter, answer; no study ID or condition) and a private key file.
- `combine`: produces `chat_level.csv` (one row per finished chat, for H1) and `person_level.csv` (one row per participant: averages of the after-chat ratings, number of home chats, all Baseline and Final answers, and the agreed scenario score, for H2–H6). It prints Cohen's kappa for the coders, study IDs that are missing or mistyped in the forms, and averages per condition. Study IDs typed as `p7` or `P 07` are read as `P07`.

## Tests

120 tests; new ones check the greeting set and the ID matching in the analysis tool.

## 14. "Typing…" bubble (10 November, late)

The participant's message now appears the moment they press Send, with an animated "typing" bubble from the chatbot until the reply arrives. The message box, Send and Finish are disabled while waiting; Stop still works. After each message the page makes one request instead of two. Server code is unchanged. Files: `app/static/app.js`, `app/static/style.css`.

## 15. Adding more study IDs later (11 November)

- **Fixed:** loading a second assignment list used to add nothing (its order numbers clashed with the first list). New IDs are now queued after all existing IDs.
- **New researcher button** "Add study IDs" (in "Enroll the next participant"): adds 4, 8 or 12 IDs in freshly shuffled blocks of 4, numbered after the last one (P49, P50, ...). Works while the app is live on Render; no laptop tool needed.
- `tools/assignments.py generate` has `--start` to continue the numbering (e.g. `--start 49`).
- Checked: deleting a participant removes their account, chats, messages, notes, ratings and logins; their access code stops working; their study ID stays used and is never given out again.

## 16. Several people at once, and the "Another chatbot process" error (11 November)

- **Why the error happens:** only one copy of the app may use a Supabase area (`DATABASE_SCHEMA`) at a time; it holds a database lock. The error appears when a second copy starts on the same area: the app or a `tools/` command on a laptop while Render uses it, or Render's new copy during a deploy while the old copy is still running.
- **Deploys no longer fail on this:** `/health` answers without the database, the app connects on the first request, and on Render (`DEPLOYMENT=render`) a new copy waits up to 90 s (`DATABASE_LOCK_WAIT`) for the old copy to release the lock. The lock is released explicitly when a copy stops. On a laptop the error still appears at once, which is intended.
- **More people at once:** 16 request threads (was 8) and up to 12 AI replies at the same moment (`GLOBAL_CONCURRENT_API_LIMIT`, was 5). Each participant can still have only one reply in progress.

Files: `app/postgres.py`, `app/server.py`, `app/config.py`, `app/limits.py`, `gunicorn.conf.py`, `render.supabase.yaml`, `.env.example`.
