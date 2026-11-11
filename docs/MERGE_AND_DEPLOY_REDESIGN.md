# Merge the redesign and deploy it

Use the existing repository. The working branch is `codex/study-experience-redesign`; the deployment branch is `v2`. The changes are currently local and uncommitted. This guide does not perform a push, merge, or deployment.

## 1. Check the work you are about to save

Open Terminal in the project folder:

```sh
cd /Users/krown/HCIProj/hci-proj2/phase1-chatbots
git branch --show-current
git status --short
git diff --stat
```

The branch should be `codex/study-experience-redesign`. Review the changes in your editor. Do not switch to `v2` with the redesign still uncommitted: uncommitted changes can follow you across branches.

## 2. Check the application and public package

```sh
.venv/bin/python -m unittest discover -s tests -v
node --check app/static/app.js
node --check tools/browser_check.cjs
.venv/bin/python tools/package.py
git diff --check
```

PostgreSQL integration tests require a disposable test database, not `hci_live`. Browser check instructions are in `ENGINEERING_REVIEW.md`; the fixture uses synthetic records and does not read `.env` or call OpenAI. Recheck after resolving any merge conflicts.

## 3. Commit on the redesign branch

Stage the public project files, then inspect what was staged:

```sh
git add .env.example MANIFEST.json README.md app docs tests tools
git diff --cached --name-only
git diff --cached --check
git ls-files .env private data exports
```

The last command must print nothing. Never add the private reset backups, connection settings, certificates, exports, or database files. The ZIP generated in the parent directory is a separate downloadable package, not a file to add to this repository.

After reviewing:

```sh
git commit -m "Redesign study experience and add configurable enrollment and allocation charts"
```

## 4. Bring the latest v2 into the redesign branch

```sh
git fetch origin
git merge origin/v2
```

Run these while still on the redesign branch. This incorporates teammates' latest `v2` work before review. If Git reports conflicts, resolve the marked files, review both sides, stage the resolutions, and complete the merge with `git commit`. Rerun the relevant checks and regenerate the manifest after resolving conflicts. If you cannot resolve the merge, `git merge --abort` returns to the pre-merge state; it is not a replacement for saving your work first.

## 5. Push and open a pull request

```sh
git push -u origin codex/study-experience-redesign
```

On GitHub, open a pull request with:

- Base: `v2`
- Compare: `codex/study-experience-redesign`
- Description: participant/researcher redesign, prompt version change, admin-defined settings, on-demand enrollment, allocation charts, access restrictions, and recorded validation.

Wait for the current commit's tests and browser checks. Have a teammate review the intervention changes and pilot evidence. Merge the PR into `v2` when ready. Do not force-push over `v2` or open the PR against a different deployment branch by accident.

## 6. Synchronize your local deployment branch

After the GitHub merge and with a clean working tree:

```sh
git switch v2
git pull --ff-only origin v2
git rev-parse HEAD
```

Save the final commit SHA. It identifies exactly what should be deployed. Do not run a second local merge after GitHub has already merged the PR.

## 7. Prepare the existing Render service

In the service's Settings, verify:

| Setting | Expected value |
|---|---|
| Repository | Your existing `chatbot-hci` repository |
| Branch | `v2` |
| Root directory | Blank for this repository layout |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn -c gunicorn.conf.py app.server:application` |
| Health check | `/health` |
| Instances / Gunicorn workers | One instance, one worker |
| Auto-deploy | Off while piloting/releasing to participants |

Keep existing private database/API credentials and verified TLS certificate settings. For the current live deployment, the intended database settings are `DATABASE_BACKEND=supabase`, `STORAGE_MODE=persistent`, and the confirmed `DATABASE_SCHEMA=hci_live`. Do not copy a laptop certificate path or local port onto Render. Named researcher accounts are optional and configured privately through `RESEARCHER_ACCOUNTS_JSON`.

Changing local `.env` or pushing code does not update Render's Environment values. If you change hosting settings, use the appropriate save/deploy action. Restart alone does not fetch a new commit or apply newly saved environment values.

The database reset has already been performed for the targets confirmed in this chat. Do not run it again as a deployment step. No new schema migration is required by configurable enrollment; it uses existing tables and settings.

## 8. Deploy the checked commit

Choose a quiet period with no participant session. Stop local apps/tools using the same Supabase schema.

In Render, select **Manual Deploy → Deploy a specific commit**, then choose/paste the checked merged `v2` SHA. Watch the build/startup result. Confirm the reported running SHA matches. Use the existing verified Python runtime and secret-file setup.

## 9. Configure and rehearse the clean study

1. Open `/health`, then sign in at `/admin`. A healthy page alone is not a database/provider check.
2. Open **Allocation**. Enter distinct labels and enrollment targets for all four support × memory combinations. Save the plan. Use equal targets for the intended balanced design; these targets are caps, not randomization weights.
3. Under **Settings & testing**, enter the agreed participant instructions and questionnaire URLs. The reset removed previous app-level settings.
4. Use team test accounts and fictional topics to check consent, ratings, pause/resume, archives, and memory boundaries. Do not enroll fictional accounts as main-study participants just to populate the real allocation charts.
5. Test a real phone and two separate accounts/devices. Verify Fresh receives no old notes and Persistent receives only eligible own notes. Recheck the new prompt behavior in the reviewed pilot.
6. Verify exports and restart persistence. Check the correct external forms and unaided-task procedure separately.
7. For actual enrollment, open **Participants → Create participant**. The default assigns a randomized setting and creates an ID/code immediately; no unused-ID list is required. Save the code privately.
8. Use **Allocation** to see counts and filter the roster by setting. This page reveals conditions and is restricted to administrators.

If more clean-up is needed after a pilot, request and review that reset separately. Deployments must not silently erase records.

## 10. If deployment fails

Keep participants off the app while investigating. Redeploy a previous known working commit if necessary, preserving the matching environment configuration. Code rollback does not restore reset data or undo changed app settings. Pre-reset recovery files are private and require a separate deliberate restore; never import them just to make an empty graph look populated.

## References

- Git branching and merging: https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging
- Render deploys and specific commits: https://render.com/docs/deploys
- Render environment settings: https://render.com/docs/configure-environment-variables
