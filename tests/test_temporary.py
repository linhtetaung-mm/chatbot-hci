"""Temporary mode uses process memory, clears chats, and keeps the storage contract."""
import os,unittest,threading
from pathlib import Path
from unittest.mock import patch
import test_chatbot as fixtures
from app.chatbot import Chatbot,Error
from app.config import configuration
class TemporaryTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.Tests();self.f.setUp();self.f.bot=Chatbot({**self.f.cfg,'storage_mode':'temporary','db':self.f.tmp.name+'/never-created/database.sqlite3'},self.f.provider)
        self.b=self.f.bot;self.f.t=self.b.create_tester();self.f.auth=self.f.authorize(self.f.t['id'],'reassure')
    def tearDown(self):self.b.storage.close();self.f.tearDown()
    def test_never_creates_database_or_parent(self):
        c=self.f.start();self.f.send(c)
        self.assertFalse(Path(self.f.tmp.name+'/never-created').exists())
        self.assertEqual(self.b.state(self.f.auth,c)['storage_mode'],'temporary')
    def test_finish_clears_without_summary_or_notes(self):
        c=self.f.start();self.f.send(c);self.f.provider.summary_fail=True
        self.assertEqual(self.b.finish(self.f.auth,c)['memory_status'],'disabled')
        self.assertEqual(self.b.usage.state()['attempts_total'],1)
        with self.b.storage.connect() as db:
            for table in ['messages','memories','conversations']:self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0)
        new=self.f.start();self.f.send(new);self.assertEqual(self.f.provider.calls[-1]['notes'],[])
    def test_current_context_is_available(self):
        c=self.f.start();self.f.send(c,'First detail');self.f.send(c,'Second detail')
        self.assertEqual([m['text'] for m in self.f.provider.calls[-1]['history']],['First detail','That sounds frustrating. Your feelings make sense.','Second detail'])
    def test_logout_clears_but_keeps_access_code_and_usage(self):
        c=self.f.start();self.f.send(c);token=self.b.login(self.f.t['code']);self.b.logout(token)
        a=self.b.authenticate(self.b.login(self.f.t['code']));self.assertFalse(self.b.state(a)['consented']);self.assertEqual(self.b.state(a)['conversations'],[])
        self.assertEqual(self.b.usage.state()['attempts_total'],1)
    def test_other_tester_is_not_cleared(self):
        c=self.f.start();self.f.send(c);t=self.b.create_tester();a=self.f.authorize(t['id'],'guide');other=self.f.start(a)
        self.b.stop(self.f.auth,c);self.assertEqual(self.b.state(a,other)['conversation']['id'],other)
    def test_stop_clears(self):
        c=self.f.start();self.f.send(c);self.b.stop(self.f.auth,c)
        self.assertEqual(self.b.state(self.f.auth)['conversations'],[])
    def test_exports_and_backups_disabled(self):
        with self.assertRaises(Error):self.b.export()
        with self.assertRaises(ValueError):self.b.storage.backup(self.f.tmp.name+'/backup.sqlite3')
        with self.assertRaises(Error):self.b.summarize('unknown')
    def test_restart_is_empty(self):
        self.f.send(self.f.start());b=Chatbot({**self.f.cfg,'storage_mode':'temporary'},self.f.provider)
        try:self.assertEqual(b.admin_state()['testers'],[]);self.assertEqual(b.usage.state()['attempts_total'],0)
        finally:b.storage.close()
    def test_render_temporary_requires_no_disk(self):
        values={'ADMIN_KEY':'test-admin-secret-at-least-24-characters','DEPLOYMENT':'render','STORAGE_MODE':'temporary','CHATBOT_MODE':'setup','RENDER_EXTERNAL_HOSTNAME':'example.onrender.com'}
        with patch('app.config.load_env'),patch.dict(os.environ,values,clear=True),patch('app.config.Path.is_mount',side_effect=AssertionError('Must not check disk')):
            self.assertEqual(configuration()['storage_mode'],'temporary')
    def test_concurrent_quota_and_stop_work_in_ram(self):
        c=self.f.start();entered=threading.Event();release=threading.Event();errors=[]
        def reply(*a):entered.set();release.wait(3);return {'text':'Late reply','model':'TEST'}
        def send():
            try:self.f.send(c)
            except Exception as exc:errors.append(exc)
        with patch.object(self.f.provider,'reply',side_effect=reply):
            t=threading.Thread(target=send);t.start();self.assertTrue(entered.wait(1));self.b.stop(self.f.auth,c);release.set();t.join(3)
        self.assertFalse(errors);self.assertEqual(self.b.state(self.f.auth)['conversations'],[])

    def test_finishing_does_not_reset_new_chat_quota(self):
        self.b.cfg['limits']['TESTER_DAILY_CHAT_LIMIT']=1
        c=self.f.start();self.f.send(c);self.b.finish(self.f.auth,c)
        with self.assertRaises(Error):self.f.start()
