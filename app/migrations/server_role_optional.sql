-- OPTIONAL HARDENING: run in Supabase SQL Editor as the schema owner AFTER init.
-- Replace hci_live with the chosen initialized schema (e.g. hci_demo).
-- Replace password placeholder privately. Do NOT save a filled-in copy to Git.
-- This role can read/write study records but cannot create/drop study tables.
-- Only run CREATE ROLE once per Supabase project; later schemas need grants/policies.
CREATE ROLE hci_chatbot_app LOGIN NOINHERIT PASSWORD 'REPLACE_PRIVATELY_WITH_A_STRONG_PASSWORD';
GRANT USAGE ON SCHEMA hci_live TO hci_chatbot_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA hci_live TO hci_chatbot_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA hci_live TO hci_chatbot_app;
CREATE POLICY server_access ON hci_live.settings TO hci_chatbot_app USING (true) WITH CHECK (true);
CREATE POLICY server_access ON hci_live.testers TO hci_chatbot_app USING (true) WITH CHECK (true);
CREATE POLICY server_access ON hci_live.conversations TO hci_chatbot_app USING (true) WITH CHECK (true);
CREATE POLICY server_access ON hci_live.messages TO hci_chatbot_app USING (true) WITH CHECK (true);
CREATE POLICY server_access ON hci_live.memories TO hci_chatbot_app USING (true) WITH CHECK (true);
CREATE POLICY server_access ON hci_live.events TO hci_chatbot_app USING (true) WITH CHECK (true);
CREATE POLICY server_access ON hci_live.logins TO hci_chatbot_app USING (true) WITH CHECK (true);
CREATE POLICY server_access ON hci_live.api_attempts TO hci_chatbot_app USING (true) WITH CHECK (true);
CREATE POLICY server_access ON hci_live.assignments TO hci_chatbot_app USING (true) WITH CHECK (true);
CREATE POLICY server_access ON hci_live.chat_meta TO hci_chatbot_app USING (true) WITH CHECK (true);
-- Then update DATABASE_URL locally: replace postgres.PROJECT_REF username with
-- hci_chatbot_app.PROJECT_REF and use THIS role's password; keep pooler host/port.
-- Stop the owner-backed app first, then run check and repeat synthetic validation.
-- Do not rerun init as this role for a new schema: use the owner for migrations.
-- Future migrations may require additional explicit grants/policies.
