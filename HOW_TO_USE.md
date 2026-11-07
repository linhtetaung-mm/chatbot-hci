> **Current free preview:** `STORAGE_MODE=temporary` does not save chat history or memory between chats. Follow [DEPLOY_RENDER.md](DEPLOY_RENDER.md). The persistent-memory instructions below apply only when persistent storage is deliberately enabled.

> **Hosted team testing:** follow [DEPLOY_RENDER.md](DEPLOY_RENDER.md). The local instructions below remain available. On Render, the researcher secret is in Environment settings, not a shared `.env` file.

# How to use the Phase 1 chatbots

## 1. Who uses it and where

A researcher runs the program on a laptop. The tester uses that same laptop during a supervised session. Both chatbots remember their own past conversations with that tester; neither receives the other chatbot's notes.

For now, there is no public link or remote participant website. Do not send the localhost address expecting someone on another device to access your laptop. Give team members the clean ZIP so they can run their own separate copy, or use your laptop for the test. Separate computers have separate databases and do not synchronize.

## 2. Start the program

1. Open Terminal in the `phase1-chatbots` folder.
2. First time only: run `python3 setup_local.py`.
3. Open the newly created `.env` file privately. Copy `ADMIN_KEY` for researcher sign-in.
4. Run `python3 run.py`.
5. Open **http://127.0.0.1:8766/admin** in a browser.
6. Keep the terminal open. Ctrl+C stops the app, but does not erase saved records.

Default mode is **setup**. It shows an API-not-connected placeholder and disables chat sending until a real key is configured. Choose `CHATBOT_MODE=demo` explicitly only for simulated interface/storage practice. Follow the README's live settings before testing actual AI support or memory quality with a person. The live app requires an API key, real researcher contact and review acknowledgment. Set actual support contacts and retention dates before a human test.

## 3. Researcher creates a tester

1. Sign in with the private `ADMIN_KEY`.
2. Press **Create private access code**.
3. Save the generated tester ID and access code in your private scheduling notes. The code is shown only once. Use no real name in the chat database.
4. In **Open a chatbot for a tester**, choose the tester and **Reassure** or **Guide**.
5. Press **Open tester screen**. You are now signed in as that tester, not as the researcher.
6. Hand over the laptop only after the tester screen appears. Keep researcher screens, assignments and raw notes private.

A tester may alternatively open **http://127.0.0.1:8766/** and enter their private code. The researcher-selected chatbot is used. In setup mode, the interface is available but Send is disabled; do not treat this as an AI conversation. Only the researcher can change their selected style; changing a request or conversation URL cannot gain access to another style's records.

## 4. Tester starts and finishes a conversation

1. Read and confirm the consent statements. You can decline and leave.
2. Press **Start or resume chat**.
3. Discuss a mild or fictional everyday situation. Avoid names, contact details, serious distress or traumatic experiences.
4. Type a message and press **Send**. Wait for the reply before sending again.
5. When finished, press **Finish chat**. This saves the completed chat and prepares remembered notes. Live summary generation may take a few moments.
6. You can view the saved transcript and press **New chat**. Open **Chats → Previous chats** to view or resume earlier chats. Up to three recent finished same-chatbot summaries are used for recall.

**Refresh / Resume:** reopens the same unfinished conversation. It is not a new memory episode. Signing out does not finish the conversation automatically.

**More → Stop conversation:** ends the chat without creating recall notes. It remains available while waiting for a reply. A late model reply is not added after Stop.

**More → Discard unfinished chat:** closes an incomplete conversation without creating notes. Its transcript remains in the private record. Discard is different from deleting data.

**More → Correct a remembered detail:** choose that form, choose the earlier source, and enter a correction. The earlier note is excluded, and the correction appears in this conversation. The chatbot can use it on the next reply. Corrections do not silently rewrite original transcripts.

## 5. Demonstrate memory with one tester

Use this sequence for a supervised usability test, not as proof of experimental effects:

1. Researcher selects **Reassure** for tester T. Tester completes a short chat about a mild or fictional topic, such as a postponed group presentation, then presses Finish.
2. Sign out. Researcher signs in at `/admin`, selects the **same tester** and **Guide**, then opens the tester screen.
3. Complete a different mild or fictional chat, such as a delayed lunch reply, and finish.
4. Sign out. Researcher returns the same tester to Reassure. Start a **new** conversation and revisit the presentation topic. It can use only Reassure's notes.
5. Repeat with Guide and revisit the lunch topic. It can use only Guide's notes.
6. Restart the program and repeat a return chat to verify saved memory persists.

For the three-note window, complete four short conversations within one style, then start a fifth. In researcher inspection, the fifth conversation should list only the newest three eligible source memory IDs. Older transcripts remain stored but are not automatically sent for recall.

In scripted practice, “remember” / “last time” / “again” / “earlier” triggers a simple saved-note excerpt for demonstration. This is deliberately a scripted storage exercise. Real AI recall, relevance, factual accuracy and support style must be evaluated in live mode.

## 6. Researcher reviews notes and failures

Sign out and reopen `/admin`, then sign in with `ADMIN_KEY`. Open **Saved conversations** to see tester, style, completion state and note status. Export, reset and deletion are under **Data tools**.

