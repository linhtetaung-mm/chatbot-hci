"""Explicit private-schema setup/check and synthetic DB verification. No secret output."""
import argparse,os,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import configuration
from app.postgres import PostgresStorage,DatabaseError,diagnose_connection

def self_test(cfg):
    if cfg['mode']!='demo':raise DatabaseError('Use --mode demo for synthetic self-tests. Main-study data must stay separate.')
    from app.chatbot import Chatbot
    class Synthetic:
        def reply(self,*args):return {'text':'Synthetic database check.','model':'DATABASE_SELF_TEST','usage':{}}
        def summarize(self,*args):return {'situation':'A fictional database test.','feelings':'','user_insights':'','bot_said':'Synthetic test only.'}
    b=Chatbot(cfg,Synthetic());tester=None
    try:
        tester=b.create_tester();token=b.login(tester['code']);auth=b.authenticate(token)
        b.consent(auth,dict.fromkeys(['adult','mild','voluntary','data_consent'],True))
        cid=b.start(auth)['id'];b.send(auth,cid,'A fictional database test.',str(uuid.uuid4()))
        if b.finish(auth,cid)['memory_status']!='ready':raise DatabaseError('Summary self-test did not complete. Check demo quotas.')
        b.storage.close();b=Chatbot(cfg,Synthetic());auth=b.authenticate(token)
        cid=b.start(auth)['id']
        if len(b.state(auth,cid)['memories'])!=1:raise DatabaseError('Restart memory test failed.')
        guide=b.authenticate(b.handoff(tester['id'],'guide'));gid=b.start(guide)['id']
        if b.state(guide,gid)['memories']:raise DatabaseError('Style isolation test failed.')
        print('PASS: messages, summary, restart persistence and separate style memory. No OpenAI calls made.')
    finally:
        try:
            if tester:b.delete(tester['id'])
        finally:b.storage.close()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['init','check','self-test','diagnose'])
p.add_argument('--mode',choices=['setup','demo','live'],help='Override CHATBOT_MODE for this command only; a blank DATABASE_SCHEMA follows the mode.')
p.add_argument('--schema',help='Override DATABASE_SCHEMA for this command only.')
a=p.parse_args()
if a.mode:os.environ['CHATBOT_MODE']=a.mode
if a.schema:os.environ['DATABASE_SCHEMA']=a.schema
try:
    cfg=configuration()
    if cfg.get('database_backend')!='supabase':raise DatabaseError('Set DATABASE_BACKEND=supabase and STORAGE_MODE=persistent in your private .env first.')
    if a.action=='diagnose':
        diagnose_connection(cfg);print('PASS: read-only database connection and TLS verification. No schema changes or AI calls made.')
    elif a.action=='self-test':self_test(cfg)
    else:
        s=PostgresStorage(cfg,initialize=a.action=='init')
        try:print('PASS:', 'schema initialized/validated' if a.action=='init' else 'database connection/schema validated', '|',cfg['database_schema'],'|',cfg['mode'])
        finally:s.close()
except ValueError as exc:raise SystemExit(str(exc)) from None
except Exception:raise SystemExit('Database setup failed. Check project availability, certificate, password, schema ownership and creation permissions. No connection details were printed.') from None
