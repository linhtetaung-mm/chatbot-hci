# Connect this chatbot to Supabase

Updated 9 November 2026. Supabase/PostgreSQL support is now implemented. This works locally or on a later hosting service; Render is not required. Your actual Supabase connection has not been tested because the private URL is still a placeholder.

## 1. Install the updated requirements

Open a terminal in `/Users/krown/HCIProj/hci-proj2/phase1-chatbots`:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If there is no virtual environment, create it first with `python3 -m venv .venv`. Use Python 3.10+ (3.12 recommended). The PostgreSQL backend uses Psycopg 3.3.8; the local SQLite backend requires SQLite 3.35+ for INSERT RETURNING.

## 2. Fill the private .env placeholders

Open `.env` locally. The update appended missing database settings and preserved existing values, including your OpenAI API key. Set:

```ini
DATABASE_BACKEND=supabase
STORAGE_MODE=persistent
DATABASE_URL=postgresql://YOUR_POOLER_USER:YOUR_URL_ENCODED_PASSWORD@YOUR_POOLER_HOST:5432/postgres
DATABASE_SCHEMA=
DATABASE_SSLROOTCERT=system
```

Copy the complete **Session pooler / IPv4** URL from Supabase → Connect. Replace its password placeholder; URL-encode reserved characters in the password. Copy the host, username and port instead of guessing them. This is the database password, not your Supabase account password or an API key.

If the copied URL includes `sslmode=require`, remove that option or change it to `sslmode=verify-full`. This implementation requires certificate and hostname verification, rather than accepting an unverified encrypted connection. Keep credentials off GitHub and out of screenshots/chat.

Leave the schema blank initially. The app chooses `hci_live`, `hci_demo` or `hci_setup` according to `CHATBOT_MODE`. This separates scripted test records from actual live records. An explicit schema must start with `hci_` and contain only lowercase letters, digits and underscores.

Keep your existing `CHATBOT_MODE`, `OPENAI_API_KEY`, model, researcher contact and applicable review settings. Database selection does not turn AI on or bypass the existing live-mode checks. The `CHATBOT_DB` setting is ignored by the Supabase backend; do not replace it with a URL.

You do **not** need `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, Supabase Auth, a vector database, or a paid disk for this connection. The server uses the PostgreSQL connection string and its existing private tester-code authentication.

[Supabase's official connection instructions](https://supabase.com/docs/guides/database/connecting-to-postgres).

## 3. Stop existing copies of the app

Use Ctrl+C in the app's terminal. Stop any other deployed copy that already uses the same schema before initialization/checking. The database supports **one running chatbot process per schema**. Separate schemas can be used for independent local/test deployments.

A held Session-pooler connection owns a schema-specific advisory lock. A second process is rejected instead of changing pending records belonging to another server. One Gunicorn worker with multiple threads remains the supported deployment. Rolling/zero-downtime replacement against the same schema is not supported: stop the old process before starting an upgraded one, and schedule the interruption outside participant chats. The command-line setup/check tools also use that lock, so run them with the corresponding app stopped.

## 4. Initialize and test the demo schema

With `DATABASE_SCHEMA` blank, run:

```sh
python tools/database.py init --mode demo
python tools/database.py check --mode demo
python tools/database.py self-test --mode demo
```

Expected results:

- Init: `PASS: schema initialized/validated | hci_demo | demo`
- Check: `PASS: database connection/schema validated | hci_demo | demo`
- Self-test: `PASS: messages, summary, restart persistence and separate style memory. No OpenAI calls made.`

The synthetic test creates a temporary tester, saves a fictional chat and note, closes/reopens its database connection, checks recalled notes and style isolation, then removes that tester. It uses no AI calls. Small content-free quota receipts remain in the demo schema; repeated runs count toward demo quotas.

Init creates eight application tables in the private schema: settings, testers, conversations, messages, memories, events, logins and api_attempts. It enables row-level security and grants no access to the database PUBLIC role. It does not use the public/Data API schema. Existing schemas are validated, never silently cleared or recreated.

## 5. Initialize your chosen running mode

For actual AI conversations, retain `CHATBOT_MODE=live` and the existing valid OpenAI settings in `.env`. Keep `DATABASE_SCHEMA` blank. Then run:

```sh
python tools/database.py init
python tools/database.py check
python run.py
```

If mode is live, the first two commands should name `hci_live`, not `hci_demo`. If they name `hci_setup`, the environment is still in setup mode. Changing a mode or model later requires a different initialized schema so previous provenance remains intact. Initialization does not call OpenAI.

Open `http://127.0.0.1:8766/admin`. Create new tester codes in the Supabase-backed app. Existing local/RAM tester codes and chats are not automatically migrated; existing SQLite files are preserved untouched.

In Supabase's Table Editor, select the appropriate `hci_*` schema instead of `public` to inspect test records. Do not expose that schema through the Data API or disable RLS to make it visible in a browser. Table Editor access is for designated researchers only.

## 6. Verify actual use and memory

Use fictional concerns before any participant collection:

