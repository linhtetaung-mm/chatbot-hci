# Supabase Free: account setup and implementation checklist

9 November 2026. This is a setup/migration plan, **not an implemented PostgreSQL connector**. Nothing here changes the deployed app or creates a database. Use synthetic records until the applicable participant review, privacy procedure and deployment tests are complete.

## Account setup (project owner)

1. Create/sign in to a Supabase account at https://supabase.com/dashboard. Use an account the team can retain under its agreed access/retention arrangements; do not share a common password.
2. Create a Free organization/project dedicated to this study. Name it clearly, for example `reassure-guide-study`. Choose the same nearby region as the application if available and compatible with the reviewed data-location requirements. Record the actual region; proximity is not proof of institutional permission.
3. Generate a strong database password and keep it in a password manager. Give access only to designated researchers. Decide who can inspect raw text and backups before collecting any.
4. Leave real participant data out. Do not turn off database protections to make a connection work.
5. In the project's Connect dialog, obtain the **Session pooler** connection string for the Python service when using an IPv4 connection. Copy the host/username/port from that dialog instead of constructing them from the region. The direct Free endpoint is IPv6; it may not work from an IPv4-only network. [Connection options](https://supabase.com/docs/guides/database/connecting-to-postgres).
6. Keep the completed database URL private. In the later Render configuration it will be a server environment variable such as `DATABASE_URL`, not frontend JavaScript, GitHub or a group-chat message. Obtain the appropriate certificate/TLS settings: use verified TLS where supported and never silently fall back to plaintext.
7. Creating the project is not enough to activate it in this app. **Do not put a PostgreSQL URL into `CHATBOT_DB`**. That variable currently points to a SQLite file. Wait for the tested adapter and schema migration.
8. Monitor storage and activity. Current Free allowance is 500 MB and projects may pause after a week of low activity. [Pricing](https://supabase.com/pricing), [pausing](https://supabase.com/docs/guides/platform/free-project-pausing).

Do not paste database passwords, project secrets or connection strings into this chat. Screenshots of connection pages may expose secrets too.

## Intended deployment boundary

Participant browser → authenticated Python server on Render → PostgreSQL on Supabase.

Python server → OpenAI: current successful conversation and permitted prior notes only.

Google Forms/Sheets: questionnaire originals, verified study IDs and restricted operational/analysis exports. No public shared transcript sheet. Booking contacts stay separate from outcome records.

Keep existing private-code authentication unless there is a clear need to replace it. Supabase Auth is optional, not a requirement to use its database. Keep study tables in a private/non-Data-API schema and grant a dedicated server role only the privileges it needs. If exposing any tables through the Data API, explicitly configure RLS, policies and grants; do not assume existing app sessions automatically become Supabase `auth.uid()` identities. Service-role credentials or direct database privileges can bypass RLS, so ownership authorization must still be enforced in the backend. Never place privileged credentials in a browser. [RLS documentation](https://supabase.com/docs/guides/database/postgres/row-level-security).

## Required implementation changes (developer)

1. Introduce a named PostgreSQL backend and its configuration, independent of temporary/persistent memory policy. Keep RAM for team demos and SQLite for local tests. Make study mode fail closed if durable storage is missing; never silently substitute RAM.
2. Use a maintained PostgreSQL driver with a small connection pool, bounded connect/statement timeouts and verified TLS. Keep network/API waits outside database transactions. Test reconnect after both host and database inactivity.
3. Create explicit versioned migrations. Port SQLite `?` placeholders, row/ID handling, positional inserts, `INSERT OR IGNORE/REPLACE`, PRAGMAs and `BEGIN IMMEDIATE` to PostgreSQL equivalents. Use explicit column names and preserve uniqueness/foreign-key constraints. Avoid a blanket text replacement compatibility layer.
4. Store the four-condition assignment separately from operational storage mode. `memory_policy=fresh` is compatible with saving consented transcripts; `storage_mode=temporary` is not an experimental Fresh condition.
5. Add participant records (stable ID, locked condition, cohort/test marker, enrollment status), versioned consent, scheduled/actual visits, chat purpose/stage, ratings/Form linkage and final task/activity records. Preserve source IDs, timestamps, sequence/status, returned model and prompt hashes.
6. Keep separate structured summary fields with user/bot provenance and source conversation IDs. Generate summaries consistently across conditions if following the agreed guide. Retrieve none for Fresh; retrieve the last three eligible same-person notes for Persistent. Recheck exclusions before every reply.
7. Use atomic database quota reservations and study allocations across all deployed processes. Existing in-process conversation locks alone do not protect multiple processes. Replace startup-wide pending-message resets with owned leases/recovery. Record API metadata for summary attempts as well as replies.
8. Ensure chat finish, summary job creation and retries are idempotent. Persist messages before/after network requests with unambiguous states. Handle uncertain outcomes without silently double-counting a treatment chat or dropping content. A browser timeout may still have incurred provider cost.
9. Make conditions immutable for main-study participants, while allowing explicit test accounts to switch styles. Separate code creation, consent, random allocation and study activation. Do not let account creation or a guessed URL reveal the condition.
10. Preserve Stop/withdrawal and deletion semantics. Define handling of pending work after stop/deletion. Apply the actual policy to primary records, summary references, exports, contacts and backups. Retain only the technical metadata covered by that policy.
11. Remove temporary-preview wording only once the durable system and new consent are actually active. Show a neutral participant interface with one next action, exposed Stop/help, no treatment labels and verified Google Form IDs.
12. Add full deployed-backend integration tests. SQLite/RAM tests are regression coverage, not PostgreSQL verification.

## Database acceptance test

Use synthetic test participants for all four cells. Required evidence:

- Messages/consent/condition/notes survive logout, Render restart and redeploy.
- Fresh's actual payload contains zero earlier-note IDs in Chats 2–4; Persistent's contains the correct ones. Neither leaks another person's data.
- Failed/incomplete summaries are recoverable without silently changing the context window.
- Simultaneous sends/retries, worker interruption and deployment overlap do not duplicate or lose records.
- Conditions cannot be switched through participant routes or ordinary admin convenience controls for active main-study users.
- Quota/pause state survives restart and has enough budget for the full protocol.
- The participant Form ID joins correctly, unauthorized record access fails, and coder exports omit assignment.
- A backup is restored into a separate test database and checked for completeness.
- Withdrawal/deletion is exercised against synthetic data, including the agreed backup/export policy.

## Backup and retention

Supabase recommends regular exports and off-site backups for Free projects; do not rely on paid-plan backup features being available. Use the Supabase CLI/PostgreSQL-supported dump/restore flow appropriate to the connection; the existing `tools/backup.py` is SQLite-only and cannot back up PostgreSQL. Run a restore rehearsal, not just a dump command. [Backup documentation](https://supabase.com/docs/guides/platform/backups).

Store backups privately with restricted access and the agreed retention schedule; document exactly how often and who performs them. Never add a dump to GitHub. Confirm the date currently in app settings is the actual reviewed date, rather than retaining the default automatically.

## What remains outside these files

Account creation, database provisioning, secure credential entry, adapter/migrations, participant study UI and actual deployed acceptance testing remain to be performed. Do not start collection merely because the Supabase dashboard opens or a connection check succeeds. See the release gate in `READINESS_REVIEW.md`.
