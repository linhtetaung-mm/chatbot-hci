# Deploy Reassure and Guide for private team testing

Updated 7 November 2026. This guide is for the `phase1-chatbots` repository, not the older `study-kit` app.

## What is included

Two styles with separate memories for each tester/style; saved notes from up to three finished chats; private tester codes; researcher-only inspection and exports; HTTPS sessions; persistent request limits; pause/resume; and remote style assignment. The key stays on the server.

This release prepares the existing chatbot for **team testing**. It does not add the Fresh memory condition, random assignment, Google Forms/Sheets integration, or the complete longitudinal experiment. Do not describe deployment as completing the study or obtaining review approval.

## 1. Upload the updated source

Use the Git repository inside `phase1-chatbots`, connected to `chatbot-hci`. Review and commit the updated files in GitHub Desktop, then push them. Do not upload the parent HCI project or old study-kit. No push has been performed by this update.

The repository root should contain:

```text
app/
tests/
tools/
requirements.txt
render.yaml
gunicorn.conf.py
DEPLOY_RENDER.md
README.md
```

Never commit `.env`, `.venv`, `data`, exported records, database files, or private backups. `.gitignore` already excludes them. Existing local chats will not automatically appear on Render; deployment starts a new database.

## 2. Create the Render service

Use a **paid web service with a persistent disk**. This design stores SQLite on disk. Free services cannot attach persistent disks, and ordinary service files are lost on restart/redeploy. See [Render persistent disks](https://render.com/docs/disks). Check the current service and disk charges in Render before creating them.

### Recommended: Blueprint

1. Sign in to Render and connect your GitHub account.
2. Choose **New → Blueprint** and select `chatbot-hci`.
3. Select the branch containing the updated files. Keep the Blueprint path `render.yaml` if it is at the repository root.
4. Review the proposed paid Starter service, Singapore region and 1 GB disk.
5. For `OPENAI_API_KEY`, enter your API key privately in Render. For `RESEARCHER_CONTACT`, enter the team contact testers can reach. Never place the key in the YAML or chat.
6. Create the resources. Wait until the service reports that deployment succeeded.
7. Copy the public HTTPS URL. It will look like `https://your-service.onrender.com`.

The Blueprint starts in **setup** mode, so it makes no AI calls. Render generates `ADMIN_KEY`; copy that value from the service's Environment settings into your password manager. It is the researcher login secret. Share tester codes, not this secret.

The app automatically uses `RENDER_EXTERNAL_HOSTNAME` for its public origin. Do not add a guessed URL. If using a custom domain later, set `PUBLIC_ORIGIN` to its exact HTTPS origin, without a path. Only that configured host is accepted.

### Alternative: manual Web Service

If you prefer **New → Web Service**, use these settings:

| Setting | Value |
|---|---|
| Runtime | Python |
| Root Directory | Blank if `app/` is at repository root |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn -c gunicorn.conf.py app.server:application` |
| Health check | `/health` |
| Instances | 1 |
| Plan | Paid plan supporting a persistent disk |
| Disk mount | `/var/data` |
| Disk size | 1 GB |

Add the variables from `render.yaml` manually. Generate an `ADMIN_KEY` of at least 24 random characters, preferably using a password manager. Use Python `3.12.8` as specified in the Blueprint. Do not set `PORT`; Render provides it. The startup command binds to Render's port on all interfaces.

If your GitHub repository contains the `phase1-chatbots` folder inside another folder, set Root Directory to its actual relative path. For a Blueprint, add the corresponding `rootDir` field and select the correct Blueprint file path. Do not move unrelated project documents into the deployment repository.

## 3. Check setup mode before enabling AI

1. Open `https://YOUR-SERVICE/health`. Expect `{"ok": true, "mode": "setup"}`.
2. Open `https://YOUR-SERVICE/admin` and sign in with the generated `ADMIN_KEY`.
3. Create a tester and save its one-time code privately. Codes cannot be recovered later.
4. Under **AI usage and access**, assign that tester to Reassure or Guide. This does not sign you out.
5. Open the main URL in an incognito window or a separate browser. Sign in using that tester's code.
6. Check the style name at the top, consent information, researcher contact and deletion date. Sending is disabled in setup mode.

Each teammate should have their own code. Anyone holding a code can use that tester's records, so send it privately. There is no public registration. The site/login page is publicly reachable, but chats and records require authentication. The `/admin` page requires the researcher secret; knowing its URL is not sufficient.

For testing both styles, assign the same tester to the other style and have them sign out/sign back in. Assignment revokes earlier tester sessions. Reassure and Guide retain separate histories. Use the **Open tester screen** form only when deliberately taking over the tester browser yourself; it switches your session away from admin.

## 4. Enable live AI deliberately

In Render → service → Environment, set:

| Variable | Value/action |
|---|---|
| `CHATBOT_MODE` | `live` |
| `CHATBOT_DB` | `/var/data/chatbots-live.sqlite3` |
| `OPENAI_API_KEY` | Real API-project key, kept private |
| `OPENAI_MODEL` | A model you have verified your API project can use; default `gpt-6-luna` |
| `OPENAI_REASONING_EFFORT` | Default `none`; remove/blank for a model that does not support this setting |
| `RESEARCHER_CONTACT` | A reachable team contact |
| `SUPPORT_CONTACTS` | Locally verified support information appropriate to your procedure |
| `DELETE_DATE` | The team's actual storage deletion date |
| `HUMAN_TEST_REVIEW` | `confirmed` only once the applicable course/review requirements for this testing are met |

Save and redeploy. Instructor proposal feedback alone does not establish procedure/consent approval. If that review is still pending, remain in setup mode for interface checks or demo mode for clearly labeled fictional simulations (`CHATBOT_DB=/var/data/chatbots-demo.sqlite3`). Do not mark the review confirmed just to bypass startup validation.

The live database must be different from the setup/demo database. Mode/model are recorded in each database; changing either requires a new filename to preserve provenance. Setup-mode invitations do not carry over into a new database: create fresh tester codes after switching. ChatGPT Plus does not fund API calls; check your API billing separately.

Open `/health` again and check that the mode is live. This health check does **not** call OpenAI or prove the key works. Send one fictional mild-topic message as a tester to verify actual API access.

## 5. Usage limits and cost control

The default settings are intentionally conservative for the five-person team:

| Environment variable | Default | Scope |
|---|---:|---|
| `TESTER_DAILY_API_LIMIT` | 50 | Attempts per tester across both styles per UTC day |
| `GLOBAL_DAILY_API_LIMIT` | 250 | Attempts for the whole app per UTC day |
| `GLOBAL_TOTAL_API_LIMIT` | 500 | Attempts for this database across all days |
| `TESTER_MINUTE_API_LIMIT` | 3 | Attempts per tester in a rolling minute |
| `GLOBAL_CONCURRENT_API_LIMIT` | 5 | Simultaneous calls across the app |
| `TESTER_DAILY_CHAT_LIMIT` | 4 | New chats per tester across both styles per UTC day |

Each reply, memory summary, summary retry and failed API attempt consumes one attempt reservation. Blocked requests consume none. The existing 20-user-message cap remains per conversation. Demo operations also consume local reservations, but never incur API charges. An ordinary completed chat with ten AI replies and one summary uses eleven attempts. Finishing a chat immediately after three quick requests may delay its summary; the researcher can retry it after the minute window.

Counters persist across app restarts/redeploys. Deleting tester records does not reset the app's total counter; only a content-free tester-ID hash, operation kind and attempt timestamps/status remain in this quota ledger. The hash is pseudonymous metadata, not a promise of anonymity. Retain/delete the database and its backups according to your actual retention policy. Do not switch database paths merely to bypass a budget cap. Adjust a limit deliberately in Environment and redeploy after checking spending. A new model/database intentionally starts its own counters.

The admin **AI usage and access** section shows total and today's attempts and has **Pause AI requests**. Pause blocks new replies, summaries and retries; already running calls may complete and incur cost. Stop, logout, inspection and deletion remain available. Resume when ready. The pause state persists in the database.

These are **request caps, not a guaranteed dollar cap**. Input size varies with history and saved notes. Chat responses are capped at 250 output tokens and summary responses at 700. The app also caps message size and total assembled chat context. Set the API project's own spending controls and alerts, and watch actual API costs. Using the same key outside this app bypasses its caps. Render hosting charges are separate.

Sign-in attempts are limited separately to 15 per minute per connection IP. The app does not trust visitor-supplied forwarding headers. Depending on Render's proxy, testers may share an effective IP; if several team members hit this limit, wait a minute rather than repeatedly retrying. Private random access codes remain the main access control.

## 6. Team acceptance test before inviting anyone else

Record dates and outcomes. Use fictional topics first.

1. Verify the deployment is running the intended Git commit and live mode.
2. Confirm an unsigned-in browser cannot read `/api/admin/export` or `/api/state`.
3. Create separate codes for two teammates; verify they cannot see each other's histories.
4. Test both styles with the same mild scenario and review whether their support behaviors differ as intended.
5. Finish a chat. In admin, inspect its notes and confirm that they accurately reflect what was said.
6. Start another chat in the same style and check its memory source IDs and relevant recall. Avoid encouraging unnecessary personal disclosure just to exercise memory.
7. Assign the other style, sign back in and confirm the first style's notes are absent there.
8. Pause AI in admin. Confirm a new message is blocked without an AI response; resume, then retry the same pending message.
9. For a cap test, temporarily set `TESTER_DAILY_API_LIMIT=1` in a dedicated test database. One reply should work; a second attempt and the finishing summary should be blocked. Increase the cap and retry the summary. Restore the intended configuration afterward.
10. Redeploy with the same database path. Confirm login codes, chats, notes and usage counts remain. This is the key persistence check.
11. Test Stop during a reply, logout, memory correction, reset and deletion using test records.
12. Check mobile layout and English wording with a teammate. Record any delays, errors, repetition or style drift.

Do not include team trials in participant study results. Before participant collection, resolve the separate procedure/consent/privacy review, final conditions and assignment plan, measures and questionnaires, recruitment and withdrawal procedures, and study data handling. This chatbot release is not a validated clinical intervention.

## 7. Privacy, backups and operation

- The privacy notice names OpenAI processing and Render hosting, plus team access and the configured deletion date. Review it against the actual course procedure and provider arrangements. `store: false` is sent to the API; it is not a guarantee of zero provider retention.
- Keep admin access limited to designated researchers. Neither the browser nor the tester code receives the API key.
- The app does not write conversation text into its request logs. Render infrastructure still handles network metadata; downloaded exports contain sensitive records and must stay private.
- For a content export use admin → Data tools → Download private records. This is JSON for review, not a restorable SQLite backup.
- For a restorable backup, use Render's Shell and run `python tools/backup.py /var/data/chatbots-live.sqlite3 /var/data/backups/chatbots-live-YYYY-MM-DD.sqlite3`, replacing the date with a unique value. Download it through Render's SSH/SFTP facility and store it securely. Never copy just the live `.sqlite3` file while it is running in WAL mode.
- A database backup contains tester access-code hashes and sessions as well as records. Protect it accordingly. Restoration replaces current state and may revive older access sessions; arrange a controlled pause and session invalidation before restoring. No automated restore tool is included.
- Test the documented backup/restore procedure on a disposable copy before relying on it. Exports/backups are separate copies: app deletion does not remove them.
- Persistent disk deployments may briefly interrupt service. Avoid redeploying while testers are chatting. Keep **one instance and one Gunicorn worker**: chat locks and startup recovery are designed for that topology. Do not add workers, enable preload, or add autoscaling.
- If you suspect key disclosure, pause the app, revoke/replace the API key, update Render Environment and redeploy. If the researcher secret is disclosed, change it and invalidate old admin sessions using a controlled database operation; changing the secret alone does not revoke already issued sessions. For tester-code disclosure, delete the compromised test record and issue a new tester code after preserving only records you are permitted to retain.
- Pause when a testing window ends. Remove the service/disk and private backups according to the retention plan when no longer needed.

## Troubleshooting

| Symptom | Check |
|---|---|
| Startup says attach persistent disk | Disk must be mounted at `/var/data`; check Render disk setup, not an ordinary folder |
| Host/origin rejected | Open the exact public HTTPS URL; remove a wrong `PUBLIC_ORIGIN`; do not add paths or a trailing `/admin` to it |
| Sending disabled | Setup mode deliberately disables AI; follow live activation steps |
| Live startup refuses settings | Check key, contact and applicable review confirmation; never paste values into support chats |
| Database mode/model differs | Select a new mode/model-specific database filename; preserve the existing one |
| No tester codes after switch | A different database starts empty; create new invitations |
| 401/403/404 from OpenAI | Key/project/model permissions may be wrong; inspect the safe user error and private API project settings |
| 429 or quota errors | Check app attempt counters, API billing/credit and API rate limits; distinguish app caps from provider errors |
| Memory failed | Chat is saved; fix the cause then admin → Inspect → Retry summary. Do not discard a successful chat to work around it |
| Pending message after restart | Retry the same message/request; do not repeatedly submit new versions |
| Local port in use | Open the existing local app or stop its terminal; Render uses its own port |

Official references: [Render Python deployment](https://render.com/docs/deploy-flask), [Blueprint configuration](https://render.com/docs/blueprint-spec), [persistent disks](https://render.com/docs/disks), [health checks](https://render.com/docs/health-checks). The app is WSGI, so it does not require Flask.
