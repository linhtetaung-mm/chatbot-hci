# Free team preview on Render

This version lets teammates try Reassure and Guide now and decide on the database later. No disk, external database account or database subscription is required. Live OpenAI API usage is still charged separately.

## What this preview does

- Two distinct chatbot styles, labeled at the top.
- Context within the current conversation.
- Private access codes and a server-side API key.
- No chat database written to disk and no saved notes between chats.
- Finish, Stop, discard or sign-out clears the current tester's relevant chat content. Closing a tab alone does not clear it.
- Researchers can inspect active chats in RAM, but record exports/backups are disabled.
- Server restart/sleep clears everything in RAM, including codes, chats, consent confirmations, quotas and the admin pause switch. Admin credentials/API keys remain in Render Environment settings.

OpenAI still processes live chat text. This is not a claim of zero retention by OpenAI or Render, and service/network metadata may exist outside this app. Use fictional mild topics for the preview.

## 1. Push the updated project

In GitHub Desktop, select the repository **inside `phase1-chatbots`**, review the changes, commit and push. Your repository root should contain `app/`, `render.yaml`, `gunicorn.conf.py` and `requirements.txt`.

Never upload `.env`, `.venv`, `data`, private exports or existing databases. The refreshed ZIP excludes these files. This update did not push to GitHub or create a Render service.

## 2. Create the free service

1. Sign in to Render and connect GitHub.
2. Choose **New → Blueprint**, then select your chatbot repository and updated branch.
3. Keep the Blueprint file path **`render.yaml`**. It now specifies the **Free** plan, `STORAGE_MODE=temporary`, and no disk.
4. Enter your API key privately for `OPENAI_API_KEY`, and a reachable team contact for `RESEARCHER_CONTACT`.
5. Confirm the preview shows no paid disk or paid service, then create it.
6. Wait for deployment. Copy its public HTTPS URL.
7. Find the generated `ADMIN_KEY` in Render → service → Environment. Keep it private; this is your researcher password.

If a paid service was already created using the earlier configuration, do not assume that uploading the new Blueprint removes its disk or billing. For this preview, create a separate free service and check the old service's resources/billing separately. Preserve any authorized existing records before removing anything.

If creating a Web Service manually instead, use:

| Setting | Value |
|---|---|
| Plan | Free |
| Root directory | Blank when `app/` is at repository root |
| Build | `pip install -r requirements.txt` |
| Start | `gunicorn -c gunicorn.conf.py app.server:application` |
| Health check | `/health` |
| Disk | None |

Copy the variables from `render.yaml`, generating your own private random `ADMIN_KEY` of at least 24 characters. Use one instance and one Gunicorn worker. Render supplies the port and hostname. Do not set `PUBLIC_ORIGIN` unless you need an exact custom HTTPS origin.

## 3. Check the interface first

The Blueprint starts in **setup** mode, which sends no AI requests.

1. Open `https://YOUR-APP/health`; expect `ok: true` and `mode: setup`.
2. Open `/admin` and sign in with `ADMIN_KEY`.
3. Create one tester code per teammate. Privately send each person their code and the main URL.
4. Use **AI usage and access → Assign a chatbot remotely** to choose Reassure or Guide for each tester.
5. Have testers sign in at the main URL. Confirm the style and temporary-preview notice appear.

Tester codes are shown only once. They disappear on server restart; recreate and reissue them when needed. Keep admin access to designated researchers. Assignment revokes older tester sessions; the teammate signs back in with their code. Do not use **Open tester screen** unless you intend to switch your own browser into the tester session.

## 4. Enable real responses

In Render Environment:

```text
STORAGE_MODE=temporary
CHATBOT_MODE=live
OPENAI_API_KEY=<enter privately in Render>
OPENAI_MODEL=gpt-6-luna
OPENAI_REASONING_EFFORT=none
RESEARCHER_CONTACT=<your reachable contact>
```

Use a model your API project can access; blank the reasoning setting if that model does not support it. Preserve the existing review gate: set `HUMAN_TEST_REVIEW=confirmed` only after the applicable course/review requirements for this testing have been met. Proposal feedback alone does not establish approval of the participant procedure. Until then, interface checks are available in setup mode and fictional scripted checks in demo mode.

Save/redeploy. Recreate tester codes afterward because RAM is reset. The `/health` response confirms the mode but does not prove API access. Test one fictional mild-topic message to verify a real reply. The API key stays in Render; never send it to teammates.

**Do not set up `CHATBOT_DB` or attach a disk for this preview.** It is ignored in temporary mode.

## 5. Run the short team test

1. Open the app shortly before the agreed test time, sign in as researcher, and create fresh codes if it has restarted.
2. Have teammates try the same mild fictional situation in both styles. Reassign the style and ask them to sign in again to switch.
3. Ask for feedback on relevance, tone, repetition, how naturally the bot continues, and interface clarity.
4. Verify Finish/Stop clears the conversation, and that a new chat does not use previous-chat information.
5. Note feedback manually without copying sensitive chat text. These are team trials, not participant results or a test of persistent memory.
6. Pause AI requests in admin when the session ends. Already running requests can finish. Because a restart resets pause, disable live mode or remove the API key in Environment if access must remain off after a restart.

## Usage and free-tier limitations

Default caps: 50 attempts per tester/day, 250 app-wide/day, 500 total **per running process**, three attempts per tester/minute, five concurrent app calls and four new chats per tester/day. Replies and retries count. Temporary mode generates no summary calls.

These controls exist in RAM: restarting resets them, so they cannot enforce a lasting spending ceiling. Configure API-provider spending controls separately. Do not distribute the API key. Quotas cannot control use of that key outside this app.

Render Free may sleep after 15 minutes without traffic; startup can be slow. Treat sleep/restart/redeploy as losing the preview's temporary state and codes. No always-on availability is promised. See [Render free-service limits](https://render.com/docs/free).

## Local preview

Add `STORAGE_MODE=temporary` to your private `.env`, keeping your other private settings. Then start with `python3 run.py`. Stop an older running instance first; it will not adopt new settings until restarted. Existing local databases are not deleted or loaded in temporary mode.

## Database decision later

The app retains a shared storage interface with two implementations: in-memory working state and persistent SQLite. Your team can later choose local SQLite, a paid Render disk, or a hosted database such as Supabase (which requires a PostgreSQL adapter/migration). No hosted database credentials are needed now.

`render.persistent.yaml` and [the earlier persistent setup guide](docs/DEPLOY_RENDER_PERSISTENT.md) are optional future references. Do not select that Blueprint for the free preview. Re-enabling persistent memory requires deliberately selecting persistent storage and testing its full lifecycle; this preview does not verify the memory IV or complete the experiment.
