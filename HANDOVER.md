# Handover: Reassure or Guide study chatbot

> Historical handover. The deployment-lock/concurrency changes described as uncommitted below were committed in `f0d9247` and are included in this cleanup. Use [the current team guide](docs/TEAM_GUIDE.md) and [engineering review](docs/ENGINEERING_REVIEW.md) for software operation and verified status. Historical host/database observations below have not been re-verified by this cleanup; this note does not change the study protocol.

Written 10–11 November 2026 by Barnnita (with Claude) for the team member who continues. Read this first, then the team guide (Claude Doc "Reassure or Guide: Project Guide for the Team"), then `STUDY_HOW_TO_USE.md`. Submission: **19 November 2026**.

## 1. The study in five lines

- 2 × 2 between-subjects: support style (**Reassure** = comfort, **Guide** = equally warm questions so people find their own view) × memory (**Persistent** = uses notes from the last 3 chats, **Fresh** = no memory). Each participant gets one fixed version; everyone sees the same neutral "Chatbot".
- Each participant: **first session** (consent, Baseline form, first chat) → **free use at home about 4 days** (no fixed days, no reminders) → **final session** (final chat, Final form with the no-AI scenario task, next-step choice, debrief).
- Every chat: slider "how upset" 0–100 before, chat, then slider again + 2 questions (1–7).
- Target 40 finishers (minimum 32). 48 study IDs (P01–P48) are prepared.
- Plan: first sessions 12–13 Nov, final sessions 16–17 Nov, analysis 18 Nov, submit 19 Nov.

## 2. Where everything is

| What | Where |
|---|---|
| Code | GitHub repo, branch **`v2`** (local folder `chatbot-hci`) |
| What changed in the code, section by section | `STUDY_CHANGES.md` (sections 1–16) |
| How to run sessions, enroll, download data | `STUDY_HOW_TO_USE.md` and section 4 of the team guide |
| Private files (NOT in Git) | `.env` (all secrets), `private/assignments.csv` (who gets which version: keep hidden), `private/assignments.csv.seed`, `private/prod-ca-2021*.crt` (Supabase certificate) |
| Database | Supabase project in **Singapore** (`ap-southeast-1`). Areas: `hci_dev` (laptop testing), `hci_pilot` (pilot on Render), `hci_live` (real study, 48 IDs loaded) |
| Website | Render web service, region Singapore, branch `v2`, Starter instance during the study |
| Old Supabase project (Mumbai, `ap-south-1`) | Test data only; delete after the study has started successfully |

Secrets (OpenAI key, Supabase database password, `ADMIN_KEY` for Render and for the laptop) are handed over privately, never in chat, GitHub or screenshots. `envcrypt.py` / `shared.env.enc` are a teammate's tool for sharing settings; check with them before committing either.

## 3. What has been done

| Done | Notes |
|---|---|
| Proposal v2 (Intro + Related Work) and the team guide | Proposal still says Reassure "agrees with the user's view" and fixed chat days: update wording to the final design before submission |
| Study version of the chatbot | Neutral look; locked random 2×2 assignment; Persistent/Fresh memory; in-app ratings; chat types (first/home/final via link); minimum 6 messages in guided chats; simple participant screen; safety stop with hotline 1323; short codes, 7-day login; one-row-per-chat CSV; schema version 2 |
| Database moved to Singapore | Reply wait went from 11.9 s to 1.9 s |
| Prompts version 5 (`study-v5-variety-2026-11-10`) | Less repetitive: fewer questions, shorter replies, rotating moves, 4 random greetings, examples no longer rehearse the final scenarios |
| "Typing…" bubble | Message shows instantly while the reply is written |
| Analysis tool `tools/combine_data.py` | `blind` makes the coders' file; `combine` gives `chat_level.csv` (H1) and `person_level.csv` (H2–H6), kappa and ID checks |
| Add study IDs button; fixed loading a second list | Commit `5079112` |
| Deletion checked | Removes account, chats, notes, ratings, logins; code stops working; ID never reused. Form answers and downloaded backups must be deleted by hand |
| Deployed on Render | Working on `hci_live` before switching to `hci_pilot` |
| Several people at once; deploy lock fix; clearer database errors | **Not committed yet** (see section 4) |
| Tests | 121 pass; 1 needs the `psycopg` driver (passes on a Mac with requirements installed); 17 PostgreSQL tests run only in GitHub Actions |

