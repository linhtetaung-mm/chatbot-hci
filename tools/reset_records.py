"""Explicit record reset. Default is a count-only preview; never prints credentials or content."""
import argparse, hashlib, json, os, sqlite3, sys
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import configuration
from app.postgres import PostgresStorage, DatabaseError
TABLES=['settings','testers','assignments','conversations','messages','memories','chat_meta','events','logins','api_attempts']
DELETE_ORDER=['logins','events','chat_meta','memories','messages','assignments','conversations','testers','api_attempts']
KEEP=('schema','postgres_migration','mode','model')

def clear_records(db,tables):
    for table in DELETE_ORDER:
        if table in tables:db.execute('DELETE FROM '+table)
    if 'settings' in tables:db.execute("DELETE FROM settings WHERE key NOT IN ('schema','postgres_migration','mode','model')")

def private_write(path,text):
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as file:file.write(text)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-local',action='store_true',help='Also reset the three data/chatbots-*.sqlite3 files in this checkout.')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--confirm',default='')
    args=parser.parse_args();cfg=configuration();cfg['database_lock_wait']=0
    target=cfg['database_schema'] if cfg['database_backend']=='supabase' else Path(cfg['db']).name
    phrase='RESET '+target+(' AND LOCAL DATABASES' if args.include_local else '')
    if args.execute and args.confirm!=phrase:raise SystemExit('Confirmation mismatch. Preview first and copy its exact confirmation phrase.')
    local_paths=sorted((Path(__file__).resolve().parents[1]/'data').glob('chatbots-*.sqlite3')) if args.include_local else []
    if cfg['database_backend']=='sqlite' and Path(cfg['db']) not in local_paths:local_paths.append(Path(cfg['db']))
    rem=None;locals=[]
    try:
        # Acquire the app's ownership lock first; never clear a live owned schema.
        if cfg['database_backend']=='supabase':rem=PostgresStorage(cfg)
        with ExitStack() as stack:
            for path in local_paths:
                if not path.is_file():continue
                db=sqlite3.connect(path.resolve().as_uri()+'?mode=rw',uri=True,timeout=3)
                stack.callback(db.close);db.execute('PRAGMA foreign_keys=ON');db.execute('BEGIN EXCLUSIVE')
                tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0] in TABLES]
                counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in tables if t!='settings'}
                locals.append((path,db,tables));print(json.dumps({'target':str(path),'counts':counts}))
            context=rem.connect() if rem else ExitStack()
            with context as remote_db:
                if rem:
                    counts={t:remote_db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in TABLES if t!='settings'}
                    print(json.dumps({'target':target,'backend':'supabase','counts':counts}))
                if not args.execute:
                    print('PREVIEW ONLY. Stop all app processes before execution. Confirmation:',phrase)
                else:
                    folder=Path(__file__).resolve().parents[1]/'private'/('reset-backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
                    folder.mkdir(parents=True,mode=0o700)
                    for path,db,tables in locals:private_write(folder/(path.stem+'.sql'),'\n'.join(db.iterdump())+'\n')
                    if rem:
                        from psycopg import sql
                        lines=['BEGIN;',sql.SQL('SET LOCAL search_path TO {}, pg_catalog;').format(sql.Identifier(target)).as_string(rem._raw)]
                        for table in DELETE_ORDER:lines.append('DELETE FROM '+table+';')
                        lines.append('DELETE FROM settings;')
                        for table in TABLES:
                            for row in remote_db.execute('SELECT * FROM '+table).fetchall():
                                columns=list(row)
                                line=sql.SQL('INSERT INTO {} ({}) VALUES ({});').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,columns)),sql.SQL(',').join(sql.Literal(row[k]) for k in columns))
                                lines.append(line.as_string(rem._raw))
                        lines.append('COMMIT;');private_write(folder/(target+'-records.sql'),'\n'.join(lines)+'\n')
                    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.sql')}
                    private_write(folder/'SHA256.json',json.dumps(manifest,indent=2)+'\n')
                    # All backups are complete before any records are removed.
                    if rem:clear_records(remote_db,TABLES)
                    for path,db,tables in locals:clear_records(db,tables)
                    for path,db,tables in locals:
                        assert all(db.execute('SELECT count(*) FROM '+t).fetchone()[0]==0 for t in tables if t!='settings')
                    if rem:assert all(remote_db.execute('SELECT count(*) FROM '+t).fetchone()[0]==0 for t in TABLES if t!='settings')
                    print('Verified empty record tables. Private recovery backups:',folder)
            if args.execute:
                for _,db,_ in locals:db.commit()
                print('Reset complete. Credentials and schema/model compatibility metadata preserved. Study settings must be configured again.')
    except DatabaseError as exc:raise SystemExit(str(exc)) from None
    except Exception:raise SystemExit('Reset did not complete. No credentials or record contents were printed. Check ownership/connectivity; inspect backup and target counts before retrying. Independent database commits cannot be atomic across services.') from None
    finally:
        if rem:rem.close()