- **Inspect** shows the automatically generated summary, source transcript and selected memory IDs/prompt version.
- **Retry summary** is available when notes are pending or failed. A completed conversation is preserved even if summary generation fails.
- **Download private records** exports transcripts, summaries and metadata. It excludes access-code hashes and login tokens. The export still contains personal content; store it privately and never upload it to GitHub.
- **Reset one chatbot's remembered notes** requires typing `RESET MEMORY`. It closes that tester/style's open chat and excludes its earlier notes. The other style and other testers are unaffected; retained transcripts are not erased.
- **Delete a tester** requires typing `DELETE TESTER`. It removes both histories and access from this database. Also remove applicable exported files/backups yourself under the disclosed retention policy.

A safety stop pauses the tester's access to both styles. Do not create another account just to bypass it. Speak with the tester and follow the agreed instructor/researcher support procedure. The app does not claim to provide emergency care, and keyword detection is incomplete.

## 7. Common problems

| Problem | What to do |
|---|---|
| Address already in use | Another copy is running. Open its page or stop its terminal with Ctrl+C. This app defaults to port 8766 to avoid the older app's 8765. |
| Wrong page or host error | Use `http://127.0.0.1:8766/` or `/admin`, rather than `localhost`. If PORT changed, use the printed port. |
| Invalid access code | Researcher uses ADMIN_KEY at `/admin`; tester uses their generated tester code at `/`. Do not confuse the two. |
| No ready memory | Finish the earlier conversation. Inspect note status. If failed/pending, researcher retries the summary. Open/stopped/discarded chats do not produce notes. |
| API request fails | Check account billing, key and model availability privately. Retry the same saved message. No canned live reply is substituted. |
| Model/mode differs from database | Preserve the old database. Leave CHATBOT_DB blank for automatic demo/live separation, or choose a new filename. Never delete the old data to bypass this check. |
| A message is marked not yet answered | Retry the saved message with its original text; do not append a different message first. Or discard the unfinished conversation. |
| Chat reaches 20 messages | Finish it and start a new conversation. Its validated summary can be recalled later. |
| Tester code is lost | Existing codes are stored only as hashes. Do not guess or share a different person's code. For a prototype, create a new clearly separate tester and log the interruption. |

If the app is stopped, run it again with the same settings. Data remains in its database; browser sessions expire after 12 hours and may require sign-in again.

## 8. Share the complete project safely

Run `python3 tools/package.py`. Share the resulting `phase1-chatbots.zip` found **beside** this folder. Every teammate extracts it and runs `setup_local.py` to create their own private secret. They supply their own authorized API key to use live mode.

Do not share `.env`, `data/`, private exports, backup files, tester codes or your researcher secret. The packaging tool excludes runtime records. To transfer an actual study database between authorized researchers, use a separate private agreed channel and retention procedure; it is not part of the general shareable project.

## Updated interface and prompts

The name at the top tells you which chatbot you are using: **Reassure** offers comfort; **Guide** helps you think it through. They have separate histories and notes. Their green/blue accents distinguish them visually. Researchers select the style before opening the tester screen.

The main chat screen contains messages, a text box, Send, Finish chat and More. Press Enter to send or Shift+Enter for a new line. Less frequent actions and memory corrections are in More; previous conversations are under Chats. Creating a tester, saved-conversation inspection and data tools expand only when needed on the researcher page.

If a response seems unrelated, first check the mode line. **Demo** means simulated examples, not AI understanding. Every simulated response also says “demo”. The richer prompts only affect live model responses. Configure live mode through the README to test general conversation quality.

Restart the server after updating the code. Start a New chat to use the latest prompts. New chat saves an answered open conversation and its notes first; an empty chat is discarded. An unresolved failed message must be retried or discarded before switching. The previous transcript remains available. Older prompt snapshots are not silently rewritten.

## Checking conversation follow-through

The live prompts now ask both bots to lead the current conversation with a focused follow-up, including when the tester says “I don’t know”. Reassure leads through comfort and feelings; Guide narrows the reflection so the tester can form their own perspective or next step. Restart the server and use **New chat** to apply this prompt version.

For each style, try this short check in live mode:

1. Start with “I am having a bad day. How can I feel better?”
2. Reply “I don’t know. Can you lead?” The bot should make the next reply easier rather than repeat its question or ask you to choose the whole topic.
3. Supply a concrete concern, then answer its follow-up briefly. Check that it uses that detail and moves forward, without inventing facts or switching support styles.
4. Say “Thanks, that’s enough for now.” It should close naturally without another probing question.

These are manual response-quality checks, not automated proof. Demo uses fixed examples and does not evaluate these live instructions.

## API placeholder and Phase 1 status

The public `.env.example` contains `OPENAI_API_KEY=PASTE_YOUR_OPENAI_API_KEY_HERE`. This is not a working key. On a new installation, keep `CHATBOT_MODE=setup` while waiting. Preserve an existing private live key; do not replace it with this placeholder. The setup screen makes no AI replies or summaries; previously saved demo records remain in their separate database.

When you obtain a key, follow [API_SETUP.md](docs/API_SETUP.md). Stop and restart the server after editing settings, reload the browser and start a new chat. Do not merely change the model name or make prompts longer to try to repair a disconnected model.

Before calling Phase 1 complete, use [the audit checklist](docs/PHASE1_AUDIT.md) and record at least one actual supervised human test using [the blank template](docs/USABILITY_TEST_TEMPLATE.md). Store the completed template privately, not beside its public blank copy. The new API diagnostic makes six opt-in synthetic calls and does not replace that human test.

## Progress update on 4 November 2026

The project owner confirms both styles were tested with Live AI and a real key. Only team testing has taken place; the external supervised test remains pending. Use [PROJECT_TASK_GUIDE.md](docs/PROJECT_TASK_GUIDE.md), or its Word copy, for the complete status, remaining work, five-member roles and Phase 2 procedure.
