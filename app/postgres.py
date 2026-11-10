"""Host-independent, private-schema PostgreSQL repository.

Only parameter markers are adapted to the driver's format. SQL is shared ANSI
SQL; SQLite upserts/IDs/locking were explicitly ported in application code.
One app process owns one session-pooler connection, serialized for short DB work.
"""
import hashlib,re,threading
from pathlib import Path
from contextlib import contextmanager
from collections.abc import Mapping
from urllib.parse import urlsplit,parse_qs

class DatabaseError(ValueError):
    """Safe to display: never contains connection strings or server error text."""

def validate_database_url(value):
    try:
        u=urlsplit(value);port=u.port
        valid=u.scheme in ('postgres','postgresql') and u.hostname and u.username and u.password and u.path not in ('','/')
        if not valid or any(x in value for x in ('[YOUR-PASSWORD]','PASTE_','PROJECT_REF','POOLER_HOST')):raise ValueError()
        if port==6543:raise DatabaseError('Use the Supabase Session pooler on port 5432, not the transaction pooler on 6543.')
        query=parse_qs(u.query)
        if any(k not in ('sslmode','sslrootcert','channel_binding','application_name') for k in query):
            raise DatabaseError('DATABASE_URL contains unsupported options. Copy a plain Session pooler URL.')
        if query.get('sslmode',['verify-full'])[-1] not in ('verify-full',):
            raise DatabaseError('Use sslmode=verify-full or omit sslmode; TLS verification is required.')
    except DatabaseError:raise
    except Exception:raise DatabaseError('DATABASE_URL is missing or invalid. Add the complete private PostgreSQL Session pooler URL; URL-encode the password.') from None
    return value


def connection_error(exc):
    """Classify internally; never expose a raw libpq message/host/username/password."""
    text=str(exc).lower()
    if any(x in text for x in ('certificate verify failed','root certificate','self-signed','certificate validation','certificate has expired')):
        return DatabaseError('Supabase TLS certificate verification failed. Download the CA certificate from Supabase Database Settings > SSL Configuration, then set DATABASE_SSLROOTCERT to its absolute file path. Keep verify-full enabled.')
    if 'does not match host name' in text or 'hostname mismatch' in text:
        return DatabaseError('Supabase certificate hostname mismatch. Copy the Session pooler hostname again and use its matching CA certificate; do not disable verification.')
    if any(x in text for x in ('tenant or user not found','tenant not found')):
        return DatabaseError('Supabase could not identify the pooler user/project. Copy the full Session pooler username and host from Connect; do not use the direct-connection username.')
    if any(x in text for x in ('password authentication failed','authentication failed','wrong password')):
        return DatabaseError('Supabase rejected the database credentials. Check the database password and its URL encoding. This is not your Supabase account password or API key.')
    if any(x in text for x in ('could not translate host name','name or service not known','nodename nor servname','failed to resolve')):
        return DatabaseError('Cannot resolve the Supabase hostname. Check the copied Session pooler host and your network/DNS connection.')
    if 'timeout' in text or 'connection refused' in text:
        return DatabaseError('Supabase is unreachable or timed out. Check project availability, Session pooler port 5432 and network access.')
    return DatabaseError('Cannot connect to Supabase. Check Session pooler URL/password encoding, IPv4, certificate settings and project availability. Connection details were not logged.')


def connection_options(cfg):
    opts=dict(connect_timeout=10,autocommit=True,prepare_threshold=None,row_factory=record_factory,application_name='hci-chatbots')
    if cfg.get('_local_pg_test',False):
        if urlsplit(cfg['database_url']).hostname not in ('localhost','127.0.0.1','::1'):raise DatabaseError('Local test connection must use loopback.')
        opts['sslmode']='disable'
    else:
        validate_database_url(cfg.get('database_url',''))
        cert=cfg.get('database_sslrootcert') or 'system'
        if cert!='system' and not Path(cert).is_file():
            raise DatabaseError('DATABASE_SSLROOTCERT does not point to an existing CA certificate file. Download the certificate from Supabase Database Settings > SSL Configuration and set its absolute path.')
        opts.update(sslmode='verify-full',sslrootcert=cert)
    return opts


