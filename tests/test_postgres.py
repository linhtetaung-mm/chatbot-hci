"""No cloud credentials: unit checks and optional disposable loopback PostgreSQL."""
import io,os,json,secrets,tempfile,threading,unittest,uuid
from pathlib import Path
from unittest.mock import patch
import test_chatbot as fixtures
from app.postgres import DatabaseError,PostgresStorage,Record,parameters,validate_database_url,connection_error,connection_options
from app.chatbot import Chatbot,Error
from app.config import configuration

class PostgresUnitTests(unittest.TestCase):
    def test_url_errors_do_not_echo_password(self):
        for url in ['','PASTE_YOUR_SUPABASE_SESSION_POOLER_URL_HERE','postgresql://user:secret@example.invalid:6543/postgres','postgresql://user:secret@example.invalid:5432/postgres?sslmode=disable']:
            with self.assertRaises(DatabaseError) as e:validate_database_url(url)
            self.assertNotIn('secret',str(e.exception))
    def test_error_categories_never_echo_sensitive_details(self):
        for raw,expected in [('SSL error: certificate verify failed SECRET_URL','certificate'),('password authentication failed for user SECRET_USER','credentials'),('Tenant or user not found SECRET_HOST','pooler user'),('could not translate host name SECRET_HOST','hostname')]:
            message=str(connection_error(RuntimeError(raw)))
            self.assertIn(expected,message);self.assertNotIn('SECRET',message)
    def test_certificate_file_is_checked_without_printing_path(self):
        cfg=self.config({'DATABASE_SSLROOTCERT':'/private/SECRET_PATH/missing.cer'})
        with self.assertRaises(DatabaseError) as exc:connection_options(cfg)
        self.assertNotIn('SECRET_PATH',str(exc.exception));self.assertIn('existing CA',str(exc.exception))
    def test_plain_session_url_accepted(self):validate_database_url('postgresql://user:encoded%40password@example.invalid:5432/postgres')
    def test_marker_translation_preserves_quotes(self):
        self.assertEqual(parameters("SELECT '?' AS literal, ? AS arg, '100%' AS percent"),"SELECT '?' AS literal, %s AS arg, '100%%' AS percent")
    def test_record_supports_existing_queries(self):
        r=Record(['id','text'],[1,'test']);self.assertEqual(r[0],1);self.assertEqual(r['text'],'test');self.assertEqual(dict(r),{'id':1,'text':'test'})
    def config(self,extra):
        values={'ADMIN_KEY':'unit-test-admin-at-least-24-characters','CHATBOT_MODE':'demo','DATABASE_BACKEND':'supabase','DATABASE_URL':'postgresql://u:pass@example.invalid:5432/postgres','STORAGE_MODE':'persistent',**extra}
        with patch('app.config.load_env'),patch.dict(os.environ,values,clear=True):return configuration()
    def test_database_requires_persistent_storage(self):
        with self.assertRaisesRegex(ValueError,'persistent'):self.config({'STORAGE_MODE':'temporary'})
    def test_schema_is_mode_specific_and_private(self):
        self.assertEqual(self.config({})['database_schema'],'hci_demo')
        with self.assertRaises(ValueError):self.config({'DATABASE_SCHEMA':'public'})
    def test_render_supabase_needs_no_local_disk(self):
        with patch('app.config.Path.is_mount',side_effect=AssertionError('Must not inspect disk')):
            c=self.config({'DEPLOYMENT':'render','RENDER_EXTERNAL_HOSTNAME':'example.onrender.com'})
        self.assertTrue(c['secure_cookie']);self.assertEqual(c['database_backend'],'supabase')
    def test_driver_errors_are_sanitized(self):
        cfg=self.config({})
        import psycopg
        with patch('psycopg.connect',side_effect=psycopg.OperationalError('password=VERY_PRIVATE')):
            with self.assertRaises(DatabaseError) as e:PostgresStorage(cfg)
        self.assertNotIn('VERY_PRIVATE',str(e.exception))

