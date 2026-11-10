-- Study version (schema 2). Run by tools/database.py init (new schema) or migrate (existing schema 1).
-- Adds fixed 2x2 assignment, memory condition, chat type and in-app ratings. Existing rows are kept.
ALTER TABLE testers ADD COLUMN IF NOT EXISTS study_id TEXT;
ALTER TABLE testers ADD COLUMN IF NOT EXISTS memory TEXT NOT NULL DEFAULT 'persistent' CHECK(memory IN ('persistent','fresh'));
ALTER TABLE testers ADD COLUMN IF NOT EXISTS locked INTEGER NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX IF NOT EXISTS testers_study_id ON testers(study_id) WHERE study_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS assignments(study_id TEXT PRIMARY KEY,seq INTEGER UNIQUE NOT NULL,style TEXT NOT NULL CHECK(style IN ('reassure','guide')),memory TEXT NOT NULL CHECK(memory IN ('persistent','fresh')),scenario TEXT NOT NULL CHECK(scenario IN ('A','B')),tester_id TEXT REFERENCES testers(id) ON DELETE SET NULL,assigned DOUBLE PRECISION);
CREATE TABLE IF NOT EXISTS chat_meta(conversation_id TEXT PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,chat_type TEXT NOT NULL CHECK(chat_type IN ('first','home','final')),pre_distress INTEGER CHECK(pre_distress BETWEEN 0 AND 100),post_distress INTEGER CHECK(post_distress BETWEEN 0 AND 100),support_needed INTEGER CHECK(support_needed BETWEEN 1 AND 7),felt_understood INTEGER CHECK(felt_understood BETWEEN 1 AND 7),rated DOUBLE PRECISION);
ALTER TABLE assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_meta ENABLE ROW LEVEL SECURITY;