def diagnose_connection(cfg):
    """Read-only SELECT 1; no schema/records/locks or secret output."""
    try:
        import psycopg
        with psycopg.connect(cfg['database_url'],**connection_options(cfg)) as conn:
            if conn.execute('SELECT 1').fetchone()[0]!=1:raise DatabaseError('Database read-only check failed.')
    except ImportError:raise DatabaseError('Install requirements.txt to enable Supabase/PostgreSQL support.') from None
    except DatabaseError:raise
    except Exception as exc:raise connection_error(exc) from None

class Record(Mapping):
    def __init__(self,names,values):self.names=names;self.values=values;self.index=dict(zip(names,values))
    def __getitem__(self,key):return self.values[key] if isinstance(key,(int,slice)) else self.index[key]
    def __iter__(self):return iter(self.index)
    def __len__(self):return len(self.index)

def record_factory(cursor):
    names=[c.name for c in cursor.description] if cursor.description else []
    return lambda values:Record(names,values)

def parameters(query):
    """Translate controlled qmark markers only; preserve quoted text and % literals."""
    # The application uses static single-quoted SQL strings, with standard '' escaping.
    parts=re.split(r"('(?:''|[^'])*')",query)
    return ''.join(part.replace('%','%%') if i%2 else part.replace('%','%%').replace('?','%s') for i,part in enumerate(parts))

class Connection:
    def __init__(self,raw):self.raw=raw
    def execute(self,query,args=()):
        return self.raw.execute(parameters(query),args) if args else self.raw.execute(query)
    def begin_serialized(self):pass # connect() already owns an advisory-locked transaction.