## 4. Not committed yet: commit and deploy first

These changes are in the local folder only: overlapping Render deploys no longer fail with "Another chatbot process…", 16 threads and 12 simultaneous AI replies, and database errors now show an error type and SQLSTATE code in Render's logs.

```sh
cd chatbot-hci && source .venv/bin/activate
python3 -m unittest discover -s tests        # everything should pass (some skipped)
git add app tests tools gunicorn.conf.py render.supabase.yaml .env.example STUDY_CHANGES.md STUDY_HOW_TO_USE.md HANDOVER.md
git commit -m "Overlapping deploys, more people at once, clearer database errors, handover notes"
git push origin v2
```

Then on Render: set `GLOBAL_CONCURRENT_API_LIMIT=12` (Environment) and **Manual Deploy → Deploy latest commit** when nobody is chatting.

## 5. Open problem right now

After switching Render to `DATABASE_SCHEMA=hci_pilot`, the site shows "Database operation failed…". Most likely `hci_pilot` was never created in the Singapore project, or was created by older code.

1. Supabase → SQL Editor: `select schema_name from information_schema.schemata where schema_name like 'hci_%';` and, if it exists, `select * from hci_pilot.settings;`
2. Missing → on a laptop (laptop app stopped, `.env` pointing to Singapore, `CHATBOT_MODE=live`): `python3 tools/database.py init --schema hci_pilot` then `check --schema hci_pilot`. Older version (`postgres_migration` = 1) → `python3 tools/database.py migrate --schema hci_pilot`. `mode` not `live` → use a fresh name such as `hci_pilot2`.
3. Render → **Manual Deploy → Restart service**, open `/admin`. After the section 4 deploy, Render **Logs** show the error code if it fails again (3F000 area missing, 42P01 table missing, 42703 column missing, 42501 no permission).

## 6. Remaining steps, in order, with what to check

1. **Fix section 5, commit and deploy section 4.** Check: `/health` shows `"ok": true`; `/admin` loads.
2. **Prompt check** (Render on `hci_pilot`, 4 test accounts, 2–3 chats each, include "just tell me what to think"). Check: Reassure comforts and never asks you to rethink or says the other person was wrong; Guide asks and reflects but never gives the answer; Persistent sometimes refers to earlier chats, Fresh never; replies 1–3 sentences, not repetitive. Then freeze the prompts.
3. **Safety test** with a test account: type "I want to die". Check: chat stops, hotline shown, account marked paused (safety) in `/admin`.
4. **Two people at once:** two phones chatting at the same time. Check: both get replies, no "busy" message.
5. **Study materials:** instructor approval (until then `HUMAN_TEST_REVIEW` must not be `confirmed` for real participants); consent sheet; debrief sheet; verified AIT counselling contact in `SUPPORT_CONTACTS`; Baseline and Final Google Forms (exact items in section 3 of the team guide; Study ID required with validation `^[Pp] ?\d{1,2}$`; scenario letter branches to A or B); private booking sheet; roles including safety checker + backup and two blind coders; coders practise the 0–3 rubric.
6. **Pilot** with 4 people who are not participants: whole flow in a few hours on Render (`?visit=first`, plain link twice, `?visit=final`, forms, debrief). Then download the chat CSV and both forms and run `tools/combine_data.py blind` and `combine`. Check: every pilot ID appears in `person_level.csv` with no CHECK warnings.
7. **Switch to the real study:** Render `DATABASE_SCHEMA=hci_live`, Save and deploy. Check: `/admin` shows 48 IDs left and no participants; delete any test accounts there.
8. **Recruit and run** first sessions 12–13 Nov, safety checks twice a day, JSON backup every evening, final sessions 16–17 Nov (team guide section 4).
9. **After the last session:** Render instance back to Free; downloads; blind coding; `combine`; analysis; writing; update proposal wording; delete data by 19 Dec.

## 7. Rules that prevent most problems

- One copy of the app per database area. Laptop = `hci_dev`; Render = `hci_pilot`, then `hci_live`. `tools/` commands count as a copy: on `hci_live`, use the researcher page (e.g. **Add study IDs**) instead.
- Never pick a study ID for someone, never enroll anyone twice, never reuse an ID, never change prompts once the pilot has started.
- Never give the chat CSV, JSON export or `private/assignments.csv` to the coders: they show the versions.
- Redeploys interrupt chats for about a minute: only when nobody is in a session.
