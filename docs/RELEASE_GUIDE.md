# Commit, push and deploy — release checklist

Prepared against the current code on 11 November 2026. Application folder: `/Users/krown/HCIProj/hci-proj2/phase1-chatbots`. Repository: `https://github.com/linhtetaung-mm/chatbot-hci`. The cleanup is currently uncommitted on **`codex/clean-study-workflow`**, based on `origin/v2` at `f0d9247`.

The route below is: local checks → commit the cleanup branch → push it → merge its reviewed pull request into `v2` → deploy `v2` on the existing Render service → verify the hosted app. These are instructions; no commit, push or deployment has been performed for you.

## 1. Prepare a quiet release window

- [ ] Nobody is currently using the deployed chatbot for a study session.
- [ ] Record the current live commit, Render branch and non-secret settings, including schema, mode, model and quota values. Keep a private copy of the actual settings separately.
- [ ] If records exist, download the chat CSV and all-records JSON into restricted storage. JSON is a record export, not an automatic database restore.
- [ ] Turn Render **Auto-Deploy** off before merging anything. Keep deployment deliberate during collection.
- [ ] Keep the approved protocol, questionnaire wording and experimental settings unchanged.

This release does not introduce a database migration. Do not delete, recreate or rename a working schema just to deploy it.

## 2. Run the local code checks

In Terminal:

```sh
cd /Users/krown/HCIProj/hci-proj2/phase1-chatbots
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

If `.venv` does not exist, first run `python3 -m venv .venv`, then activate and install as above. Do not overwrite your existing `.env` or rerun setup to replace working settings.

Expected: `OK`. PostgreSQL integration tests skip unless `HCI_TEST_POSTGRES_URL` points to a disposable loopback test database. Do **not** set it to Supabase. GitHub Actions supplies an isolated PostgreSQL service for the full suite.

If Node is installed, also run:

```sh
node --check app/static/app.js
node --check tools/browser_check.cjs
```

Node/browser tools are test dependencies, not needed for the running app. The browser checks are included in GitHub Actions; optional local instructions are in [ENGINEERING_REVIEW.md](ENGINEERING_REVIEW.md).

The preceding cleanup passed 136 Python tests with local PostgreSQL and 75 browser checks across Chromium, Firefox and WebKit. Those are local results; check the new commit's GitHub results after pushing.

## 3. Check private configuration and local operation

```sh
python tools/preflight.py
```

Preflight reads settings without contacting OpenAI or opening a database. Check mode, model, backend and schema in its output. Never paste your `.env`, access codes or raw connection string into a public issue.

For a local Supabase test, privately check:

| Local setting | Check |
|---|---|
| `DATABASE_BACKEND` | `supabase` |
| `STORAGE_MODE` | `persistent` |
| `DATABASE_URL` | Your complete IPv4 Session pooler URL, with an encoded password |
| `DATABASE_SCHEMA` | An existing development/pilot schema matching the mode/model; avoid a schema owned by the running Render app |
| `DATABASE_SSLROOTCERT` | `/Users/krown/HCIProj/hci-proj2/phase1-chatbots/private/prod-ca-2021.crt` if this is still the correct downloaded CA |
| `DEPLOYMENT` | `local` |
| `PUBLIC_ORIGIN` | Blank for the default localhost address |
| `CHATBOT_MODE` / model / reasoning | Existing tested settings; live mode requires the configured API key and applicable review acknowledgement |

With your local app stopped:

```sh
python tools/database.py diagnose
python tools/database.py check
```

`diagnose` is a read-only connection/TLS check. `check` also takes the app's schema ownership lock: it cannot share a schema with a running local or Render app. Use a separate initialized development schema, or arrange a quiet stop of its current owner first. Do not suspend a live study service simply to run an optional laptop check.

If `check` says the schema is missing, initialize only the intended development/pilot schema with the schema owner's credentials using the existing [Supabase setup guide](../SUPABASE_SETUP.md). A restricted app role cannot create schemas. If it says older schema/mode/model mismatch, investigate before proceeding; do not erase data or point the app at a different study area to hide the error.

Start the local app:

```sh
python run.py
```

Open the address printed by the server; the default researcher screen is `http://127.0.0.1:8766/admin`. Use **test accounts**, fictional mild topics and the existing first/home/final links. Check sign-in, consent, a chat, Finish and all three ratings. Test a return chat: Fresh has no prior-chat note references; Persistent uses eligible ready notes. Both retain context inside the current conversation.

