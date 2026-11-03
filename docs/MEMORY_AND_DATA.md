# Memory and private data

## Recall boundary

One SQLite database holds testers, conversations, messages, memory summaries, events and login sessions. Every conversation has an owner and a fixed `reassure` or `guide` style. A memory belongs to its source conversation; its owner/style cannot be supplied independently by the browser.

A new conversation selects the newest three completed, non-excluded same-owner/same-style source conversations. Pending or failed notes in that window block starting a new same-style chat until the researcher retries. Notes are supplied oldest first, with IDs and source completion times, on each reply request. Existing open conversations keep a recorded selection; reset or correction invalidates notes immediately.

Only the active chat's successful messages and selected summaries are sent to the reply model. Old full transcripts stay available for private inspection, but are not automatically replayed across chats. Messages in other styles or belonging to another tester are not used. Fixed greeting is identical for both. The prototype UI now identifies each chatbot by its actual style name; do not treat this visible-label prototype as a blinded experiment.

## Notes

Notes contain exactly four string fields: `situation`, `feelings`, `user_insights`, `bot_said`. The application checks keys, types, character limits and a total under 180 words. JSON shape checks cannot establish truth. Inspect live notes for invented details, mistaken attribution or identifiers.

The versioned system/style/memory/summary prompts and illustrative examples live in `app/prompts.json`. A new conversation snapshots those prompts and their hash. Its summary uses that same frozen summarizer prompt. Live requests use explicit system/user/assistant roles, and the latest user message is passed unchanged. Changing prompts during development affects new conversations only. Finish produces one summary job per source conversation; failures are explicit and retryable. Reset/deletion during a summary request cannot restore excluded notes.

The “wrong remembered detail” action excludes the selected source note and adds the tester's correction as a distinct user message. This preserves provenance and prevents silent rewriting. It does not automatically identify every wrong note: the researcher/tester must select the source.

## Saving and failure behaviour

Foreign keys are enabled on each SQLite connection. Access is checked by authenticated owner and style, including state, resume, send, finish and corrections. There is at most one open conversation per owner/style. Server locks and unique request IDs prevent duplicate saved turns and memory jobs.

Messages are saved before an API call and marked failed if it cannot produce a complete usable reply. The same pending message may be retried. After app restart, an interrupted pending message becomes retryable. A failed request may still have incurred provider charges; retry prevents duplicate local records, not necessarily duplicate provider work.

Manual Stop, discard, empty chats and safety-stopped conversations do not create memory. Safety keywords are checked before model transmission; flagged text is not sent or copied into an event log. A model response matching the shared safety message also stops access. These rules are incomplete detection, so this prototype requires supervised use.

## Local and provider privacy

Keys live only in private `.env`. The browser receives an HttpOnly, SameSite session cookie; the server stores only its hash. Tester access codes are high-entropy random values stored only as hashes. The researcher key remains private. SQLite files use restrictive file permissions but are not encrypted by the app.

In live mode, messages and selected notes are processed by OpenAI. Responses requests use `store=false` and manually supplied context rather than shared provider conversation IDs. `store=false` does not guarantee zero provider retention; consult [official data controls](https://developers.openai.com/api/docs/guides/your-data). The app does not delete provider logs on your behalf.

Researcher exports omit tester code hashes and session credentials but contain raw private conversation content. Keep exports/backups restricted, off Git, and subject to the consented deletion date. No names are required in the database. Summary instructions omit names, but redaction is not guaranteed: remind testers not to enter identifiers and inspect pilot notes.

## Reset versus deletion

Reset excludes all previous notes for one owner/style and discards its open conversation. It preserves original transcripts for the team's disclosed records. The other style is unchanged.

Delete tester cascades through both styles' conversations, messages, memories, events and login records. Erasing rows is not a promise of forensic erasure of disk pages or backups. The researcher must remove applicable downloaded copies/backups and follow the agreed storage retention procedure. Do not put raw data in general-purpose shared ZIPs.

For a restore rehearsal: stop the app, copy a consistent private backup to a new filename, set CHATBOT_DB to that copy, preserve the same mode/model, start and inspect counts/a test login. Return to the intended database afterwards. Never overwrite the only original.

## Setup mode

Setup mode is an interface placeholder: no message can create an AI exchange or generated summary. It uses its own `chatbots-setup.sqlite3`; demo and live records remain separate. A placeholder value in OPENAI_API_KEY is never sent to OpenAI. Adding a real key later does not automatically import demo notes as live memory.
