# Phase 1 audit and completion status

Audit date: 3 November 2026. Scope: local Reassure and Guide chatbots with separate persistent memory and at least one supervised usability test. Deployment and the full participant experiment are outside this audit.

**Honest status: the software is ready for API setup and further testing; Phase 1 is not yet complete.** No API key was supplied, no live provider request was verified, and no completed human test record was supplied to this audit.

## What was verified before making changes

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
- [ ] Actual API key/project/billing/model access configured and the opt-in API check completed.
- [ ] Live multi-turn replies reviewed for context handling and nonrepetition across mild topics, including the user's bad-day example and follow-up “I don't know”.
- [ ] Live summaries inspected for invented details, identifiers and attribution; both styles' later chats use only their own recent notes.
- [ ] Researcher contact, support route, retention dates, consent and applicable course review confirmed before a human test.
- [ ] At least one consenting adult completes a supervised usability test of both styles and repeated-chat memory; results recorded using the template.
- [ ] Problems are fixed/retested and a short progress summary reports actual observations and remaining limits.

A successful unit suite or six-call diagnostic is not proof that these unchecked gates have been met. Keep main-study recruitment and deployment in Phase 2.

## Suggested live test coverage

Use mild or fictional scenarios: vague bad day, direct request for comfort, exam disappointment, delayed reply, neutral greeting, good news and a correction to remembered information. Include follow-ups such as “I don't know”, “you tell me”, and a topic change. Check that the bot responds to the latest message, avoids assumptions, varies phrasing, stays in style and stops appropriately. Run separate fictional keyword tests with the team rather than asking a participant to disclose crisis experiences.

For one person's prototype test, both styles can be tried in separate conversations. That does not change the later experiment's between-participant design or establish causal effects.
