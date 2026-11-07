# Reassure and Guide — Phase 1 chatbot

Two distinct chatbot styles with separate persistent memory for each tester and style. This folder contains the local interface, SQLite storage, OpenAI Responses API adapter, prompts, tests and operating instructions. Local mode uses Python 3.10+ and the standard library. Render uses Gunicorn (included in requirements.txt).

**Current status — 4 November 2026:** the project owner confirms Live AI testing of both styles with an API key. Only team testing has taken place. Phase 1 still needs a recorded review of the latest prompts and live memory, followed by at least one external supervised usability test. See [the current task guide](docs/PROJECT_TASK_GUIDE.md) and [the audit](docs/PHASE1_AUDIT.md).

**Hosting update — 7 November 2026:** Render configuration, private access and persistent quotas are implemented and locally tested. See [deployment verification](VERIFICATION.md). A Render deployment and live hosted acceptance test remain to be done.

## Deploy for team testing on Render

Follow [DEPLOY_RENDER.md](DEPLOY_RENDER.md). The included `render.yaml` sets up a paid service with a persistent disk and private environment settings. Setup mode is the initial default; enable live mode after completing the documented checks. No API key or existing tester data is included in deployment files.

Hosting includes secure HTTPS cookies, exact host/origin checks, persistent API-attempt quotas, an admin pause/resume switch, and remote chatbot assignment. Each tester needs a private access code. Limits include memory summaries and failed attempts, across both styles. This is preparation for team testing, not completion of the four-condition experiment or approval for participant recruitment.

## Start without an API key

Open a terminal inside this folder:

```sh
python3 setup_local.py
python3 run.py
```

Run `setup_local.py` only the first time. It creates a private `.env` and random `ADMIN_KEY`; it refuses to overwrite existing settings. Open `.env` locally to copy the researcher secret. Visit **http://127.0.0.1:8766/admin**, sign in, create a tester, choose Reassure or Guide and open their screen.

The default is **setup mode**: the interface says OpenAI is not connected and disables sending. It does not fabricate replies or AI memories. Your private `.env` contains this explicit slot:

```ini
CHATBOT_MODE=setup
OPENAI_API_KEY=PASTE_YOUR_OPENAI_API_KEY_HERE
```

That text is a placeholder, not a working credential. The code rejects it in live mode and never sends it to OpenAI. No need to create an account, spend money or supply a key just to inspect the interface.

## Three modes

| Mode | Purpose | API calls and records |
|---|---|---|
| `setup` | Inspect the app while waiting for a key | No AI replies or summaries. Separate `data/chatbots-setup.sqlite3`. |
| `demo` | Explicitly exercise UI/storage with scripted examples | No API calls. Responses are simulated and can repeat; not suitable for evaluating support quality. Separate demo database. |
| `live` | Real AI replies and summaries | Requires actual API key and human-test settings. Separate live database. |

Leave `CHATBOT_DB` blank for automatic mode separation. Do not point a different mode/model at an existing database: preserve it and choose a new filename. The update does not erase older demo records.

## Connect real AI when you have a key