Stop with **Ctrl+C** afterwards. A laptop and Render must not own the same schema simultaneously.

Optional API-only check:

```sh
python tools/check_api.py
```

This is a dry run. Adding `--execute` makes **six real, potentially billable synthetic API requests**; it does not contact the database. Only run that intentionally with appropriate tested live settings. It does not replace an end-to-end memory test.

## 4. Check that secrets are excluded

```sh
git branch --show-current
git status --short
git ls-files .env private data exports
git check-ignore .env private/prod-ca-2021.crt
```

Expected:

- Branch: `codex/clean-study-workflow`.
- `git ls-files ...` prints nothing. If it lists private runtime files, stop before committing and fix what is tracked; adding an ignore rule alone does not untrack a file.
- `git check-ignore ...` prints those private paths, confirming they are ignored.
- Code, tests, guides, `.env.example` and the public manifest are okay to track. `.env`, actual database files, participant exports, access codes and private certificates/settings are not part of this release.

If a real credential has already been pushed, removing it in a later commit does not remove the exposure; rotate the exposed credential privately and arrange appropriate history cleanup separately.

## 5. Commit and push the cleanup branch

Rebuild the public manifest after all edits:

```sh
python tools/package.py
```

This also regenerates the ZIP outside the repository; do not add that ZIP to this commit.

Stage the public changes:

```sh
git add app tests tools docs .github README.md HANDOVER.md HOW_TO_USE.md STUDY_CHANGES.md STUDY_HOW_TO_USE.md VERIFICATION.md DEPLOY_RENDER_SUPABASE.md MANIFEST.json
git diff --cached --name-only
git diff --cached --check
```

Review the staged files and changes in your editor or GitHub Desktop. Ensure no private runtime files appear. Then:

```sh
git commit -m "Clean up study workflow, responsive UI, recovery and team guides"
git push -u origin codex/clean-study-workflow
```

Use that explicit first push: this new branch currently tracks `origin/v2`. The `-u` command switches its upstream to the matching cleanup branch. Do not force-push or push the unreviewed cleanup directly over `v2`.

## 6. Review, check and merge into v2

1. Open the repository on GitHub → **Pull requests → New pull request**.
2. Set **base = `v2`**, **compare = `codex/clean-study-workflow`**.
3. Describe the UI/recovery/database-query/data-tool changes and link the engineering review.
4. Wait for the latest commit's checks: `test` plus browser jobs for Chromium, Firefox and WebKit. All must pass. A skipped PostgreSQL suite is not the desired full CI result.
5. Have a teammate review the changes, then merge the pull request into `v2`. If GitHub reports conflicts, resolve and rerun checks before merging; do not force the merge.
6. Wait for the merged `v2` commit's checks and record its commit SHA for deployment.

GitHub Actions does not need your real API key, Supabase URL or CA certificate. Its database and providers are synthetic/disposable.

Optional local synchronization after merging:

```sh
git switch v2
git pull --ff-only origin v2
```

Run that only after the cleanup is committed/merged and your working tree is clean.

## 7. Verify the existing Render service settings

Open the existing **Web Service → Settings**. Verify:

| Setting | Value for this repository |
|---|---|
| Repository | `linhtetaung-mm/chatbot-hci` |
| Branch | `v2`, after the merge and checks above |
| Runtime | Python |
| Root directory | Blank: `app/`, `requirements.txt` and `gunicorn.conf.py` are already at this repository's root |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn -c gunicorn.conf.py app.server:application` |
| Health check path | `/health` |
| Instances | `1` |
| Auto-Deploy | Off during the study |
| Persistent disk | Not required when Supabase holds the data |

The Gunicorn file already specifies one worker and 16 threads. Do not add a second worker or start another service against the same schema.

