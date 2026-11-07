"""Local WSGI server. API data is never logged by the request handler."""
import json,time,threading
from urllib.parse import urlsplit
from pathlib import Path
from http.cookies import SimpleCookie
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server,WSGIServer,WSGIRequestHandler
from .chatbot import Chatbot,Error
from .config import configuration
ROOT=Path(__file__).with_name('static');bot=None;init_lock=threading.Lock();attempts={};attempt_lock=threading.Lock()
def get_bot():
    global bot
    if bot is None:
        with init_lock:
            if bot is None:bot=Chatbot(configuration())
    return bot
class Quiet(WSGIRequestHandler):
    def log_message(self,*args):pass
class Threaded(ThreadingMixIn,WSGIServer):daemon_threads=True

def application(env,start):
    headers=[('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('Referrer-Policy','no-referrer'),('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")]
    def reply(value,status=200,ctype='application/json; charset=utf-8'):
        body=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
        labels={200:'OK',400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',409:'Conflict',410:'Gone',413:'Too Large',429:'Too Many Requests',500:'Internal Error',503:'Unavailable'}
        start(f'{status} {labels.get(status,"Error")}',headers+[('Content-Type',ctype),('Content-Length',str(len(body)))]);return [body]
    try:
        service=get_bot()
        if service.cfg.get('secure_cookie'):headers.append(('Strict-Transport-Security','max-age=31536000'))
        path=env.get('PATH_INFO','/');method=env.get('REQUEST_METHOD','GET');data={}
        host=env.get('HTTP_HOST','')
        if host!=service.cfg.get('allowed_host',urlsplit(service.cfg['origin']).netloc):raise Error('Request host rejected.',403)
        if path in ('/','/admin','/app.js','/style.css') and method=='GET':
            f=ROOT/('index.html' if path in ('/','/admin') else path[1:]);return reply(f.read_bytes(),ctype='text/html; charset=utf-8' if f.suffix=='.html' else 'text/javascript; charset=utf-8' if f.suffix=='.js' else 'text/css; charset=utf-8')
        if path=='/health' and method=='GET':return reply({'ok':True,'mode':service.cfg['mode']})
        if method not in ('GET','POST'):raise Error('Unsupported request method.',400)
        if method=='POST':
            if env.get('HTTP_ORIGIN')!=service.cfg['origin'] or env.get('HTTP_X_CHATBOT_REQUEST')!='1':raise Error('Request origin rejected.',403)
            if 'application/json' not in env.get('CONTENT_TYPE',''):raise Error('JSON required.')
            try:size=int(env.get('CONTENT_LENGTH') or '0')
            except ValueError:raise Error('Invalid request size.')
            if not 0<=size<=20000:raise Error('Request too large.',413)
            try:data=json.loads(env['wsgi.input'].read(size))
            except (ValueError,TypeError):raise Error('Invalid JSON.')
            if not isinstance(data,dict):raise Error('JSON object required.')
        cookie=SimpleCookie();cookie.load(env.get('HTTP_COOKIE',''));token=cookie['chatbot_session'].value if 'chatbot_session' in cookie else ''
        cookie_flags='; Secure' if service.cfg.get('secure_cookie',False) else ''
        def set_cookie(value):headers.append(('Set-Cookie',f'chatbot_session={value}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'+cookie_flags))
        if path=='/api/login' and method=='POST':
            ip=env.get('REMOTE_ADDR','local')
            with attempt_lock:
                now=time.time()
                for key in list(attempts):
                    if not attempts[key] or now-attempts[key][-1]>=60:attempts.pop(key,None)
                if ip not in attempts and len(attempts)>=10000:raise Error('Sign-in is busy. Wait one minute.',429)
                history=[x for x in attempts.get(ip,[]) if now-x<60]
                if len(history)>=15:raise Error('Too many attempts. Wait one minute.',429)
                attempts[ip]=history+[now]
            set_cookie(service.login(data.get('code',''),data.get('admin') is True));return reply({'ok':True})
        if path=='/api/logout' and method=='POST':service.logout(token);headers.append(('Set-Cookie','chatbot_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'+cookie_flags));return reply({'ok':True})
        if path.startswith('/api/admin/'):
            service.authenticate(token,'admin')
            if path=='/api/admin/state' and method=='GET':return reply(service.admin_state())
            if path=='/api/admin/pause' and method=='POST':return reply(service.set_paused(data.get('paused')))
            if path=='/api/admin/assign' and method=='POST':return reply(service.assign(data.get('tester_id',''),data.get('style','')))
            if path=='/api/admin/create' and method=='POST':return reply(service.create_tester())
            if path=='/api/admin/handoff' and method=='POST':set_cookie(service.handoff(data.get('tester_id',''),data.get('style','')));return reply({'ok':True})
            if path=='/api/admin/inspect' and method=='POST':return reply(service.inspect(data.get('conversation_id','')))
            if path=='/api/admin/retry' and method=='POST':return reply(service.summarize(data.get('conversation_id','')))
            if path=='/api/admin/reset' and method=='POST':
                if data.get('confirmation')!='RESET MEMORY':raise Error('Type RESET MEMORY to confirm.')
                return reply(service.reset(data.get('tester_id',''),data.get('style','')))
            if path=='/api/admin/delete' and method=='POST':
                if data.get('confirmation')!='DELETE TESTER':raise Error('Type DELETE TESTER to confirm.')
                return reply(service.delete(data.get('tester_id','')))
            if path=='/api/admin/export' and method=='GET':headers.append(('Content-Disposition','attachment; filename="private-chatbot-records.json"'));return reply(service.export())
            raise Error('Not found.',404)
        auth=service.authenticate(token,'tester')
        if path=='/api/state' and method=='GET':
            from urllib.parse import parse_qs
            cid=parse_qs(env.get('QUERY_STRING','')).get('conversation_id',[None])[0];return reply(service.state(auth,cid))
        if path=='/api/action' and method=='POST':
            action=data.get('action');cid=data.get('conversation_id','')
            if action=='consent':service.consent(auth,data);return reply({'ok':True})
            if action=='start':return reply(service.start(auth))
            if action=='send':return reply(service.send(auth,cid,data.get('text',''),data.get('request_id','')))
            if action=='finish':return reply(service.finish(auth,cid))
            if action in ('stop','discard'):return reply(service.stop(auth,cid,action=='discard'))
            if action=='invalidate':return reply(service.invalidate(auth,cid,data.get('memory_id',''),data.get('correction','')))
            raise Error('Unknown action.')
        raise Error('Not found.',404)
    except Error as exc:return reply({'error':exc.message},exc.status)
    except Exception:
        # No submitted text, tokens or API response bodies are logged.
        return reply({'error':'The app encountered a problem. Ask the researcher; your last saved records remain available.'},500)

def main():
    service=get_bot()
    try:
        with make_server('127.0.0.1',service.cfg['port'],application,server_class=Threaded,handler_class=Quiet) as server:
            print(f"Mode: {service.cfg['mode']} | Tester: {service.cfg['origin']} | Researcher: {service.cfg['origin']}/admin",flush=True)
            server.serve_forever()
    except OSError as exc:
        if exc.errno in (48,98):raise SystemExit(f"Port {service.cfg['port']} is already in use. Open the existing app or stop its terminal with Ctrl+C.")
        raise
    except KeyboardInterrupt:print('\nChatbot stopped. Saved conversations remain in the database.')
