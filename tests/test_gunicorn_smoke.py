"""Exercise the actual deployment server in demo mode, using disposable records."""
import importlib.util,json,os,secrets,socket,subprocess,sys,tempfile,time,unittest,urllib.request,http.cookiejar
from pathlib import Path
@unittest.skipUnless(importlib.util.find_spec('gunicorn'),'Install requirements.txt for the production-server smoke test')
class GunicornSmoke(unittest.TestCase):
    def test_real_server_chat_summary_and_restart(self):self.exercise('persistent')
    def test_real_temporary_server_restart(self):self.exercise('temporary')
    def exercise(self,storage):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            origin=f'http://127.0.0.1:{port}';admin=secrets.token_urlsafe(32)
            env={**os.environ,'CHATBOT_MODE':'demo','DATABASE_BACKEND':'sqlite','STORAGE_MODE':storage,'PORT':str(port),'PUBLIC_ORIGIN':origin,'ADMIN_KEY':admin,'CHATBOT_DB':temp+'/demo.sqlite3','DEPLOYMENT':'local','RENDER':'false','TESTER_MINUTE_API_LIMIT':'100'}
            jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            def call(path,data=None):
                req=urllib.request.Request(origin+path,data=None if data is None else json.dumps(data).encode(),headers={'Origin':origin,'X-Chatbot-Request':'1','Content-Type':'application/json'})
                with client.open(req,timeout=5) as response:return json.load(response)
            def launch():
                proc=subprocess.Popen([sys.executable,'-m','gunicorn','-c','gunicorn.conf.py','app.server:application'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                for _ in range(100):
                    if proc.poll() is not None:raise AssertionError('Gunicorn exited during startup')
                    try:
                        if call('/health')['ok']:return proc
                    except OSError:time.sleep(.05)
                proc.terminate();proc.wait(10);raise AssertionError('Health check timed out')
            proc=launch()
            try:
                call('/api/login',{'code':admin,'admin':True});tester=call('/api/admin/create',{})
                call('/api/admin/assign',{'tester_id':tester['id'],'style':'guide'})
                call('/api/login',{'code':tester['code']})
                call('/api/action',{'action':'consent',**dict.fromkeys(['adult','mild','voluntary','data_consent'],True)})
                cid=call('/api/action',{'action':'start'})['id']
                call('/api/action',{'action':'send','conversation_id':cid,'text':'I had a bad day.','request_id':'smoke-test-001'})
                self.assertEqual(call('/api/action',{'action':'finish','conversation_id':cid})['memory_status'],'disabled' if storage=='temporary' else 'ready')
                proc.terminate();proc.wait(10);proc=launch()
                if storage=='temporary':
                    call('/api/login',{'code':admin,'admin':True});state=call('/api/admin/state')
                    self.assertEqual(state['testers'],[]);self.assertEqual(state['usage']['attempts_total'],0)
                    return
                call('/api/login',{'code':tester['code']});cid=call('/api/action',{'action':'start'})['id']
                state=call('/api/state?conversation_id='+cid);self.assertEqual(state['bot_label'],'Guide');self.assertEqual(len(state['memories']),1)
                call('/api/login',{'code':admin,'admin':True});self.assertEqual(call('/api/admin/state')['usage']['attempts_total'],2)
            finally:
                proc.terminate();proc.wait(10)