1. Create a tester and assign a style.
2. Complete consent, send messages and Finish.
3. Confirm the conversation is completed and the memory note is ready.
4. Sign out and sign back in. The tester code, chat and notes should remain.
5. Start another chat in that style and inspect its selected memory IDs in admin.
6. Try the other style with a test account and confirm its notes are separate.
7. Stop the app, restart it, and confirm the same records and counters remain.
8. Exercise summary failure/retry, correction, Stop and deletion on synthetic records.

There are two independent settings: `STORAGE_MODE=persistent` saves research records; a future experimental `Fresh` policy must separately prohibit retrieving earlier notes for model input. This change implements the durable backend for the existing chatbot. It does not add fixed four-condition assignment, visit stages or questionnaires.

## TLS certificate troubleshooting

A real endpoint check on 9 November failed at certificate verification with `DATABASE_SSLROOTCERT=system`. No downloaded project certificate was found locally. This does not establish whether the password is correct; TLS must succeed first. Download the project CA certificate using the dashboard steps below. The app now identifies certificate failures explicitly rather than displaying only a generic connection error.

You can check transport/authentication without initializing tables or acquiring the app's schema lock:

```sh
python tools/database.py diagnose
```



`DATABASE_SSLROOTCERT=system` asks the PostgreSQL driver to use system certificate trust. If your project/pooler certificate cannot be verified, download the appropriate CA certificate from Supabase's database SSL configuration. Keep it locally, for example in `private/prod-supabase.cer`, then set:

```ini
DATABASE_SSLROOTCERT=/absolute/path/to/private/prod-supabase.cer
```

Use the absolute path on the machine running the app. On a future host, supply the certificate there and use its host-local path. Do not disable verification, use transaction pooler port 6543, or paste certificate/password screenshots into support messages. [Supabase TLS guidance](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Privacy and server credentials

Use a dedicated study project and restrict dashboard membership. The server credential can access raw records, so protect it like the OpenAI key. The browser never receives it. No connection URL or server error body is printed by the diagnostic commands.

The initial Session pooler URL commonly uses the project's database owner. For tighter separation before main collection, initialize with that owner and then create a restricted server role using `app/migrations/server_role_optional.sql`, following its instructions. Do not reuse a project that contains unrelated sensitive applications. Row-level security is defense in depth; the backend must still authorize every tester operation, because the trusted server role must access multiple participants' records.

Update the participant information/consent to name the actual server host, Supabase storage region, OpenAI processing, access roles and retention/deletion arrangements. Raw free-text narratives are not anonymous simply because IDs replace names. Decide the handling of stopped chats, withdrawals, backups and exports before real collection.

For step-by-step Render deployment with Secret Files, see [DEPLOY_RENDER_SUPABASE.md](DEPLOY_RENDER_SUPABASE.md).

## Backups and future hosting

The old `tools/backup.py` is SQLite-only. Use Supabase/PostgreSQL dump and restore tools for this backend, and rehearse restoration into a separate test database. Free projects need private off-site exports rather than an assumption of paid backup coverage. [Supabase backup guidance](https://supabase.com/docs/guides/platform/backups).

When a host is selected, configure the same server-only environment variables there. The host needs a reachable PostgreSQL Session pooler connection, your certificate if needed, the updated requirements and one process. Initialize the chosen schema from a trusted local machine with the app stopped; do not run migrations automatically on every deployment. For non-Render hosting set `PUBLIC_ORIGIN` to the exact public HTTPS origin and provide the host's PORT.

Supabase does not require a paid Render disk, even if you later choose Render. It also does not remove the availability limitations of whichever app host you select. Existing Render blueprints still explicitly describe the previous temporary/SQLite options; do not assume they configure Supabase automatically.

## Common problems

| Message/problem | Action |
|---|---|
| Missing/invalid DATABASE_URL | Fill the placeholder with the complete Session pooler URL and encoded database password |
| Supabase requires persistent mode | Set both `DATABASE_BACKEND=supabase` and `STORAGE_MODE=persistent` |
| Cannot connect | Check copied host/user/port, password encoding, project availability, network and CA certificate; credentials are not printed |
| Another chatbot process | Stop the copy using this schema; do not attempt to run local and deployed copies against it simultaneously |
| Operation failed / missing tables | Stop app, run init/check; verify schema and server role permissions; no RAM fallback occurs |
| Schema/mode/model mismatch | Preserve the current schema; select and initialize a new `hci_*` schema for the changed mode/model |
| Check succeeds but no AI replies | Database checks do not verify API billing/access. Check CHATBOT_MODE and existing OpenAI settings |
| Old local tester code rejected | Supabase starts with new records; create new testers. Local history is not auto-imported |
| Pending request after crash | Restart does not globally rewrite pending records. Retry the original message; an active API reservation may require up to two minutes to expire |
| Quota reached | Current limits are still team-demo defaults. Set study quotas against an approved budget before collection; do not clear counters to bypass them |

## What has and has not been verified

The implementation passed the existing RAM/SQLite checks and actual PostgreSQL integration tests using a disposable local PostgreSQL server. No cloud credentials or OpenAI calls were used. Your specific Supabase endpoint, pooler authentication, TLS chain, permissions and any future hosting deployment still require the init/check/self-test commands and live acceptance checks above. Existing data has not been migrated.
