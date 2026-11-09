# Experiment readiness review

9 November 2026 | Reassure or Guide | Source: current `phase1-chatbots`, original proposal, later project task guide, previous validity audit, and current provider documentation.

## Decision

**Do not start the main experiment with the present temporary deployment.** It is a useful team preview, but lacks durable study records, enforced four-condition assignment, and the required measurement/stage workflow. Passing software tests is not evidence of style separation or participant readiness.

The owner confirmed on 9 November: retain the 2×2 between-participant design, one assigned condition per person, four required chats on Days 1/3/5/7, and no existing Supabase account. The final visit remains first visit +6 days, ±1 day. Earlier two-chat wording in the original proposal is superseded for operations and must be revised in submitted materials. This review does not create a Supabase account or connect a live database.

### Evidence boundary

84 current tests passed again, including disposable real Gunicorn servers in temporary and persistent modes. These use scripted/mocked AI; no billable API calls, secrets or private transcripts were used. This review did not inspect Render Environment or observe its currently deployed commit. The latest supplied screenshot showed setup mode. The code has a real API adapter, but current live deployment operation still needs verification.

## 1. Prompt assessment

Shared rules correctly preserve actual conversation context, constrain invented facts, distinguish examples from user history, encourage focused follow-through, respect closure, keep approximate length/warmth matched, and separate current user turns from saved context. Both style profiles are supplied as system instructions, not just labels in the UI. Style examples are illustrative, and old conversations freeze their prompt versions. These are strengths.

| Dimension | Reassure should do | Guide should do |
|---|---|---|
| Shared foundation | Accurate acknowledgment, warmth, continuity, one useful follow-up | Same |
| Main mechanism | Emotional validation, comfort and acknowledgment of explicitly stated effort | Help the user generate evidence, alternative perspectives or an actionable step |
| Ownership | Bot supplies comfort, not a verdict about other people's motives | Participant supplies the substantive interpretation/solution |
| Follow-up | Feelings, events or whether comfort fits | One manageable thinking step anchored in the user's response |
| Exclude | Alternative-explanation/evidence drills, guarantees, unsupported agreement | Bot-written reframes, leading verdicts, endless questioning |
| Memory | Recall relevant reported context without endorsing it as fact | Recall only genuinely user-stated/endorsed insights as the user's own |

### Specific weaknesses and recommended revisions

1. **Reassure says to affirm feelings “or interpretation.”** This can invite agreement with an unverified accusation despite the later uncertainty rule. Replace it with: “Validate the feeling and why the situation matters to the user. Do not affirm that an unverified interpretation or accusation is true.” Do not reward unsupported agreement in fidelity coding.
2. **The original proposal and current treatment differ.** The proposal says Reassure agrees with the user's view; the implemented bot explicitly avoids unsupported agreement. Keep the safer comfort-versus-guided-reflection treatment and revise the proposal, hypotheses and conclusions accordingly. This does not test unconditional agreement or sycophancy as a pure manipulation.
3. **Reassure can give a small comforting action; Guide elicits an action.** This is not automatically contamination. Distinguish who generates the substantive step and whether it functions as immediate comfort versus reasoning/planning. State that distinction explicitly. Do not interpret all discussion of action as Guide behavior.
4. **Guide can stall when a participant cannot generate an answer.** Preserve the ban on supplying a ready-made reframe, but allow neutral process scaffolds: choose one moment, identify the thought, separate observed facts from an assumption, then ask one smaller question. Do not invent the user's thought or offer two leading explanations that effectively supply the reframe.
5. **Early vague-topic replies can legitimately overlap.** Both bad-day examples begin by clarifying the situation. Require separation over eligible substantive turns once details are available, not artificially different greetings or a reappraisal question in every turn.
6. **Follow-through is shared, which is appropriate.** Keep a focused next turn in both; assess interrogation, repetition and appropriate closure equally. Do not make Guide longer, colder or harder to answer merely to make it distinct.
7. **The shared ban on suggesting human contact except for safety is too categorical.** It can conflict with constructive coping or a user who already wants to ask for help. Permit discussion of user-raised appropriate human support equally in both styles, while retaining the ban on encouraging repeated chatbot use. Decide and freeze this before data collection.
8. **Automatic safety wording assumes a researcher is immediately available.** The independent Day 3/5 chats need truthful availability wording and an approved incident procedure. A keyword regex is not a comprehensive risk detector; it can both miss risk and trigger on a fictional quotation. Do not claim clinical screening.
9. **Summary instructions and validator disagree.** The system asks for “2–3 short sentences” in situation, whereas validation also imposes 700/300/700/700-character field limits that the model is not told. Add those exact limits to the summary prompt and keep the total under 180 words. Valid JSON alone does not ensure faithful, de-identified notes.

