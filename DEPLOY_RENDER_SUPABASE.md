# Deploy the Supabase-backed chatbot on Render

9 November 2026. This is the current deployment guide for **Supabase**, not the earlier temporary preview or SQLite disk configuration. Render is the application host; Supabase stores the records. No Render disk is needed. GitHub test execution is separate from the running service.

## 1. Push the CI fix first

The provided screenshot shows the GitHub Actions `test` job failing, not a Render startup error. The screenshot does not include the Python failure traceback, and GitHub requires sign-in for the run logs. We therefore cannot attribute that exact run conclusively from the screenshot alone.

A reproducible test defect was found: the restricted-role test created a role with the SQL template password but tried to log in with `test-only`. Trusted local PostgreSQL authentication hid this; password-enforcing CI rejects it. The test now sets the same synthetic password for creation and connection. All 109 tests pass with password authentication enabled on a disposable local PostgreSQL instance. The Node.js deprecation warning was addressed by updating checkout to v5 and setup-python to v6 (Node 24 runtimes).

In GitHub Desktop, select the `phase1-chatbots` repository, review the updates, commit and push. The repository root should contain `app`, `tests`, `requirements.txt`, `gunicorn.conf.py` and `.github/workflows/tests.yml`. Wait for the **new commit's** checks to pass; re-running an older commit does not include the fix. If the new run fails, sign into GitHub, open Actions → failed run → test → failing step, and provide the final exception/traceback after removing any credentials. Do not treat the Node warning alone as the cause of an exit-code-1 test failure.

The automated tests use a disposable loopback PostgreSQL service and synthetic credentials, not Supabase. **Do not add your real DATABASE_URL, API key or certificate to GitHub Actions secrets to fix these tests.**

## 2. Keep the local and Render paths separate

| Setting | On your Mac | On Render |
|---|---|---|
| Certificate | `/Users/krown/HCIProj/hci-proj2/phase1-chatbots/private/prod-ca-2021.crt` | `/etc/secrets/prod-ca-2021.crt` |
| Config | Private `.env` | Render Environment |
| Records | Supabase database | Same Supabase database if schema/mode/model match |

The Mac path does not exist on Render. Keep `.env` and `private/` excluded from GitHub; do not remove the exclusions. The CA certificate is a public trust certificate rather than your database password, but Render Secret Files provide a clear way to supply the correct file without copying private project directories.

## 3. Verify and initialize locally before deploying

Keep your local `.env` certificate path as the Mac path. Confirm these settings privately:

```ini
DATABASE_BACKEND=supabase
STORAGE_MODE=persistent
DATABASE_SCHEMA=hci_live
CHATBOT_MODE=live
```

Keep the actual Session pooler URL, API key, model and researcher settings in `.env`. If you already use a different initialized schema, retain that name consistently rather than guessing `hci_live`. Use the **same OPENAI_MODEL** as the existing schema. Changing modes/models is intentionally rejected and requires a separate initialized schema.

With the local app stopped:

```sh
cd /Users/krown/HCIProj/hci-proj2/phase1-chatbots
source .venv/bin/activate
python -m pip install -r requirements.txt
python tools/database.py diagnose
python tools/database.py init
python tools/database.py check
```

Proceed only after PASS. Init validates an existing matching schema without clearing it. If using a restricted server role, initialize as the schema owner first; that server role cannot create a new schema.

**Do not leave `python run.py` running against the same schema during deployment.** This implementation uses one process per schema; the setup/check commands must finish and close their connections before Render starts. Separate localhost and cloud demos require different initialized schemas if both must run concurrently.

For synthetic checks, use a separate demo schema, e.g. `--mode demo --schema hci_demo`, on init/check/self-test. Do not accidentally run the demo command against an explicit `hci_live` schema.

## 4. Prepare the Render service

For an existing service, keep the app/repository connection and update its settings. For a new service, choose **New → Web Service**, connect `chatbot-hci`, and select the branch with the successful checks (the supplied screenshot uses `master`). Manual Web Service setup is recommended here because the certificate must be supplied separately.

