# API setup checklist

The adapter is already implemented in `app/provider.py`. There is no need to replace it with a consumer ChatGPT page or another API endpoint. It calls OpenAI's `/v1/responses` endpoint using server-side bearer authentication.

## While waiting for a key

Keep `CHATBOT_MODE=setup` and `OPENAI_API_KEY=PASTE_YOUR_OPENAI_API_KEY_HERE` in private `.env`. Run the app to inspect both interfaces and researcher controls. Chat sending is disabled; no personal-support reply or memory is fabricated. The separately selected `demo` mode is only a simulator.

## Activate later

1. Create an API account/project, set up billing and a modest budget/alerts, and create a project key through the official API platform. Account creation/payment is the team's action.
2. Paste the key privately into `.env`, replacing the entire placeholder. Never paste it into group chat or the browser interface.
3. Set `CHATBOT_MODE=live`; confirm the model/settings, real researcher contact, support contacts, deletion date and applicable human-test review acknowledgment.
4. Leave `CHATBOT_DB` blank to use a fresh live database. Keep setup/demo data separate.
5. Stop and restart the app. Run preflight, then the optional synthetic six-call API check described in the README. No automatic test is run just because a key is present.
6. Inspect replies and summaries for accuracy and clear style separation; review several topics and follow-up messages. Run the supervised usability test and record the results separately.

## Failures

- A blank/example/placeholder key cannot be used in live mode and is not sent to OpenAI.
- Authentication failures identify the key issue without printing the key or raw error body.
- Model/permission errors identify the configured model or project access issue.
- Usage/rate limits require checking project credit/limits rather than repeatedly retrying.
- API failures never silently replace a live response with a demo reply.

The software can check syntax/settings and parse responses; only a real account request can establish current access. Only actual review/testing can establish whether the responses are suitable for the project.
