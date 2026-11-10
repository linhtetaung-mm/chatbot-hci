# What success means for this project

**Success is a usable, reliable experiment that produces traceable evidence and an honest HCI report.** It does not require Reassure or Guide to win, a significant interaction, or a desired effect of memory.

This document gives operational acceptance checks. It does not change the recruitment target, visit schedule, measures, scoring rules, exclusions or analysis plan.

## Software success

| Area | Evidence of success |
|---|---|
| Access | Each person can use their own code; another person's conversation cannot be opened; participant pages do not reveal the assigned condition. |
| Four conditions | Locked study assignments remain fixed. The same interface and model configuration serve all conditions. Existing prompt-validation cases confirm the intended styles in live pilot testing. |
| Memory isolation | Fresh receives no previous-chat notes. Persistent retrieves only eligible notes for the same participant/style, up to the current three-chat limit. First chats have no earlier notes in either condition. Failures remain observable. |
| Reliable interaction | Sign-in, consent, start, send, finish and ratings work in sequence. Retrying the same message does not duplicate a saved exchange. Stop is available during a pending reply. |
| Device usability | Login, consent, chat, ratings and researcher screens fit narrow phones, tablets and desktops. Inputs remain readable; wide tables scroll within their own area. Keyboard focus and reduced-motion preferences are respected. |
| Saved data | A persistent deployment retains the account, chat, ratings and memory over a service restart. Enrollment cannot happen in the temporary preview. Verify retention on the actual host before collection. |
| Recoverability | The team can identify an interrupted request, retry a summary, export records and locate the correct support/withdrawal procedure without creating a second participant account. |
| Handover | Another teammate follows the team guide and completes a rehearsal without the developer explaining hidden steps. Record the rehearsal and issues. |

Automated local tests establish only the behaviours they exercise. A real phone check and a consented supervised pilot remain evidence needed for the deployed application; they cannot be claimed from screenshots alone.

## Research success

| Question / construct | What the current project can observe | Claim boundary |
|---|---|---|
| Immediate relief | Within-chat change in the 0–100 distress rating, plus the existing post-chat support/understanding ratings | Short-term self-report during this interaction; not a clinical treatment effect or durable resilience measure |
| Coping without AI | The existing final scenario task completed without the chatbot, scored using the approved blind rubric; relevant approved questionnaire measures | Performance on that task and self-reported constructs actually measured; broader resilience needs an explicit theoretical and measurement link |
| Reliance | Existing voluntary home-chat counts, the planned next-step choice and relevant approved questionnaire measures | Behavioural use/preferences in this study; frequent use alone does not demonstrate AI dependency or harm |
| Memory manipulation | Frozen note-reference counts, ready-note status and the existing participant manipulation checks | Whether earlier-chat context was available and perceived; a condition label alone does not prove the manipulation worked |
| Support-style manipulation | Existing prompt checks, transcript review and planned participant manipulation checks | Whether the intended distinction appeared; do not reinterpret failed fidelity as a clean style comparison |

The report should explain how these operational measures relate to the broader constructs in the literature, and state what they cannot establish. Do not relabel a single distress item as a validated resilience scale or usage counts as a dependency diagnosis.

## Data and report success

- Every retained participant can be reconciled across enrollment, chats and forms; zero-chat participants and withdrawals do not silently disappear from the participant-flow account.
- The four group sizes, exposure, missing data and deviations are transparent. Unknown values stay unknown.
- Independent coder scores remain preserved; the coding key stays private; disagreements and reliability are reported using the approved method.
- The analysis follows the approved plan, respects repeated observations and reports uncertainty. Any departure is identified and justified.
- The report describes what was actually built and tested, gives results supported by the data, connects them to the literature, and explains practical HCI implications and limitations.
- Consent/privacy materials have the required review and reflect the actual vendors, stored records, access and retention arrangements. Software flags are not evidence of approval.

A small sample, wide uncertainty or a null result can still support a successful student HCI project when the procedure, data and interpretation are sound. Missing approval, broken condition isolation or untraceable data cannot be repaired by a polished interface or positive findings.
