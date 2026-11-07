# Temporary preview and future storage

`STORAGE_MODE` is independent of `CHATBOT_MODE`:

- `temporary` (default): process RAM only, no filesystem database. Real responses are still available with `CHATBOT_MODE=live`.
- `persistent`: existing SQLite repository and three-chat memory behavior. Live/setup/demo data must use separate database filenames.

`Chatbot` chooses `MemoryStorage` or `Storage`. Both implement `connect()` with the existing schema and transaction contract. `MemoryStorage` uses one `:memory:` SQLite connection protected by a reentrant lock; temporary SQLite work is configured to use RAM. The SQL repository boundary is preserved for a future backend, but PostgreSQL is not a drop-in configuration change: SQL, transactions, migrations and concurrency would need adaptation and verification.

Temporary state includes tester IDs/code hashes, sessions, current chat messages, in-process quota metadata and administration state. It is not written to a chat database file. As with any process, this does not claim control of operating-system swap, infrastructure diagnostics or API-provider retention.

Finish deletes the conversation/messages and generates no summary. Stop/discard deletes the chat, including while a reply is pending. Sign-out deletes that tester's chats/events and resets consent. Active-chat inspection remains available to researchers. Exports and backups are rejected server-side. Tab closure alone is not a deletion signal. State can remain in process RAM until explicit clearing or process termination. The deployment runs a single process; new processes start empty.

Saved-memory retrieval returns no notes in temporary mode. Current conversation history still goes to the model so it can respond coherently. No change is made to the Reassure/Guide system prompts. This implementation is a UI/support-style preview, not a Fresh/Persistent experimental comparison.

Cost counters do not survive restart. Finishing/deleting a chat does not reset its process-local API count or new-chat count. Use provider-side spending controls as the independent guard. Do not use a database switch/restart as a workaround for the study's budget.

Persistent storage remains available, but is off by default. Existing local files are preserved untouched; this update does not migrate, export or delete them. Before enabling persistent records, agree on access, consent/privacy wording, retention and backup procedures as well as the database provider.
