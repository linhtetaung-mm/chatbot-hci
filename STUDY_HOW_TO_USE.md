# How to use the study chatbot

Part A is for the research team. Part B is for participants (you can copy it into the information sheet or a message).

---

# Part A: Research team

## A1. What the study looks like

| When | Where | What happens |
|---|---|---|
| **First session** | With a team member (in person or video call) | Consent → Baseline Google Form → enroll → participant signs in on their own phone/laptop → **first chat** (at least 6 messages) → three questions |
| **Free use** (about 4 days) | Anywhere | Participant chats whenever they like, as often as they like. Each chat: slider before, chat, three questions after. No fixed days and no reminders to chat. |
| **Final session** | With a team member | **Final chat** (at least 6 messages) → three questions → Final Google Form (scenario task with the chatbot closed) → next-step choice → debrief |

Everyone sees the same "Chatbot". The condition (Reassure/Guide × Persistent/Fresh) is fixed at enrollment and never shown.

## A2. Settings (`.env` locally, or Render Environment)

| Setting | Study value |
|---|---|
| `CHATBOT_MODE` | `live` for the real study, `demo` for practice without OpenAI |
| `STORAGE_MODE` | `persistent` (never `temporary` for the study) |
| `DATABASE_BACKEND` | `supabase` |
| `OPENAI_MODEL` | one model for the whole study, e.g. `gpt-6-luna` |
| `RESEARCHER_CONTACT` | team email or LINE that participants can use |
| `SUPPORT_CONTACTS` | `Thailand Mental Health Hotline 1323 (24 hours) · AIT student counselling: <verified contact>` |
| `HUMAN_TEST_REVIEW` | `confirmed` only after the instructor has approved the study |
| `SESSION_HOURS` | `168` (participants stay signed in for 7 days) |
| `MIN_GUIDED_MESSAGES` | `6` |
| Limits | leave the defaults (3000 total, 800 per day) and set a spending limit in the OpenAI dashboard |

## A3. Database (one time)

- **New Supabase schema:** `python3 tools/database.py init`
- **Existing schema from before 10 Nov:** `python3 tools/database.py migrate` (keeps all records; the app will not start on the old schema)
- Check: `python3 tools/database.py check`, then `python3 tools/database.py self-test --mode demo`
- Local SQLite databases upgrade themselves when the app starts.

## A4. Make and load the assignment list (one time, before the pilot)

```sh
python3 tools/assignments.py generate --n 48      # writes private/assignments.csv; use a multiple of 4
python3 tools/assignments.py load private/assignments.csv
python3 tools/assignments.py status               # e.g. "0 of 48 study IDs used, 48 left"
```

- Every 4 IDs contain all 4 conditions, so the groups stay balanced as long as IDs are used in order.
- `private/assignments.csv` shows the conditions. Keep it private; do not open it during sessions and never give it to the coders.
- If you need more IDs later, generate a second file with a different name and `--prefix Q`, then load it.

## A5. Test accounts and pilot

1. Open `/admin` and sign in with `ADMIN_KEY`.
2. **Test accounts** → choose style and memory → **Create test account**. Make one for each of the 4 conditions.
3. Test accounts are marked `test_account = 1` in exports and are not part of the sample. Only test accounts can be switched to another condition or have their memory reset.
4. For the pilot, run the whole flow with each test account: first chat (`/?visit=first`), two or three home chats (`/`), final chat (`/?visit=final`). Check that the Persistent accounts sometimes refer back to earlier chats and the Fresh accounts never do.

## A6. First session, step by step

1. Consent sheet, then the Baseline Google Form (first question: study ID; fill it in after step 3).
2. In `/admin`, press **Enroll the next participant**. Copy the box into the private booking sheet:
   - Study ID (e.g. P07), access code (e.g. `K7MP-Q2XA`), final-form scenario (A or B).