@unittest.skipUnless(os.getenv('HCI_TEST_POSTGRES_URL'),'Set HCI_TEST_POSTGRES_URL to a disposable loopback database')
class PostgresIntegrationTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        self.schema='hci_test_'+secrets.token_hex(8);self.role=None
        self.f=fixtures.Tests();self.f.setUp()
        self.cfg={**self.f.cfg,'database_backend':'supabase','storage_mode':'persistent','database_url':os.environ['HCI_TEST_POSTGRES_URL'],'database_schema':self.schema,'_local_pg_test':True}
        init=PostgresStorage(self.cfg,initialize=True);init.close()
        self.b=Chatbot(self.cfg,self.f.provider)
        self.t=self.b.create_tester();self.a=self.b.authenticate(self.b.login(self.t['code']))
        self.b.consent(self.a,dict.fromkeys(['adult','mild','voluntary','data_consent'],True))
    def tearDown(self):
        import psycopg
        from psycopg import sql
        self.b.storage.close()
        with psycopg.connect(os.environ['HCI_TEST_POSTGRES_URL'],autocommit=True) as raw:raw.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))
        if self.role:
            with psycopg.connect(os.environ['HCI_TEST_POSTGRES_URL'],autocommit=True) as raw:raw.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(self.role)))
        self.f.tearDown()
    def chat(self,auth=None):
        a=auth or self.a;c=self.b.start(a)['id'];self.b.send(a,c,'A fictional mild concern.',str(uuid.uuid4()));return c
    def complete(self,auth=None):
        c=self.chat(auth);self.assertEqual(self.b.finish(auth or self.a,c)['memory_status'],'ready');return c
    def test_chat_summary_restart_and_logout_preserve_data(self):
        self.complete();token=self.b.login(self.t['code']);self.b.logout(token)
        self.b.storage.close();self.b=Chatbot(self.cfg,self.f.provider)
        a=self.b.authenticate(self.b.login(self.t['code']));c=self.b.start(a)['id'];self.assertEqual(len(self.b.state(a,c)['memories']),1)
        self.assertEqual(self.b.usage.state()['attempts_total'],2)
    def test_three_notes_and_style_isolation(self):
        for _ in range(4):self.complete()
        c=self.b.start(self.a)['id'];self.assertEqual(len(self.b.state(self.a,c)['memories']),3)
        g=self.b.authenticate(self.b.handoff(self.t['id'],'guide'));gc=self.b.start(g)['id'];self.assertEqual(self.b.state(g,gc)['memories'],[])
    def test_other_participant_and_foreign_keys(self):
        c=self.complete();other=self.b.create_tester();a=self.b.authenticate(self.b.login(other['code']))
        with self.assertRaises(Error):self.b.state(a,c)
        with self.assertRaises(DatabaseError):
            with self.b.storage.connect() as db:db.execute("INSERT INTO events(tester_id,event,created) VALUES('missing','test',0)")
        self.assertEqual(self.b.state(self.a)['tester_id'],self.t['id'])
    def test_duplicate_message_and_finish(self):
        c=self.b.start(self.a)['id'];rid=str(uuid.uuid4())
        for _ in range(2):self.b.send(self.a,c,'A fictional mild concern.',rid)
        for _ in range(2):self.b.finish(self.a,c)
        self.assertEqual(self.b.usage.state()['attempts_total'],2)
    def test_summary_retry_and_memory_reset(self):
        self.f.provider.summary_fail=True;c=self.chat();self.assertEqual(self.b.finish(self.a,c)['memory_status'],'failed')
        self.f.provider.summary_fail=False;self.assertEqual(self.b.summarize(c)['memory_status'],'ready')
        self.b.reset(self.t['id'],'reassure');c=self.b.start(self.a)['id'];self.assertEqual(self.b.state(self.a,c)['memories'],[])
    def test_private_tables_and_rls(self):
        with self.b.storage.connect() as db:
            tables=db.execute('SELECT tablename,rowsecurity FROM pg_tables WHERE schemaname=?',(self.schema,)).fetchall()
            self.assertEqual(len(tables),8);self.assertTrue(all(r['rowsecurity'] for r in tables))
    def test_second_process_is_rejected_and_close_releases_lock(self):
        with self.assertRaisesRegex(DatabaseError,'Another chatbot'):PostgresStorage(self.cfg)
        self.b.storage.close();self.b=Chatbot(self.cfg,self.f.provider)
        self.assertEqual(len(self.b.admin_state()['testers']),1)
    def test_mode_mismatch_and_existing_init_preserve_data(self):
        self.complete();self.b.storage.close()
        with self.assertRaises(DatabaseError):PostgresStorage({**self.cfg,'mode':'live'})
        init=PostgresStorage(self.cfg,initialize=True);init.close();self.b=Chatbot(self.cfg,self.f.provider)
        self.assertEqual(len(self.b.admin_state()['testers']),1)
    def test_rollback(self):
        with self.assertRaises(RuntimeError):
            with self.b.storage.connect() as db:
                db.execute("INSERT INTO settings(key,value) VALUES('rollback_test','x')");raise RuntimeError()
        with self.b.storage.connect() as db:self.assertIsNone(db.execute("SELECT value FROM settings WHERE key='rollback_test'").fetchone())
    def test_pause_and_quota_returning_identity(self):
        self.b.usage.limits['GLOBAL_TOTAL_API_LIMIT']=1;c=self.chat()
        self.assertEqual(self.b.usage.state()['attempts_total'],1)
        self.assertEqual(self.b.finish(self.a,c)['memory_status'],'failed')
        self.b.set_paused(True);self.assertTrue(self.b.usage.state()['paused'])
    def test_stop_during_request(self):
        c=self.b.start(self.a)['id'];entered=threading.Event();release=threading.Event();errors=[]
        def reply(*a):entered.set();release.wait(3);return {'text':'Late','model':'TEST'}
        def worker():
            try:self.b.send(self.a,c,'A mild concern.',str(uuid.uuid4()))
            except Exception as e:errors.append(e)
        with patch.object(self.f.provider,'reply',side_effect=reply):
            t=threading.Thread(target=worker);t.start();self.assertTrue(entered.wait(1));self.b.stop(self.a,c);release.set();t.join(3)
        self.assertFalse(errors);self.assertNotIn('Late',json.dumps(self.b.inspect(c)))
    def test_startup_does_not_change_pending_message(self):
        c=self.b.start(self.a)['id']
        with self.b.storage.connect() as db:db.execute("INSERT INTO messages(conversation_id,seq,role,text,status,request_id,created) VALUES(?,1,'user','test','pending','pending_test',0)",(c,))
        self.b.storage.close();self.b=Chatbot(self.cfg,self.f.provider)
        self.assertEqual(self.b.inspect(c)['messages'][-1]['status'],'pending')
    def test_delete_cascades_but_counter_remains(self):
        self.complete();self.b.delete(self.t['id']);self.assertEqual(self.b.admin_state()['conversations'],[])
        self.assertEqual(self.b.usage.state()['attempts_total'],2)
    def test_backup_rejects_sqlite(self):
        with self.assertRaises(DatabaseError):self.b.storage.backup('/tmp/not-a-sqlite-backup')

    def test_optional_restricted_role_can_run_chat_without_schema_ownership(self):
        import psycopg
        from urllib.parse import urlsplit
        self.role='hci_role_'+secrets.token_hex(8)
        script=Path(__file__).resolve().parents[1].joinpath('app/migrations/server_role_optional.sql').read_text()
        ddl='\n'.join(line for line in script.splitlines() if not line.lstrip().startswith('--'))
        # Use the same synthetic password in CREATE ROLE and the TCP connection.
        # Trust-authenticated local PostgreSQL used to hide this CI-only mismatch.
        ddl=ddl.replace('hci_chatbot_app',self.role).replace('hci_live',self.schema).replace('REPLACE_PRIVATELY_WITH_A_STRONG_PASSWORD','test-only')
        with psycopg.connect(os.environ['HCI_TEST_POSTGRES_URL'],autocommit=True) as raw:
            for statement in ddl.split(';'):
                if statement.strip():raw.execute(statement)
        self.b.storage.close()
        u=urlsplit(os.environ['HCI_TEST_POSTGRES_URL'])
        self.cfg={**self.cfg,'database_url':f'postgresql://{self.role}:test-only@{u.hostname}:{u.port or 5432}{u.path}'}
        self.b=Chatbot(self.cfg,self.f.provider)
        self.complete()
        with self.assertRaises(DatabaseError):
            with self.b.storage.connect() as db:db.execute('CREATE TABLE forbidden(id INTEGER)')