| Setting | Value |
|---|---|
| Runtime | Python |
| Root directory | Blank if `app/` is at the repository root; otherwise the exact folder containing it |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn -c gunicorn.conf.py app.server:application` |
| Health check path | `/health` |
| Instances | 1 |
| Disk | None needed for Supabase |
| Auto deploy | Off initially; deploy deliberately after checks |

Free hosting is usable for team preview but sleeps after inactivity. A persistent Supabase database prevents losing records; it does not prevent host startup delays or interrupted requests. For independent participant access, prefer an always-on app instance or an appropriate university host after reliability testing. Do not begin the main study simply because this deployment works.

## 5. Add the certificate as a Render Secret File

1. Open your service → **Environment**.
2. Find **Secret Files → Add Secret File**.
3. Set Filename to exactly `prod-ca-2021.crt`.
4. Open your downloaded local `.crt` in a text editor. Copy its **entire PEM certificate text**, including `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----`, into Contents. Preserve all lines if it contains a certificate bundle.
5. Save. Render makes it available at `/etc/secrets/prod-ca-2021.crt`.

This is not a GitHub upload and does not mean putting the database password into the certificate field. For an existing temporary service, add the file before switching the database settings; it may trigger an intermediate redeploy. [Render Secret Files documentation](https://render.com/docs/configure-environment-variables#secret-files).

## 6. Set Render's environment variables

Enter values individually in the Render dashboard. Do not blindly import the local `.env`, which includes Mac paths and possibly localhost/port settings.

| Variable | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.8` |
| `DEPLOYMENT` | `render` |
| `CHATBOT_MODE` | `live` |
| `DATABASE_BACKEND` | `supabase` |
| `STORAGE_MODE` | `persistent` |
| `DATABASE_URL` | Complete private Session pooler IPv4 URL, including encoded database password |
| `DATABASE_SCHEMA` | `hci_live`, or the exact schema you initialized locally |
| `DATABASE_SSLROOTCERT` | `/etc/secrets/prod-ca-2021.crt` |
| `OPENAI_API_KEY` | Actual API key, entered privately |
| `OPENAI_MODEL` | Exact model used when initializing that schema |
| `OPENAI_REASONING_EFFORT` | Same tested setting as locally; `none` only if supported |
| `ADMIN_KEY` | Existing strong secret or a new random secret of at least 24 characters; never share with participants |
| `RESEARCHER_CONTACT` | Reachable contact |
| `SUPPORT_CONTACTS` | Reviewed support text appropriate to the procedure |
| `DELETE_DATE` | Actual agreed data-retention date |
| `HUMAN_TEST_REVIEW` | Existing applicable review acknowledgement; set `confirmed` only if those requirements have been met |

Remove a localhost `PUBLIC_ORIGIN` override; Render's HTTPS hostname is detected automatically. If using a custom domain, set its exact HTTPS origin. Do not override Render's PORT, put a URL into `CHATBOT_DB`, or use `STORAGE_MODE=temporary` for durable records. Supabase bypasses the SQLite persistent-disk requirement.

Keep API limits deliberately configured. Current demo defaults (250 app requests/day and 500 total) are insufficient for the full 48-person/four-chat protocol. Raise them only against an agreed budget and measured pilot usage; do not remove safeguards or reset counters to work around caps.

## 7. Deploy

Save environment changes and deploy the latest commit. Watch Events/Logs for startup completion. Do not share full logs containing unexpected credentials.

Initial switch from a temporary deployment is straightforward because the old process is not holding a Supabase schema lock. For later Supabase-to-Supabase redeploys, the current single-process design needs a **stop/start deployment**: suspend/stop the old service and wait for it to terminate before starting the new release. An ordinary rolling replacement starts the new instance while the old one owns the lock and can fail with “Another chatbot process.” If your selected hosting controls cannot perform a stop/start replacement, resolve that deployment limitation before relying on repeated updates. Disable automatic deployment during collection and avoid releases while people chat. Render normally uses overlapping zero-downtime deployments; one instance alone does not disable that behavior. [Render deployment behavior](https://render.com/docs/deploys).

Do not add a paid disk just to evade this lock; the application design, not missing database storage, is the cause. Do not repeatedly deploy against a still-running local copy.

An optional `render.supabase.yaml` is included for later Blueprint use; it declares the Supabase settings but **does not upload your certificate automatically**. The existing `render.yaml` still describes the earlier temporary preview, so do not expect it to switch storage for you.

## 8. Verify the deployed app

1. Open `https://YOUR-SERVICE/health`; expect `ok: true` and `mode: live`. Startup includes checking the selected database schema. Health does not call or verify OpenAI.
2. Open `/admin`, sign in privately, and create a synthetic tester if needed.
3. Open the main URL in a separate browser and use that tester's code. Participants receive the main URL, never the admin secret.
4. Complete a fictional chat, Finish, and inspect its transcript and ready summary.
5. Sign out and return. Start a second same-style chat and check that expected notes are selected.
6. Verify another tester cannot access the first tester's history; test the second style's separate notes.
7. Test actual persistence after a controlled stop/start deployment outside a participant session.
8. If restarting to verify records, leave local copies stopped. Export/backup separately according to the actual retention procedure.

Database persistence is now a deployment feature; immutable four-condition assignment, visit scheduling, outcome linkage and approved study procedures are still separate release requirements.

## If it fails

| Error | Meaning/action |
|---|---|
| GitHub Actions test failed | Open the latest run's actual Python traceback; the Render Secret File cannot fix a disposable CI database test |
| Certificate file missing | Secret File filename/path mismatch, or a Mac path copied into Render |
| Certificate verification failed | Check the file's full PEM content and that it is the correct CA downloaded for the Supabase database |
| Database authentication rejected | Check copied pooler username, database password and URL encoding; unrelated to the OpenAI key |
| Schema/mode/model mismatch | Use the exact initialized schema and matching settings; preserve old records |
| Another chatbot process | Stop local/older deployed copies; ordinary rolling redeployment conflicts with the schema lock |
| API not connected / setup | Set CHATBOT_MODE to live with the existing required settings; the banner is not a test of API credentials |
| Health succeeds but AI fails | Check OpenAI billing, key/model permissions and supported model settings separately |

No GitHub push, Render environment change or live deployment was performed by this documentation/fix update. The CI defect was reproduced and fixed locally; the exact private run logs were not available for confirmation.