Keep your existing hosting plan for this release. If it is Free, account for idle startup delays in testing: free web services spin down after inactivity. Supabase persistence does not keep Render awake. Validate the team's chosen hosting arrangement before unsupervised participant access. [Render free-service documentation](https://render.com/docs/free).

Use the existing service's manual settings. The root `render.yaml` describes an older temporary preview. The optional `render.supabase.yaml` describes the Supabase configuration, but it neither uploads the certificate nor automatically rewrites all settings on an existing manually configured service.

## 8. Check the certificate and Render environment

**Certificate:** Environment → Secret Files. If absent, add Filename `prod-ca-2021.crt` and paste the full contents of the CA certificate, including BEGIN/END lines. Render mounts it at `/etc/secrets/prod-ca-2021.crt`. Do not use the Mac path there. Saving a secret file can trigger deployment, so do this during the quiet release window. [Render secret files](https://render.com/docs/configure-environment-variables#secret-files).

**Environment variables:** enter/check values individually; do not blindly import your laptop `.env`.

| Variable | Value / check on Render |
|---|---|
| `PYTHON_VERSION` | The known working pinned runtime; the existing Supabase Blueprint pins `3.12.8`. Do not depend on Render's creation-date-dependent default. |
| `DEPLOYMENT` | `render` |
| `DATABASE_BACKEND` | `supabase` |
| `STORAGE_MODE` | `persistent` |
| `DATABASE_URL` | Complete private Session pooler URL, including the encoded database password; port `5432` |
| `DATABASE_SCHEMA` | Exact initialized schema for this release: the pilot area for team testing, or the approved live area for real collection. Preserve its name if already in use. |
| `DATABASE_SSLROOTCERT` | `/etc/secrets/prod-ca-2021.crt` |
| `CHATBOT_MODE` | `live` for actual AI with its existing review requirements; `demo` for scripted practice, in a matching separate schema |
| `OPENAI_API_KEY` | Existing valid key, entered privately |
| `OPENAI_MODEL` | Exact already-tested model matching the chosen schema |
| `OPENAI_REASONING_EFFORT` | Existing tested value; `none` only when supported by the selected model |
| `ADMIN_KEY` | Existing strong secret, at least 24 characters; retain it unless intentionally rotating |
| `RESEARCHER_CONTACT` | Actual reachable team contact |
| `SUPPORT_CONTACTS` | Actual reviewed support text, not placeholders |
| `DELETE_DATE` | Actual agreed retention date |
| `HUMAN_TEST_REVIEW` | `confirmed` only when the applicable requirements have actually been met |
| `SESSION_HOURS` | `168` unless the approved existing configuration differs |
| `MIN_GUIDED_MESSAGES` | `6` unless the approved existing configuration differs |
| `DATABASE_LOCK_WAIT` | `90` for the current hosted handover behaviour |

The Session pooler supports IPv4. Use the actual pooler host/username supplied by Supabase; encode reserved characters in the password. This application requires verified TLS. [Supabase connection instructions](https://supabase.com/docs/guides/database/connecting-to-postgres). Render requires a fully specified version when setting `PYTHON_VERSION`; see [runtime-version documentation](https://render.com/docs/python-version).

Current code defaults for request/chat limits:

| Variable | Default |
|---|---:|
| `TESTER_DAILY_API_LIMIT` | 80 |
| `GLOBAL_DAILY_API_LIMIT` | 800 |
| `GLOBAL_TOTAL_API_LIMIT` | 3000 |
| `TESTER_MINUTE_API_LIMIT` | 6 |
| `GLOBAL_CONCURRENT_API_LIMIT` | 12 |
| `TESTER_DAILY_CHAT_LIMIT` | 6 |

If the team already configured different agreed limits, preserve and document them. Do not change the study's limits just to match this table. Check remaining allowance, not just the configured cap: stored usage counts survive deployments, and failed/summary attempts count. These limits are attempt caps, not an exact spending cap in currency.

Also check:

- [ ] No stale localhost `PUBLIC_ORIGIN`. Leave unset/blank for Render's detected HTTPS hostname, or use the exact custom-domain HTTPS origin with no path.
- [ ] Do not override Render's supplied `PORT` with laptop value `8766`.
- [ ] `CHATBOT_DB` is unnecessary for Supabase; do not put a URL in it.
- [ ] No stale `RENDER_EXTERNAL_HOSTNAME` override copied from another service; Render supplies its own value.
- [ ] No real `HCI_TEST_POSTGRES_URL` on Render; it is a test-only variable.
- [ ] No conflicting values in linked environment groups. A service-level value overrides the same key in a group; avoid duplicate definitions across groups.

Local `.env` edits and GitHub pushes do not update dashboard secrets. With **Save only**, values apply on the next deployment. **Save and deploy** applies them to the current build; **Save, rebuild, and deploy** also rebuilds. A runtime-version change needs a rebuild. [Render environment settings](https://render.com/docs/configure-environment-variables).

## 9. Deploy the checked v2 commit

1. Confirm the merged `v2` commit is green in GitHub Actions.
2. Confirm no participant session or laptop process owns the deployment schema.
3. If you used Save only for settings, deploy after all required values and the certificate are present.
4. In Render → **Manual Deploy → Deploy latest commit**. Confirm the displayed SHA matches the merged `v2` SHA you recorded. If the branch has advanced unexpectedly, deploy the specific checked commit instead.
5. Watch Events/Logs for successful build and startup. Do not share raw logs containing credentials.
6. Give database handover time on the first authenticated request. The current app waits up to 90 seconds for the previous copy to release the schema lock. This is not a promise that every request continues uninterrupted.

The old guide's blanket claim that every update requires stopping the service predates the lock-wait fix. Use a quiet manual deploy and verify it. If ownership errors persist, identify an old/local/second service still holding the schema; do not remove the lock or repeatedly deploy over it.

**Restart service does not apply saved environment changes or fetch new code.** It reuses the running commit and configuration. Use the deployment actions above to apply this release. [Render deployment behaviour](https://render.com/docs/deploys).

## 10. Hosted acceptance checklist

Use synthetic test accounts in the pilot area first.

- [ ] `/health` returns `ok: true` with the intended mode. This is liveness only; it does not prove database/API readiness.
- [ ] `/admin` opens; sign-in succeeds; displayed mode/backend/storage/model are correct.
- [ ] A test account signs in on a separate browser or device; the admin secret is never shared.
- [ ] Consent → pre-chat rating → chat → Finish → all three ratings works.
- [ ] First and final links keep the existing minimum-message requirement. The plain link starts a home chat.
- [ ] Reassure and Guide behave as already validated, with the same neutral participant interface.
- [ ] A later Persistent chat has the expected eligible note references; Fresh always has none. First-chat zero references are expected in both.
- [ ] A retry does not duplicate the saved exchange; unanswered messages have a recovery path.
- [ ] Stop works while a reply is pending; a late reply does not reopen the stopped chat.
- [ ] Lost-code replacement works on a test account and retains its records/condition.
- [ ] Two devices can chat concurrently without seeing each other's records.
- [ ] Phone layout, keyboard use, rating scales and sign-out work on real devices.
- [ ] Chat CSV and JSON downloads are readable and correspond to the test records.
- [ ] During a quiet controlled redeploy/restart, the same test account's records and Persistent notes remain available afterward.
- [ ] Request allowances and pause switch are understood; expected usage fits the remaining allowance.
- [ ] Before actual participants, the team has the required procedure review, accurate consent/privacy/support materials, approved external forms and a completed supervised pilot.

A successful deployment is not completion of the experiment or evidence that the hypotheses are true.

## 11. Roll back if needed

Keep participants off the app while resolving a failed release. Redeploy the previous known working commit using **Deploy a specific commit**, preserving its matching environment/schema configuration. A code rollback does not restore deleted data or automatically restore settings: verify both. This cleanup has no new schema migration, but do not roll back to pre-study-schema code against a study-schema database. Do not delete tables, change memory assignments or clear quotas to make a rollback start.

After recovery, repeat the hosted acceptance checks and record the final active SHA, schema, mode and test results.