“ChatGPT API” here means the **OpenAI API**. Your ChatGPT subscription does not itself configure this application. Use the official API platform to create an API project, establish billing/budget and create a private key. See [official authentication guidance](https://developers.openai.com/api/reference/overview).

Edit only the private `.env` file:

```ini
CHATBOT_MODE=live
OPENAI_API_KEY=PASTE_YOUR_REAL_KEY_PRIVATELY_HERE
OPENAI_MODEL=gpt-6-luna
OPENAI_REASONING_EFFORT=none
RESEARCHER_CONTACT=your actual contact
SUPPORT_CONTACTS=verified local and campus support contacts
HUMAN_TEST_REVIEW=confirmed
```

Replace the key placeholder with the real value; do not send it in chat or put it in source code, screenshots, GitHub or terminal commands. Confirm the applicable course review before setting `HUMAN_TEST_REVIEW=confirmed`, and check the local deletion date. The key is read server-side only.

Use the same model for both styles. Confirm the selected model and settings are supported by your account before human testing; model availability is not guaranteed by this package. If another model lacks the reasoning setting, leave `OPENAI_REASONING_EFFORT` blank. There is no automatic model switch or canned fallback on API errors.

Restart the terminal server with Ctrl+C, then:

```sh
python3 tools/preflight.py
python3 tools/check_api.py
python3 tools/check_api.py --execute
python3 run.py
```

Preflight and the dry run make no network calls. **Only `--execute` makes six synthetic, potentially billable calls:** initial reply, structured summary and return-with-memory reply for each style. Results go to `private/api-check.json` for human review. A successful request is not proof of style fidelity, correct memories or Phase 1 completion.

Reload the browser after a restart. Start a **New chat** for updated prompt versions. Existing conversations preserve their earlier prompt snapshots and records.

## How the chatbots work

- **Reassure** is shown by name with a green accent: comfort and reassurance without a reappraisal exercise.
- **Guide** is shown by name with a blue accent: warm questions that help the tester form their own perspective or next step.
- Both lead the active conversation with a focused follow-up and simplify the next turn when the tester is unsure. Reassure stays with comfort; Guide helps the tester form their own perspective. They respect a goodbye or request to stop.
- Both use the same model/interface, but different system style blocks. `app/prompts.json` contains shared system rules, style rules/examples, memory instructions and a separate summarizer prompt.
- Requests explicitly preserve system, user and assistant roles. The latest message is passed unchanged. Saved notes are labelled untrusted context data, not instructions. Examples are illustrations, not invented user history.
- A chat keeps current messages. Later chats receive notes from the same tester/style's last three eligible finished chats, oldest first. Other testers and the other style are excluded.
- Notes distinguish situation, feelings, **user** insights and **bot** suggestions. Summary shape is checked; factual accuracy requires a human check in live mode.
- Finish saves the conversation and generates notes. Failed summary jobs remain retryable. Stop/discard/empty chats do not produce recall notes. Corrections exclude the selected old note.
- Main controls are Send, Finish chat and More. Previous chats and data tools are collapsed. The limit is 20 answered user messages per chat, 1,500 characters each.

See [HOW_TO_USE.md](HOW_TO_USE.md) for the researcher/tester walkthrough and [memory/data details](docs/MEMORY_AND_DATA.md).

## Files

```text
README.md / HOW_TO_USE.md       Setup and operation
.env.example / setup_local.py   Safe private settings and key placeholder
run.py / requirements.txt      Standard-library-only local launch
app/config.py                  Mode, credentials and readiness checks
app/provider.py                OpenAI Responses API, summaries and explicit demo
app/prompts.json                Versioned system/style/memory/summary prompts
app/storage.py / chatbot.py     SQLite, ownership and conversation lifecycle
app/server.py / static/         Local API and simple interface
local data/ and private/        Runtime records; never packaged

docs/PROJECT_TASK_GUIDE.docx      Current detailed guide, progress and remaining experiment steps
docs/PROJECT_TASK_GUIDE.md        Editable text of the same guide
docs/PHASE1_AUDIT.md             Verified findings and remaining completion gates
docs/API_SETUP.md               Short activation checklist
docs/USABILITY_TEST_TEMPLATE.md  Blank form for the supervised human test
docs/MEMORY_AND_DATA.md          Retrieval, correction, retention and privacy
docs/CHATBOT_DESIGN.docx         Original design reference; current controls here
VERIFICATION.md                 Actual software check record
tests/test_chatbot.py            Automated workflow and boundary checks
tools/                          Preflight, API check, backup and packaging
MANIFEST.json                   Public file hashes
```

## Verify, back up and share

```sh
python3 -m unittest discover -s tests -v
python3 tools/backup.py data/chatbots-live.sqlite3 private/backup-live-YYYY-MM-DD.sqlite3
python3 tools/package.py
```

Choose a new dated backup filename; existing backups are not overwritten. The clean ZIP is generated beside this folder. It excludes private settings, records, exports and caches. Run `setup_local.py` after extracting on a new computer to create new private settings.

A virtual environment is optional; there are no external dependencies. If desired, use `python3 -m venv .venv` then `source .venv/bin/activate` on macOS/Linux. On Windows use `.venv\Scripts\activate` and, if needed, `py` instead of `python3`.

## Scope and privacy

This phase runs on the researcher laptop only. A localhost link will not give someone on another device access to your computer. Public deployment and the multi-participant experiment remain Phase 2; do not expose this HTTP prototype to the LAN/Internet.

In live mode, content leaves the laptop for OpenAI processing. `store=false` does not guarantee zero provider retention; see [official data controls](https://developers.openai.com/api/docs/guides/your-data). The local database is private but is not encrypted by the app. Human review and support arrangements remain necessary; keyword checks are incomplete.
