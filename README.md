# Reassure or Guide — study chatbot

A small research application for the **Reassure/Guide × Persistent/Fresh memory** experiment. Participants see the same neutral **Chatbot** interface and keep one locked condition. Python serves the interface and API; storage can be local SQLite, temporary RAM, or Supabase PostgreSQL.

The redesign branch updates the participant/researcher experience and natural-language prompt instructions. It preserves model configuration, the four fixed conditions, questionnaire wording, message limits and visit types. Administrators now configure setting labels and targets; enrollment creates IDs on demand using randomized blocks by default, with reasoned manual exceptions. Read [the redesign release notes](docs/REDESIGN_RELEASE.md) before piloting or deploying. It does not resolve differences between earlier proposals and later study documents. Use the team's approved protocol for recruitment, visit dates, required chats and analysis decisions.

## Start here

| Reader | Guide |
|---|---|
| Team running the project | [Team guide](docs/TEAM_GUIDE.md): setup, practice, sessions, troubleshooting and handover |
| Participants | [Participant guide](docs/PARTICIPANT_GUIDE.md): sign in, chat, finish, retry and get help |
| Project lead / report writer | [Success criteria](docs/SUCCESS_CRITERIA.md): what counts as a successful project and what the measures support |
| Analyst | [Data guide](docs/DATA_GUIDE.md): exports, blind coding, missing records and analysis limits |
| Developer / reviewer | [Engineering review](docs/ENGINEERING_REVIEW.md): changes, checks and remaining limitations |

## Run locally

From this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python setup_local.py
python tools/preflight.py
python run.py
```

`setup_local.py` creates `.env` only if it does not exist. Keep an existing `.env`; never replace it with the example. By default, open [the researcher screen](http://127.0.0.1:8766/admin). Use the private `ADMIN_KEY` from your settings. The default port is 8766; use the address printed by the app if yours differs. The participant screen is `/`.

| Setting | What it does |
|---|---|
| `CHATBOT_MODE=setup` | Inspect the interface; no chatbot responses or API calls |
| `CHATBOT_MODE=demo` | Scripted responses for checking workflow; not suitable for evaluating chatbot quality |
| `CHATBOT_MODE=live` | OpenAI responses; requires private API credentials and the existing human-test review settings |
| `STORAGE_MODE=temporary` | Team preview in RAM; no saved memory, ratings or study enrollment |
| `STORAGE_MODE=persistent` | Saved chats, ratings and memory summaries |
| `DATABASE_BACKEND=sqlite` | Local files; useful for isolated practice |
| `DATABASE_BACKEND=supabase` | Server-side PostgreSQL; requires persistent storage and verified TLS |

The app loads `.env` without overriding environment variables already set by the host. **Changing a local file does not update Render's Environment settings.** Restart after configuration changes. Never upload `.env`, `private/`, database files or exports.

## Existing deployment and database instructions

Start with the current [commit, push and deploy checklist](docs/RELEASE_GUIDE.md). It covers the cleanup branch, merging into `v2`, local checks, private settings and hosted acceptance.

- [Supabase setup](SUPABASE_SETUP.md)
- [Render with Supabase](DEPLOY_RENDER_SUPABASE.md)
- [Temporary Render preview](DEPLOY_RENDER.md)

Use one running app per Supabase schema and one Gunicorn worker. Keep development/pilot records separate from study records. `/health` checks whether the server is alive; a successful researcher sign-in and data read are also needed to check database readiness.

## What memory means

Both conditions retain messages **within the current chat**. Persistent additionally receives validated notes from up to the last three eligible completed chats belonging to that participant and style. Fresh receives no earlier-chat notes. Both conditions' transcripts remain stored for research in persistent storage; “Fresh” does not mean deleting the data. First chats have no previous notes in either condition. Failed summaries are visible to researchers and can be retried; automatic retries before a new chat can add delay.

## Checks

```sh
python -m unittest discover -s tests -v
node --check app/static/app.js
```

The suite uses synthetic providers and disposable records. PostgreSQL integration tests require `HCI_TEST_POSTGRES_URL` pointing to a **disposable loopback database**, never the study database. See the [engineering review](docs/ENGINEERING_REVIEW.md) for browser checks and the latest verified results. No frontend build is required to run the app.

## Historical material

[STUDY_HOW_TO_USE.md](STUDY_HOW_TO_USE.md), [STUDY_CHANGES.md](STUDY_CHANGES.md), [HANDOVER.md](HANDOVER.md), and older files in `docs/` preserve project history. Old screenshots and instructions showing style names to participants describe earlier versions. Read the guides above for the current software workflow; keep the approved study materials authoritative for research decisions.

For the current branch, follow [the merge and deployment guide](docs/MERGE_AND_DEPLOY_REDESIGN.md). Configure **Allocation** before enrolling after a clean reset.