These are prompt recommendations, not evidence that any new wording has succeeded. The review pack preserves the active prompts unchanged and supplies a separate candidate file for testing. Do not replace prompts mid-study.

### Behavioral verification before freezing prompts

Use `PROMPT_VALIDATION_CASES.json` with the same model/settings and several independent runs. Include multi-turn histories, resistance to the style, one-word/uncertain answers, topic changes, good news, closure, correction and memory ownership. At least two team members should code outputs independently before discussing disagreements. Mask condition names where feasible; coders may still infer style from the text, which is part of the manipulation.

Code warmth, comfort, user-generated reflection elicitation, bot-supplied reframe, unsupported assertion, next-turn relevance, repetition, question count, word count and safety override. Separate eligible problem-processing turns from greetings, clarification and closure. Example provisional pilot criteria: at least 80% of eligible outputs show the intended dominant behavior; no observed unsupported accusation/guarantee or cross-user leak; no persistent opposite-style behavior across follow-ups. These are team acceptance targets, not published validation thresholds or guarantees. Report all runs, then freeze a prompt version/hash and returned model ID for collection. A model change requires revalidation.

## 2. Four experimental conditions

| Assignment | Current-chat context | Earlier-chat notes |
|---|---|---|
| Reassure Fresh | Full successful current chat | None |
| Reassure Persistent | Same | Up to last three eligible completed same-person chats |
| Guide Fresh | Same | None |
| Guide Persistent | Same | Up to last three eligible completed same-person chats |

Fresh does not mean no transcript storage: all conditions need equivalent research records and consent. It means no earlier-chat content in the model request. The participant's own memory of previous conversations cannot be removed. Prompt caching is not the manipulation.

Generate summaries after completed treatment chats in all four groups if retaining the latest guide's equal data-handling rule. In Fresh, never retrieve them for replies. Log the actual note IDs included in each generation, not merely the assigned label. First chats have no prior study notes in either memory group; distinguish first-chat style effects from later memory contrasts. Optional chats can enter/displace the rolling three-chat window; decide this policy before collection, apply it identically across groups, and log required versus optional exposure.

The current schema has no fixed memory assignment. Starting persistent-mode chats retrieves notes regardless of a Fresh condition. Admin handoff/assign can change style. Add immutable main-study assignment, enforce it server-side, prohibit researcher convenience switches, and maintain a separate test/pilot environment. Use a concealed randomized block list; do not hand-pick conditions. Do not reassign withdrawals to improve group outcomes.

## 3. Database recommendation