3. Send the participant, on their own device:
   - the **first session link** `https://<app>/?visit=first`
   - their access code
   - the **use-any-time link** `https://<app>/` (for chatting at home)
4. They sign in, tick the consent boxes, move the slider, and chat. **Finish chat** unlocks after 6 messages. Then they answer three questions.
5. Tell them, in the same neutral words every time: "You can use the chatbot whenever you like until our next meeting, as much or as little as you want."
6. Book the final session about 4 days later.

Never pick a study ID for a person, never re-enroll someone to get a different condition, and do not reuse the IDs of people who withdraw.

## A7. During free use

- Check `/admin` → **Participants** at least morning and evening. **paused (safety)** means a crisis word was typed or the model gave the safety reply. Contact that person the same day using the booking sheet, check in kindly, give the support contacts, and inform the instructor. Paused accounts cannot chat again.
- The column **Finished chats: first / home / final** shows how much each person has used the chatbot. Do not remind people to chat.
- **Saved conversations → Inspect** shows any chat and its memory notes. Failed notes are retried automatically when the person starts their next chat; you can also press **Retry summary**.
- **AI usage and pause switch** stops all AI replies at once if something goes wrong.

## A8. Final session

1. Send the **final session link** `https://<app>/?visit=final`. If they are signed out, they use the same access code.
2. Final chat (at least 6 messages) → three questions.
3. They close the chatbot tab. Final Google Form: manipulation checks → scenario task (A or B from the booking sheet) → questionnaires.
4. Next-step choice, then debrief.

If someone wants to use the chatbot on a lab device instead of their own: in `/admin`, **Open a participant's chat screen**, choose the study ID, and sign out afterwards.

## A9. Withdrawal and data

- Withdrawal: `/admin` → **Data downloads and deletion** → choose the person → type `DELETE TESTER`. This removes all their chats, notes and ratings. Their study ID is not reused.
- Analysis download: **One row per chat (CSV)**. Full backup: **All records (JSON)**. Both contain conditions: store privately and never share with the blind coders.
- Main measures in the CSV: `distress_change` (after − before; negative = feeling better), `support_needed`, `felt_understood`, number of `home` chats per person (voluntary use), `notes_used` (memory actually given to the model).

## A10. Common problems

| Problem | What to do |
|---|---|
| "Invalid access code" | Check the code in the booking sheet; letters can be typed in lower case, with or without the dash. |
| "Please answer how upset you feel before starting." | The participant must move or confirm the slider and press **Start chat**. |
| Finish chat is greyed out | In first/final sessions, 6 messages are needed. At home, at least 1. |
| "Please wait a minute…" | Per-minute limit; wait and press **Try again**. |
| "This chat is paused" | Safety pause. Follow A7. |
| App slow to open | Free hosting sleeps when idle. Open the app yourself a few minutes before each session. |
| App refuses to start: "older schema" | Run `python3 tools/database.py migrate` once. |

---

# Part B: Participants

**What you need:** your phone or laptop, the link and the access code we sent you.

**Signing in:** open the link and type your access code (for example `K7MP-Q2XA`; capital letters and the dash are optional). You stay signed in for 7 days on that device.

**Each time you chat:**
1. Think of something mildly stressful from your day or week (study, a group project, friends, family, roommates). Please do not share real names or anything very serious.
2. Move the slider to show how upset you feel about it, then press **Start chat**.
3. Chat as long as you like. Press **Finish chat** when you are done. In the two meetings with us, the button appears after 6 messages.
4. Answer three quick questions. That's it.

**Between our two meetings** you can use the chatbot whenever you like, as much or as little as you want, using the link we gave you.

**Stopping:** press **Stop** at any time. You can also stop taking part in the study at any time by telling us; we will delete your chats.

**If you feel very distressed:** the chatbot is an AI and nobody reads the chats live. Please contact the Thailand Mental Health Hotline **1323** (24 hours) or AIT student counselling, and let us know.

**Problems signing in?** Contact the research team using the details on your information sheet.
