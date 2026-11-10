# Data and reporting guide

This guide explains the existing exports and preparation tools. It does not select new outcomes, scoring rules, exclusions or statistical tests. Follow the approved analysis plan and preserve original records.

## 1. Save the source files

Use a restricted, dated folder, for example `private/exports/run-2026-11-18/`:

- `chats.csv`: **One row per chat (CSV)** from the researcher screen.
- `records.json`: **All records (JSON)** from the same screen. It includes enrolled accounts with no chats, conditions, transcripts, summaries and events. It excludes access-code hashes and login tokens.
- `baseline.csv` and `final.csv`: downloads from the corresponding Google Form response sheets.
- The approved scoring rubric, analysis plan and material versions.

Both app downloads disclose conditions. Keep them away from blind coders. The JSON is a portable record export; this app does not implement an automatic JSON-to-database restoration command. Keep the database's existing backup/recovery arrangement separate.

Do not edit source files to fix an inconvenient result. Record genuine ID corrections and deviations in a separate log. Import free-text CSV columns as **text** in spreadsheet software so participant text is not interpreted as a formula.

## 2. Make the blind-coding file once

From the project folder:

```sh
python tools/combine_data.py blind \
  --final private/exports/run-2026-11-18/final.csv \
  --out private/analysis/run-2026-11-18
```

The script recognizes scenario-answer headers containing “Imagine this happened”, including separate A/B branches. Each participant must have exactly one non-empty scenario answer. If the headers differ, use the exact `--answer-column` name. Use `--id-column` or `--scenario-column` if automatic matching is ambiguous or the scenario letter needs an explicit column. Check that the exported `scenario` column identifies the assigned scenario before coding; the script does not infer a scenario from the answer's wording.

The script uses the existing **last exported response per normalized study ID** rule for duplicate forms, with a warning. Preserve all originals and review that warning against the approved duplicate-response policy. This engineering update has not established a new policy.

Outputs:

| File | Who receives it |
|---|---|
| `coders_scenarios.csv` | Each blind coder, as a separate copy; contains code, scenario and answer |
| `coders_key.csv` | Data coordinator only; links the random code to study ID |

Do not regenerate or replace a key once coders receive the file. The script refuses to overwrite either coding file. A genuinely separate run needs a new output folder and its own clearly labelled key.

Each coder scores independently using the existing 0–3 rubric. Keep the other coder's scores hidden until both independent sets are recorded. The coordinator merges by `code`, not row order, and creates a private `scored.csv` containing `code,coder1,coder2,final`. Retain both original scores when the agreed `final` score is added. Do not let a disagreement discussion overwrite the independent scores.

## 3. Combine the files

```sh
python tools/combine_data.py combine \
  --chats private/exports/run-2026-11-18/chats.csv \
  --participants private/exports/run-2026-11-18/records.json \
  --baseline private/exports/run-2026-11-18/baseline.csv \
  --final private/exports/run-2026-11-18/final.csv \
  --scores private/analysis/run-2026-11-18/scored.csv \
  --key private/analysis/run-2026-11-18/coders_key.csv \
  --out private/analysis/run-2026-11-18
```

Before coding is complete, omit `--scores` and `--key` to check joins. Re-running `combine` replaces its derived `chat_level.csv` and `person_level.csv`, not the source exports or coding key. Keep a dated output folder for each analysis snapshot.

`--participants` accepts the all-records JSON or an enrolled-participant CSV with `study_id,style,memory` (optionally `locked`). Use the JSON for completeness. Unassigned IDs and team test accounts are excluded from its enrollment roster; withdrawn records already deleted from the app are absent, so the restricted recruitment/withdrawal log remains necessary for the participant-flow report.

## 4. Check the outputs

- `chat_level.csv`: completed study chats only. A completed chat may still have missing ratings; check blanks. Stopped, discarded and open chats are not included in this completed-chat table.
- `person_level.csv`: includes enrolled people with zero chats when the roster is supplied. Form-only IDs remain visible with an unknown condition; verify them rather than inventing an assignment. Counts separate finished, stopped/discarded and open chats.
- Test accounts are excluded from the study tables. Do not expect pilot test accounts to appear in the combined sample.
- `distress_change = post_distress − pre_distress`; negative means a lower post-chat rating. A missing rating stays missing, not zero.
- `notes_used` counts saved-note references frozen into a chat. Fresh should have zero; Persistent's first chat also has zero. Later Persistent chats can have zero when no eligible notes are ready. Review memory-failure events and report deviations.
- Rating fields and scenario scores must remain within their existing scale ranges. The tool rejects non-integer or out-of-range coder scores instead of truncating them.
- Technical caps, outages and safety pauses can constrain voluntary use. Report these interruptions rather than interpreting blocked usage as a participant preference.
- The printed coder statistic is **unweighted Cohen's kappa**, a descriptive check. With no marginal variation it is undefined, even if exact agreement is 100%. Use the reliability method specified in the approved plan for the report.
- Printed condition means use participants who completed a final chat. They are descriptive complete-final-chat summaries, not treatment-effect estimates or hypothesis tests.

Resolve `CHECK` warnings and document missingness before analysis. The script cannot verify the questionnaire items, reverse-scoring or scale calculations in external forms; it preserves those columns for the analyst. It does not implement the entire approved statistical analysis.

## 5. Write the findings accurately

Use the approved analysis plan. Repeated chats from one person are not independent participants; the chat table is not permission to treat every row as a separate person. Account for the study's actual design and unit of analysis.

Report recruited/enrolled/withdrawn/completed counts, group sizes, missing forms/ratings, actual chat exposure and memory failures. Keep the planned and actual procedures distinguishable. Present estimates and uncertainty as specified in the plan, including null or contrary findings. Do not invent significance, a power calculation or a completed recruitment target.

Link claims to the [success and construct boundaries](SUCCESS_CRITERIA.md). Immediate relief is not itself proof of long-term resilience; voluntary chatbot use is not itself a diagnosis of AI dependency. Include methodological limitations and the appropriate literature in the final report.
