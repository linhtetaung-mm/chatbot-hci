"""Local SQLite/RAM repositories; remote repository is selected explicitly."""
import sqlite3,os,threading
from pathlib import Path
from contextlib import contextmanager,closing
SCHEMA='''
CREATE TABLE IF NOT EXISTS api_attempts(id INTEGER PRIMARY KEY,tester_hash TEXT NOT NULL,kind TEXT NOT NULL,started REAL NOT NULL,finished REAL,status TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS api_attempt_time ON api_attempts(started);
CREATE INDEX IF NOT EXISTS api_attempt_tester ON api_attempts(tester_hash,started);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS testers(id TEXT PRIMARY KEY,code_hash TEXT UNIQUE NOT NULL,created REAL NOT NULL,consent REAL,active_style TEXT NOT NULL CHECK(active_style IN ('reassure','guide')),suspended INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,tester_id TEXT NOT NULL REFERENCES testers(id) ON DELETE CASCADE,style TEXT NOT NULL CHECK(style IN ('reassure','guide')),status TEXT NOT NULL CHECK(status IN ('open','completed','stopped','discarded')),started REAL NOT NULL,ended REAL,model TEXT NOT NULL,prompt_version TEXT NOT NULL,prompt_json TEXT NOT NULL,memory_refs TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS one_open ON conversations(tester_id,style) WHERE status='open';
CREATE INDEX IF NOT EXISTS retrieval ON conversations(tester_id,style,ended DESC);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,seq INTEGER NOT NULL,role TEXT NOT NULL CHECK(role IN ('user','assistant')),text TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('pending','success','failed')),request_id TEXT NOT NULL,created REAL NOT NULL,model TEXT,usage TEXT NOT NULL DEFAULT '{}',flags TEXT NOT NULL DEFAULT '',UNIQUE(conversation_id,seq),UNIQUE(conversation_id,request_id,role));
CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY,conversation_id TEXT UNIQUE NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,status TEXT NOT NULL CHECK(status IN ('pending','ready','failed','excluded')),notes TEXT,schema_version TEXT NOT NULL,model TEXT,prompt_version TEXT NOT NULL,created REAL NOT NULL,error TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,tester_id TEXT REFERENCES testers(id) ON DELETE CASCADE,conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,event TEXT NOT NULL,created REAL NOT NULL,detail TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS logins(hash TEXT PRIMARY KEY,tester_id TEXT REFERENCES testers(id) ON DELETE CASCADE,role TEXT NOT NULL,style TEXT,expires REAL NOT NULL);
'''
# Study version (schema 2): fixed 2x2 assignment, memory condition, chat type and in-app ratings.
# Applied automatically to new and existing SQLite/RAM databases; existing rows are kept.
STUDY_MIGRATION=[
 "ALTER TABLE testers ADD COLUMN study_id TEXT",
 "ALTER TABLE testers ADD COLUMN memory TEXT NOT NULL DEFAULT 'persistent' CHECK(memory IN ('persistent','fresh'))",
 "ALTER TABLE testers ADD COLUMN locked INTEGER NOT NULL DEFAULT 0",
 "CREATE UNIQUE INDEX IF NOT EXISTS testers_study_id ON testers(study_id) WHERE study_id IS NOT NULL",
 "CREATE TABLE IF NOT EXISTS assignments(study_id TEXT PRIMARY KEY,seq INTEGER UNIQUE NOT NULL,style TEXT NOT NULL CHECK(style IN ('reassure','guide')),memory TEXT NOT NULL CHECK(memory IN ('persistent','fresh')),scenario TEXT NOT NULL CHECK(scenario IN ('A','B')),tester_id TEXT REFERENCES testers(id) ON DELETE SET NULL,assigned REAL)",
 "CREATE TABLE IF NOT EXISTS chat_meta(conversation_id TEXT PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,chat_type TEXT NOT NULL CHECK(chat_type IN ('first','home','final')),pre_distress INTEGER CHECK(pre_distress BETWEEN 0 AND 100),post_distress INTEGER CHECK(post_distress BETWEEN 0 AND 100),support_needed INTEGER CHECK(support_needed BETWEEN 1 AND 7),felt_understood INTEGER CHECK(felt_understood BETWEEN 1 AND 7),rated REAL)",
]
SCHEMA_VERSION='2'
class LocalConnection(sqlite3.Connection):
    def begin_serialized(self):self.execute('BEGIN IMMEDIATE')

class Storage:
    def __init__(self,path,mode,model):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.initialize(mode,model)
        os.chmod(self.path,0o600)
    def initialize(self,mode,model):
        with self.connect() as db:
            db.executescript(SCHEMA)
            current=db.execute("SELECT value FROM settings WHERE key='schema'").fetchone()
            if current is None or current[0]=='1':
                columns={r[1] for r in db.execute('PRAGMA table_info(testers)')}
                for statement in STUDY_MIGRATION:
                    if statement.startswith('ALTER TABLE testers ADD COLUMN') and statement.split()[5] in columns:continue
                    db.execute(statement)
                db.execute("INSERT INTO settings(key,value) VALUES('schema',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(SCHEMA_VERSION,))
            for k,v in {'schema':SCHEMA_VERSION,'mode':mode,'model':model}.items():
                old=db.execute('SELECT value FROM settings WHERE key=?',(k,)).fetchone()
                if old and old[0]!=v:raise ValueError('Database mode/model/schema differs. Preserve it and select a new CHATBOT_DB filename.')
                db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO NOTHING',(k,v))
            # A terminated process cannot leave an active network operation behind.
            db.execute("UPDATE messages SET status='failed' WHERE status='pending'")
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15,factory=LocalConnection);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA busy_timeout=15000')
        try:yield db;db.commit()
        except Exception:db.rollback();raise
        finally:db.close()
    def backup(self,destination):
        target=Path(destination)
        if target.exists():raise ValueError('Choose a new backup filename.')
        target.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as source,closing(sqlite3.connect(target)) as dest:
            source.backup(dest);dest.commit()
        os.chmod(target,0o600)

class MemoryStorage(Storage):
    """Same repository interface, process RAM only: never opens a database file."""
    def __init__(self,mode,model):
        self._lock=threading.RLock()
        self._db=sqlite3.connect(':memory:',check_same_thread=False,factory=LocalConnection)
        self._db.row_factory=sqlite3.Row
        self._db.execute('PRAGMA foreign_keys=ON')
        self._db.execute('PRAGMA temp_store=MEMORY')
        self.initialize(mode,model)
    @contextmanager
    def connect(self):
        with self._lock:
            try:yield self._db;self._db.commit()
            except Exception:self._db.rollback();raise
    def backup(self,destination):
        raise ValueError('Backups are disabled for temporary team testing.')
    def close(self):
        with self._lock:self._db.close()


def create_storage(cfg):
    if cfg.get('database_backend','sqlite')=='supabase':
        from .postgres import PostgresStorage
        return PostgresStorage(cfg)
    if cfg.get('storage_mode')=='temporary':return MemoryStorage(cfg['mode'],cfg['model'])
    return Storage(cfg['db'],cfg['mode'],cfg['model'])
