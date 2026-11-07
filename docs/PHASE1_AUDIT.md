# Phase 1 audit and completion status

Audit updated: 4 November 2026. Original software audit: 3 November 2026. Scope: local Reassure and Guide chatbots with separate persistent memory and at least one supervised usability test. Deployment and the full participant experiment are outside this audit.

**Current status: Live AI works in team testing, as confirmed by the project owner on 4 November; Phase 1 is not yet complete.** The owner confirms a real API key and conversations with both styles. Only team testing has taken place. The latest prompt revision, live summaries/recall and an external supervised usability session still need recorded review. The key and private transcripts were not inspected or reproduced in this documentation update. See the current PROJECT_TASK_GUIDE for the full plan.

## Historical software audit on 3 November

The existing 49 tests passed. The app already contained an OpenAI Responses API adapter, explicit system/user/assistant messages, separate memory filtering, structured summaries and private storage. The screenshot's repeated reply matched the simulator's generic fallback. It did not show how a live model would respond. More prompt text or another canned variation would not solve the absence of a connected model.

## Necessary updates made

| Finding | Update |
|---|---|
| Default demo could be mistaken for a usable support chatbot | Default setup mode now shows API not connected and disables generation. Demo remains an explicit simulator option. |
| Empty key slot did not make the future activation step obvious | Added `PASTE_YOUR_OPENAI_API_KEY_HERE` in public/private configuration; live-mode and adapter guards reject placeholder values. |
| Generic API errors made diagnosis difficult | Added actionable authentication, permission/model, usage-limit and configuration errors without exposing raw provider bodies. |
| Old API diagnostic exercised only one summary | Expanded the opt-in synthetic check to both styles' replies, summaries and return replies, with a private receipt. |
| There was no concise evidence-based Phase 1 checklist | Added this audit, a key-activation checklist and a blank usability record. No human findings were fabricated. |
| Resource cleanup was incomplete | Closed SQLite backup destinations and HTTP error responses explicitly; reran tests with ResourceWarnings treated as errors. |

The working configuration was moved from demo to setup only because its key was confirmed absent. The researcher secret, existing settings and saved records were preserved. Automatic mode-specific databases keep setup/demo/live records separate.

## Completion gates

- [x] Local app, named styles, system/user roles and separate persistent memory implemented.
- [x] Ownership/isolation, last-three recall, retry, restart, correction/reset/deletion and web boundaries verified automatically.
- [x] Placeholder key is never submitted; setup mode cannot create an AI exchange or summary.
- [x] Earlier browser checks verified both styles' simulator flows. Current placeholder screen checked separately; see VERIFICATION.md.
- [x] Real API access and both styles tested, as reported by the project owner on 4 November; not a new independently observed account check.
- [ ] Exact live model/settings recorded and the optional synthetic diagnostic receipt reviewed if used.
- [ ] Latest prompt version retested in new live chats for context, nonrepetition, short/uncertain replies, follow-through and natural closure. Earlier team conversations do not by themselves verify this revision.
- [ ] Live summaries inspected for invented details, identifiers and attribution; both styles' later chats use only their own recent notes.
- [ ] Researcher contact, support route, retention dates, consent and applicable course review confirmed before a human test.
- [ ] At least one consenting adult completes a supervised usability test of both styles and repeated-chat memory; results recorded using the template.
- [ ] Problems are fixed/retested and a short progress summary reports actual observations and remaining limits.

A successful unit suite or six-call diagnostic is not proof that these unchecked gates have been met. Keep main-study recruitment and deployment in Phase 2.

## Suggested live test coverage

Use mild or fictional scenarios: vague bad day, direct request for comfort, exam disappointment, delayed reply, neutral greeting, good news and a correction to remembered information. Include follow-ups such as “I don't know”, “you tell me”, and a topic change. Check that the bot responds to the latest message, avoids assumptions, varies phrasing, stays in style and stops appropriately. Run separate fictional keyword tests with the team rather than asking a participant to disclose crisis experiences.

For one person's prototype test, both styles can be tried in separate conversations. That does not change the later experiment's between-participant design or establish causal effects.

## Documentation reconciliation on 4 November

The current guide includes memory and named styles in Phase 1, uses the standalone port-8766 app, records live team testing, and leaves outside usability testing and the full experiment outstanding. The existing 56 tests passed again with ResourceWarnings treated as errors. No new API calls or participant session were performed for this update.