class PostgresStorage:
    def __init__(self,cfg,initialize=False):
        self.cfg=cfg;self.schema=cfg['database_schema'];self._lock=threading.RLock();self._raw=None
        if not re.fullmatch(r'hci_[a-z0-9_]{1,48}',self.schema):raise DatabaseError('Invalid private database schema name.')
        self.lock_id=int.from_bytes(hashlib.sha256(('hci-chatbots:'+self.schema).encode()).digest()[:8],'big',signed=True)
        self.initialize_requested=initialize
        self._open()
        try:
            if initialize=='migrate':self.migrate()
            elif initialize:self.initialize()
            else:self.check()
        except Exception:self.close();raise
    def _open(self):
        try:
            import psycopg
            from psycopg import sql
            self._raw=psycopg.connect(self.cfg['database_url'],**connection_options(self.cfg))
            self._raw.execute("SET statement_timeout='20s'")
            self._raw.execute("SET lock_timeout='10s'")
            # One app process per schema. During a Render deploy the old copy keeps the lock for a few seconds
            # until it shuts down, so a hosted app waits for it (DATABASE_LOCK_WAIT) instead of failing at once.
            import time
            deadline=time.monotonic()+float(self.cfg.get('database_lock_wait',0) or 0)
            while not self._raw.execute('SELECT pg_try_advisory_lock(%s)',(self.lock_id,)).fetchone()[0]:
                if time.monotonic()>=deadline:raise DatabaseError('Another chatbot process is using this database schema. Stop it before starting this one. (Usually the Render app, or the app or a tools/ command on a laptop, is already using this DATABASE_SCHEMA.)')
                time.sleep(2)
            self._sql=sql
        except ImportError:raise DatabaseError('Install requirements.txt to enable Supabase/PostgreSQL support.') from None
        except Exception as exc:
            if self._raw is not None:self._raw.close();self._raw=None
            if isinstance(exc,DatabaseError):raise
            raise connection_error(exc) from None
    @contextmanager
    def connect(self):
        with self._lock:
            if self._raw is None or self._raw.closed:self._open()
            try:
                with self._raw.transaction():
                    self._raw.execute(self._sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(self._sql.Identifier(self.schema)))
                    yield Connection(self._raw)
            except Exception as exc:
                # Keep domain errors from the chatbot unchanged; sanitize driver errors only.
                import psycopg
                if isinstance(exc,psycopg.Error):
                    # Log only the error type and SQLSTATE code (no SQL text, data or credentials) to help diagnosis,
                    # e.g. 42P01 = table missing, 3F000 = schema missing, 42501 = no permission, 42703 = column missing.
                    import sys
                    print(f'Database error {type(exc).__name__} sqlstate={getattr(exc,"sqlstate",None)} schema={self.schema}',file=sys.stderr,flush=True)
                    self._raw.close();self._raw=None
                    raise DatabaseError('Database operation failed. No temporary fallback was used. Check connectivity/schema permissions, then retry the original operation.') from None
                raise
    def initialize(self):
        # Explicit admin command only. App startup never runs DDL or global recovery.
        with self._raw.transaction():
            existing=self._raw.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(self.schema,)).fetchone()
            if not existing:
                self._raw.execute(self._sql.SQL('CREATE SCHEMA {}').format(self._sql.Identifier(self.schema)))
                self._raw.execute(self._sql.SQL('REVOKE ALL ON SCHEMA {} FROM PUBLIC').format(self._sql.Identifier(self.schema)))
                self._raw.execute(self._sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(self._sql.Identifier(self.schema)))
                for name in ('001_postgres.sql','002_study.sql'):self._run_migration(name)
                for key,value in {'schema':'2','postgres_migration':'2','mode':self.cfg['mode'],'model':self.cfg['model']}.items():
                    self._raw.execute('INSERT INTO settings(key,value) VALUES(%s,%s)',(key,value))
            # Existing schemas are validated, never dropped, cleared, or changed silently.
        self.check()
    def _run_migration(self,name):
        migration=Path(__file__).with_name('migrations').joinpath(name).read_text()
        # Versioned files contain only DDL statements/comments, no procedural blocks.
        ddl='\n'.join(line for line in migration.splitlines() if not line.lstrip().startswith('--'))
        for statement in ddl.split(';'):
            if statement.strip():self._raw.execute(statement)
    def migrate(self):
        """Explicit admin command: upgrade an existing schema-1 study schema to schema 2 in place."""
        with self._raw.transaction():
            self._raw.execute(self._sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(self._sql.Identifier(self.schema)))
            current=self._raw.execute("SELECT value FROM settings WHERE key='postgres_migration'").fetchone()
            if current and current[0]=='1':
                self._run_migration('002_study.sql')
                self._raw.execute("UPDATE settings SET value='2' WHERE key IN ('schema','postgres_migration')")
        self.check()
    def check(self):
        with self.connect() as db:
            values={r['key']:r['value'] for r in db.execute('SELECT key,value FROM settings')}
            if values.get('postgres_migration')=='1':
                raise DatabaseError('This database uses the older schema. Run: python3 tools/database.py migrate (keeps all existing records).')
            expected={'schema':'2','postgres_migration':'2','mode':self.cfg['mode'],'model':self.cfg['model']}
            if any(values.get(k)!=v for k,v in expected.items()):
                raise DatabaseError('Database schema/mode/model does not match. Preserve existing data and initialize a different hci_* schema for new mode/model settings.')
    def close(self):
        with self._lock:
            if self._raw is not None:
                # Release the schema lock explicitly so a pooled connection can never keep it.
                try:self._raw.execute('SELECT pg_advisory_unlock_all()')
                except Exception:pass
                self._raw.close();self._raw=None
    def backup(self,destination):
        raise DatabaseError('Use PostgreSQL/Supabase dump and restore tools for this backend; SQLite backup is not supported.')
