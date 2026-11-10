"""Hosted boundaries, quotas and persistence. Fake AI only; no paid requests."""
import io,json,tempfile,threading,unittest,os
from pathlib import Path
from unittest.mock import patch
import test_chatbot as fixtures
from app.chatbot import Chatbot,Error
from app.provider import ProviderError
from app.config import configuration
from app import server
class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.Tests();self.f.setUp();self.bot=self.f.bot
    def tearDown(self):self.f.tearDown()
    def limit(self,**kw):self.bot.usage.limits.update(kw)
    def test_retries_count_and_no_extra_provider_call(self):
        self.limit(GLOBAL_TOTAL_API_LIMIT=1);c=self.f.start();self.f.provider.fail=True
        with self.assertRaises(Error):self.f.send(c,rid='retry0001')
        with self.assertRaises(Error):self.f.send(c,rid='retry0001')
        self.assertEqual(len(self.f.provider.calls),1);self.assertEqual(self.bot.usage.state()['attempts_total'],1)
    def test_summary_counts_and_can_be_retried_after_limit_increase(self):
        self.limit(GLOBAL_TOTAL_API_LIMIT=1);c=self.f.start();self.f.send(c)
        self.assertEqual(self.bot.finish(self.f.auth,c)['memory_status'],'failed')
        self.limit(GLOBAL_TOTAL_API_LIMIT=2);self.assertEqual(self.bot.summarize(c)['memory_status'],'ready')
        self.assertEqual(self.bot.usage.state()['attempts_total'],2)
    def test_shared_limit_across_styles_and_restart(self):
        self.limit(TESTER_DAILY_API_LIMIT=1);c=self.f.start();self.f.send(c)
        g=self.f.authorize(self.f.t['id'],'guide');gc=self.f.start(g)
        with self.assertRaises(Error):self.f.send(gc,auth=g)
        b=Chatbot(self.f.cfg,self.f.provider);b.usage.limits['TESTER_DAILY_API_LIMIT']=1
        with self.assertRaises(Error):b.send(g,gc,'Something else','restart01')
    def test_utc_reset_does_not_reset_lifetime_cap(self):
        self.limit(GLOBAL_TOTAL_API_LIMIT=1)
        with self.bot.usage.reserve(self.f.t['id'],'reply'):pass
        with patch('app.limits.time.time',return_value=3000000000):
            with self.assertRaises(ProviderError):
                with self.bot.usage.reserve('different','reply'):pass
    def test_pause_survives_restart_and_blocks_summary(self):
        c=self.f.start();self.f.send(c);self.bot.set_paused(True)
        b=Chatbot(self.f.cfg,self.f.provider);self.assertTrue(b.usage.state()['paused'])
        self.assertEqual(b.finish(self.f.auth,c)['memory_status'],'failed')
        b.set_paused(False);self.assertEqual(b.summarize(c)['memory_status'],'ready')
    def test_global_concurrency_is_atomic(self):
        self.limit(GLOBAL_CONCURRENT_API_LIMIT=1);entered=threading.Event();release=threading.Event();errors=[]
        def hold():
            try:
                with self.bot.usage.reserve('A','reply'):entered.set();release.wait(3)
            except Exception as e:errors.append(e)
        t=threading.Thread(target=hold);t.start();self.assertTrue(entered.wait(1))
        try:
            with self.assertRaises(ProviderError):
                with self.bot.usage.reserve('B','summary'):pass
        finally:release.set();t.join(3)
        self.assertFalse(errors)
        with self.bot.usage.reserve('B','summary'):pass
    def test_per_tester_concurrency_across_styles(self):
        with self.bot.usage.reserve('A','reply'):
            with self.assertRaises(ProviderError):
                with self.bot.usage.reserve('A','summary'):pass
    def test_minute_limit(self):
        self.limit(TESTER_MINUTE_API_LIMIT=1)
        with self.bot.usage.reserve('A','reply'):pass
        with self.assertRaises(ProviderError):
            with self.bot.usage.reserve('A','summary'):pass
    def test_new_chats_capped_across_styles_but_resume_allowed(self):
        self.bot.cfg['limits']['TESTER_DAILY_CHAT_LIMIT']=1;c=self.f.start()
        self.assertEqual(self.f.start(),c)
        g=self.f.authorize(self.f.t['id'],'guide')
        with self.assertRaises(Error):self.f.start(g)
    def test_remote_assignment_revokes_old_sessions(self):
        token=self.bot.login(self.f.t['code']);self.bot.assign(self.f.t['id'],'guide')
        with self.assertRaises(Error):self.bot.authenticate(token)
        self.assertEqual(self.bot.authenticate(self.bot.login(self.f.t['code']))['style'],'guide')
    def test_usage_counter_survives_tester_deletion(self):
        with self.bot.usage.reserve(self.f.t['id'],'reply'):pass
        self.bot.delete(self.f.t['id']);self.assertEqual(self.bot.usage.state()['attempts_total'],1)
    def request(self,host,origin,method='POST',path='/api/login'):
        raw=json.dumps({'code':self.f.t['code']}).encode();result={}
        env={'PATH_INFO':path,'REQUEST_METHOD':method,'HTTP_HOST':host,'HTTP_ORIGIN':origin,'HTTP_X_CHATBOT_REQUEST':'1','CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)}
        def start(status,headers):result.update(status=int(status.split()[0]),headers=dict(headers))
        with patch.object(server,'bot',self.bot):body=b''.join(server.application(env,start))
        result['body']=body;return result
    def hosted(self):self.bot.cfg.update(origin='https://example.onrender.com',allowed_host='example.onrender.com',secure_cookie=True)
    def test_https_login_secure_and_http_origin_rejected(self):
        self.hosted();r=self.request('example.onrender.com','https://example.onrender.com')
        self.assertEqual(r['status'],200);self.assertIn('; Secure',r['headers']['Set-Cookie'])
        self.assertEqual(self.request('example.onrender.com','http://example.onrender.com')['status'],403)
        self.assertEqual(self.request('evil.invalid','https://example.onrender.com')['status'],403)
    def test_health_no_secret_and_no_paid_requests(self):
        self.hosted();r=self.request('example.onrender.com','',method='GET',path='/health')
        self.assertEqual(r['status'],200);self.assertEqual(json.loads(r['body']),{'ok':True,'mode':'demo'});self.assertEqual(self.f.provider.calls,[])
    def test_interface_and_health_do_not_wait_for_database(self):
        def request(path,host='127.0.0.1:8766'):
            result={}
            def start(status,headers):result.update(status=int(status.split()[0]),headers=dict(headers))
            result['body']=b''.join(server.application({'PATH_INFO':path,'REQUEST_METHOD':'GET','HTTP_HOST':host},start))
            return result
        with patch.object(server,'bot',None),patch.object(server,'configuration',return_value=self.bot.cfg),patch.object(server,'get_bot',side_effect=AssertionError('Must not open database')):
            for path in ('/','/admin','/app.js','/style.css','/health'):
                self.assertEqual(request(path)['status'],200)
            self.assertEqual(request('/','evil.invalid')['status'],403)
    def test_render_configuration_rejects_missing_disk(self):
        values={'ADMIN_KEY':'test-admin-secret-at-least-24-characters','DEPLOYMENT':'render','STORAGE_MODE':'persistent','CHATBOT_MODE':'setup','RENDER_EXTERNAL_HOSTNAME':'example.onrender.com','CHATBOT_DB':'/var/data/test.sqlite3'}
        with patch('app.config.load_env'),patch.dict(os.environ,values,clear=True),patch('app.config.Path.is_mount',return_value=False):
            with self.assertRaisesRegex(ValueError,'persistent disk'):configuration()
    def test_render_configuration_detects_origin(self):
        values={'ADMIN_KEY':'test-admin-secret-at-least-24-characters','DEPLOYMENT':'render','STORAGE_MODE':'persistent','CHATBOT_MODE':'setup','RENDER_EXTERNAL_HOSTNAME':'example.onrender.com','CHATBOT_DB':'/var/data/test.sqlite3'}
        with patch('app.config.load_env'),patch.dict(os.environ,values,clear=True),patch('app.config.Path.is_mount',return_value=True),patch('app.config.Path.resolve',return_value=Path('/var/data/test.sqlite3')):
            c=configuration();self.assertEqual(c['origin'],'https://example.onrender.com');self.assertTrue(c['secure_cookie'])