**Recommend Supabase Free PostgreSQL, accessed only by the Python server.** It fits the related records, constraints and transactions already in the design and provides a dashboard for the student team. Current Free database allowance is 500 MB; low activity over a week may pause a project. Size and availability must be monitored, not assumed. See [pricing](https://supabase.com/pricing) and [pausing](https://supabase.com/docs/guides/platform/free-project-pausing).

| Option | Assessment |
|---|---|
| Supabase Free | Recommended managed relational store; separate from Render's ephemeral files; requires a real PostgreSQL adapter and backups |
| Neon Free PostgreSQL | Credible alternative, especially if only database hosting is wanted; includes scale-to-zero/compute limits; switching provider does not avoid the adapter work. [Official plan information](https://neon.com/blog/neon-free-plan-1-gb-per-project) |
| Render Free PostgreSQL | Avoid for the study archive: expires after 30 days, incompatible with assuming records remain until the current December retention date. [Render limits](https://render.com/docs/free) |
| Google Sheets as primary chat store | Not recommended: poor fit for atomic lifecycle, ownership and retry constraints; keep Forms/Sheets for questionnaires, coordination and controlled exports |
| Local SQLite | Viable for controlled on-site sessions with protected local storage/backups; not a durable database on Render Free and does not itself solve independent remote sessions |

Supabase does not give the model memory automatically. Our backend selects bounded, relevant notes and includes them in model input. No vector database or embeddings are required for a last-three-chat rule. Keep the full consented transcript as research data; send only the current chat and allowed prior notes to OpenAI, not the entire database.

Required records: participant/condition, consent version/answers/time, session schedule/type/status, ordered messages, memory notes/source/versions/exclusions, generation receipts/actual note IDs, outcomes/Form linkage, API quota reservations and incidents. Keep recruitment contacts separate. Supabase raw chat records should not become shared public Sheets.

See `SUPABASE_SETUP_AND_MIGRATION.md` for account setup and the migration checklist. The existing SQLite code cannot connect just by changing its filename to a connection URL. SQL syntax, parameter binding, row access, key generation, conflict handling, locks and schema migrations need a deliberate port and integration tests.

## 4. Render and participant experience

**Keep the existing web interface and Python application.** Render is its hosting service, not a separate participant tool or login they must learn. Participants need only your public app link and private code. Rebuilding in a messenger, a shared ChatGPT account or a different UI framework would add substantial work and can weaken assignment, logging or access control.

The supplied screenshot is `/admin`, the researcher screen. Never send that screen or its password to participants. The participant route is `/`. The participant screen is already much smaller but still needs study-specific simplification:

1. Same neutral title (“Study Chatbot”), styling, greeting and layout for all four conditions. Remove Reassure/Guide names, explanatory subtitles and distinct style colours from participant views. Do not falsely tell people all configurations are identical; approved consent can disclose differing configurations without revealing the prediction. Explain the manipulation in debrief.
2. Private code → information/consent → current required visit → pre-rating → chat → post-ratings → finished/next-visit message. Use a single obvious next action at each step.
3. Keep Stop/help continuously visible. Move transcript/history browsing and advanced memory/reset tools out of the treatment interface. Agree access to personal records separately, consistently across groups.
4. Show visit/day and technical status, not model names, internal IDs, memory IDs or admin controls. Provide a clear recovery message if disconnected; avoid forcing new enrollment or changing condition.
5. Baseline/final Google Forms remain possible. Use a stable verified study ID, record version/submission linkage, prevent silent duplicate joins, and never put condition in participant-facing links or coder files. Manual researcher reconciliation is acceptable if documented; an elaborate automated Sheets integration is not a prerequisite.

**Render Free is a preview platform, not a reliable default for unattended participant collection.** Its own docs say not to use Free instances for production; it sleeps after 15 minutes and loses local files at restart. With Supabase, data can survive but slow starts, request interruption and downtime still affect exposure and dropout. [Render documentation](https://render.com/docs/free).

Preferred practical compromise: free Supabase database plus an always-on Render compute instance during collection, if the team can fund hosting. A paid app server does not require buying database storage. If strictly zero hosting budget, consider instructor-provided always-on university hosting; otherwise scope the free service to closely supervised scheduled sessions after a successful reliability pilot and explicit acceptance of its limitations. That may not match independent Day 3/5 access. Do not switch to a different free host merely assuming it has no limits.

## 5. Concrete launch blockers

| Priority | Finding | Evidence / completion criterion |
|---|---|---|
| Blocker | Temporary deployment discards research chats and notes | `config.py`, `MemoryStorage`, `finish()`; durable DB must survive redeploy, logout, sleep, and reconnect |
| Blocker | No immutable four-condition enforcement | `storage.py`, `start()`, `assign()`; test all cells and forged switches |
| Blocker | No required-chat schedule/stage or pre/post measurement flow in standalone app | Task guide requirements versus current routes; demonstrate complete Days 1/3/5/7 record |
| Blocker | Procedure/consent/privacy approval remains unconfirmed | Latest known response was proposal feedback only; obtain applicable determination, not merely an environment flag |
| Blocker | No current recorded live style/memory fidelity pilot | 84 software tests pass, but do not establish actual AI behavior |
| Blocker | Team-demo request ceilings are unsuitable | `limits.py`/Blueprint total 500 and app daily 250; set study budget/caps from pilot receipts |
| High | Independent-chat safety and support availability | Regex plus exact model phrase are brittle; approve contacts, availability, pause/incident route, skip/stop and response process |
| High | Participant interface reveals treatment and exposes advanced controls | `static/app.js`; neutral presentation, visible Stop, stable assignment |
| High | Full versioned informed consent and withdrawal/deletion workflow | Four checks and a timestamp do not capture approved information version, follow-up tasks, storage recipients, cutoff or optional quotations |
| High | Outcome data and coding protocol incomplete | Forms/IDs, distress scoring, unaided task, scenario balance, blinded coder files, two-rater initial scores and missingness rules |
| High | Restore, concurrency and interruption unverified on external PostgreSQL | Existing tests cover SQLite/RAM, not the proposed deployed DB |
| High | Documents disagree | Original proposal: two chats and interpretation endorsement; latest guide: four chats and bounded comfort; current README: temporary preview. Publish one current study protocol |

### Request-budget calculation

The later guide proposes minimum participant messages of 6, 4, 4, 6 over the four required chats. If each generates one reply and every chat generates one summary in all conditions: (6+4+4+6+4) × 48 = **1,152 API attempts** before optional chats, retries or any longer conversations. The present total allowance of 500 cannot support that design. If all 48 do Chat 1 on the same UTC day, 48 × (6+1) = **336 attempts**, exceeding the app-wide daily allowance of 250. These are request counts, not token/cost estimates or validated exposure minimums. Preserve safety limits but raise them only against a documented budget, provider spend controls, expected schedule and pilot token receipts. Do not silently shorten chats to fit demo quotas.

### Privacy and recovery details to fix

Store consented data, not everything indiscriminately. Define when an incomplete/stopped transcript is retained, whether final optional activity content is discarded, and how withdrawal affects already-exported/de-identified data. Raw narratives remain potentially identifying even after replacing names with study IDs. Providers and access rights must appear in the actual information sheet. Backups require their own retention/deletion policy.

Current summary JSON validation does not verify de-identification or factual fidelity. Inspect synthetic notes against transcripts. Preserve user-versus-bot attribution. The summary provider currently returns validated notes but discards summary-call usage/model receipts, unlike reply receipts; add separate generation metadata for budgeting and audit.

Current SQLite startup marks every pending message failed. With external storage and overlapping old/new deployment processes this could incorrectly change a still-running request. Replace global reset with owned operation leases/expiry and test interrupted/retried writes. Keep one process until cross-process locks and recovery have been deliberately implemented. Persist quota and pause state externally; do not silently fall back to RAM if the database is down.

## 6. Construct validity and analysis

Retain the professor's constraint: immediate 0–100 distress change is immediate self-reported relief; unaided scenario writing is a bounded response-performance task; return intention, voluntary usage and reliance items are distinct indicators. They do not, by themselves, establish psychological resilience, clinical improvement, dependency or addiction. The [Brief Resilience Scale paper](https://pubmed.ncbi.nlm.nih.gov/18696313/) concerns perceived recovery capacity, not the same construct as a single post-chat distress rating.

The unaided rubric rewards reappraisal, which is specifically practiced in Guide. That is useful for the mechanism but does not establish superior coping of every kind. Prespecify blind scoring of alternative explanations, balanced interpretation and constructive action, and acknowledge that acceptance/self-compassion/help-seeking can be adaptive without maximizing this rubric. [Reframing research](https://aclanthology.org/2023.acl-long.555/) motivates this area, not validation of our specific scoring task.

Freeze primary contrasts, scoring, exclusions, required/optional counts and missing-data handling before collection. With 48 people and about 12 per cell, report uncertainty and treat complex interactions cautiously; no power analysis has established adequacy. Four chats do not turn 48 independent participants into 192 independent participants. Model repeated observations accordingly. A final task immediately after Chat 4 measures an immediate unaided response after repeated exposure; it is not isolated delayed retention from Chat 1.

## 7. Execution order and team ownership

1. **Member 1 — protocol and care:** consolidate confirmed four-chat design, review route, participant information/consent/debrief, recruitment/appointments and incident process.
2. **Member 2 — persistence:** create approved Supabase configuration, PostgreSQL adapter/migrations, restricted roles, durable quotas, backup/restore and tested failure handling.
3. **Member 3 — study interface:** immutable allocation, neutral participant flow, stages, visible Stop/help, forms linkage, required/optional exposure and retry/resume.
4. **Member 4 — fidelity and pilot:** synthetic live prompt tests, independent coding, summary accuracy, manipulated-memory checks, device/accessibility/load/restart tests and external supervised pilot after applicable review.
5. **Member 5 — outcomes and report:** Forms/Sheets structure, ID reconciliation, codebook, blind scenario scoring, prespecified analysis and proposal/report corrections. Keep evidence and limitations current.

These roles can work in parallel, but real collection depends on all release criteria. First freeze design and prompts; then implement/storage test; then pilot; fix and freeze the release; only then recruit main-study participants. Do not mix team, synthetic, pilot and study data.

### Calendar warning

Today is 9 November; final submission is 19 November. An 11 November first visit implies a 17 November final visit, with the agreed window 16–18 November. A 12 November first visit pushes that window through submission day. There is little room for recruitment, implementation, pilot, outages, withdrawals, scoring and writing. Discuss feasibility with the professor now; do not quietly shorten follow-up or eliminate review to fit the date. The target of 48 completions is not established merely by inviting 48 people.

## Release gate

A full test participant must progress through all required stages with correct persistent assignment, ratings and memory policy; survive sign-out/restart/redeployment without loss; complete the no-AI task; appear correctly in the analysis export; and be removable according to the reviewed withdrawal policy. Show this on the actual deployment, not only a local mock. Live fidelity/summary review, restricted database access, backup restoration, failure reporting, adequate quotas and applicable participant review must all have documented outcomes. Until then, call this a prototype/pilot build, not experiment-ready.
