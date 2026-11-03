"""Conversation lifecycle, authorization and isolated memory."""
import hashlib,json,secrets,threading,time,re,sqlite3
from pathlib import Path
from .storage import Storage
from .provider import Provider,ProviderError,validate_notes,SAFETY_RESPONSE
PROMPTS=json.loads(Path(__file__).with_name('prompts.json').read_text())
GREETING="Hi, I’m here to listen. What’s been on your mind lately?"
STYLES=('reassure','guide')
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def uid(prefix):return prefix+secrets.token_hex(8)
class Error(Exception):
    def __init__(self,message,status=400):self.message=message;self.status=status
class Chatbot:
    def __init__(self,cfg,provider=None):
        self.cfg=cfg;self.storage=Storage(cfg['db'],cfg['mode'],cfg['model']);self.provider=provider or Provider(cfg)
        self.locks={};self.guard=threading.Lock()
    def lock(self,key):
        with self.guard:return self.locks.setdefault(key,threading.Lock())
    def event(self,db,tester,cid,name,detail=''):
        db.execute('INSERT INTO events(tester_id,conversation_id,event,created,detail) VALUES(?,?,?,?,?)',(tester,cid,name,time.time(),detail))
    def style(self,style):
        if style not in STYLES:raise Error('Choose Reassure or Guide.')
        return style
    def create_tester(self):
        code=secrets.token_urlsafe(24);tid=uid('T')
        with self.storage.connect() as db:
            db.execute('INSERT INTO testers VALUES(?,?,?,?,?,?)',(tid,digest(code),time.time(),None,'reassure',0));self.event(db,tid,None,'tester_created')
        return {'id':tid,'code':code}
    def token(self,db,tid,role,style):
        token=secrets.token_urlsafe(32)
        db.execute('INSERT INTO logins VALUES(?,?,?,?,?)',(digest(token),tid,role,style,time.time()+43200));return token
    def login(self,code,admin=False):
        if not isinstance(code,str) or len(code)>200:raise Error('Invalid access code.',401)
        with self.storage.connect() as db:
            if admin:
                if not secrets.compare_digest(code,self.cfg['admin_key']):raise Error('Invalid access code.',401)
                return self.token(db,None,'admin',None)
            t=db.execute('SELECT * FROM testers WHERE code_hash=?',(digest(code),)).fetchone()
            if not t:raise Error('Invalid access code.',401)
            return self.token(db,t['id'],'tester',t['active_style'])
    def handoff(self,tid,style):
        self.style(style)
        with self.storage.connect() as db:
            if not db.execute('SELECT 1 FROM testers WHERE id=?',(tid,)).fetchone():raise Error('Unknown tester.',404)
            db.execute('UPDATE testers SET active_style=? WHERE id=?',(style,tid))
            self.event(db,tid,None,'handoff',style);return self.token(db,tid,'tester',style)
    def authenticate(self,token,role=None):
        with self.storage.connect() as db:
            row=db.execute('SELECT * FROM logins WHERE hash=? AND expires>?',(digest(token),time.time())).fetchone()
            if not row or (role and row['role']!=role):raise Error('Please sign in.',401)
            return dict(row)
    def logout(self,token):
        with self.storage.connect() as db:db.execute('DELETE FROM logins WHERE hash=?',(digest(token),))
    def tester(self,db,auth,allow_suspended=False):
        t=db.execute('SELECT * FROM testers WHERE id=?',(auth['tester_id'],)).fetchone()
        if not t:raise Error('This tester record no longer exists.',410)
        if t['suspended'] and not allow_suspended:raise Error('The test is paused. Please speak with the researcher.',409)
        return t
    def conversation(self,db,auth,cid,allow_suspended=False):
        t=self.tester(db,auth,allow_suspended)
        c=db.execute('SELECT * FROM conversations WHERE id=? AND tester_id=? AND style=?',(cid,t['id'],auth['style'])).fetchone()
        if not c:raise Error('Conversation unavailable.',404)
        return c
    def consent(self,auth,data):
        if not all(data.get(k) is True for k in ['adult','mild','voluntary','data_consent']):raise Error('Please read and confirm each consent statement.')
        with self.storage.connect() as db:
            t=self.tester(db,auth);db.execute('UPDATE testers SET consent=COALESCE(consent,?) WHERE id=?',(time.time(),t['id']));self.event(db,t['id'],None,'consent')
    def selected_notes(self,db,c):
        notes=[]
        for ref in json.loads(c['memory_refs']):
            row=db.execute("SELECT m.*,c.ended FROM memories m JOIN conversations c ON c.id=m.conversation_id WHERE m.id=? AND c.tester_id=? AND c.style=? AND c.status='completed' AND m.status='ready'",(ref,c['tester_id'],c['style'])).fetchone()
            if row:notes.append({'memory_id':row['id'],'completed_at':row['ended'],'notes':json.loads(row['notes'])})
        return notes
    def start(self,auth):
        with self.lock('start:'+auth['tester_id']+auth['style']):
            with self.storage.connect() as db:
                t=self.tester(db,auth)
                if not t['consent']:raise Error('Please complete consent first.',409)
                old=db.execute("SELECT id FROM conversations WHERE tester_id=? AND style=? AND status='open'",(t['id'],auth['style'])).fetchone()
                if old:return {'id':old[0],'resumed':True}
                rows=db.execute("SELECT m.id,m.status FROM conversations c JOIN memories m ON m.conversation_id=c.id WHERE c.tester_id=? AND c.style=? AND c.status='completed' AND m.status!='excluded' ORDER BY c.ended DESC,c.id DESC LIMIT 3",(t['id'],auth['style'])).fetchall()
                if any(r['status']!='ready' for r in rows):raise Error('Earlier conversation saved, but its memory needs retry. Ask the researcher to retry the summary before a new chat.',409)
                refs=[r['id'] for r in reversed(rows)];cid=uid('C');prompt_json=json.dumps(PROMPTS,sort_keys=True)
                db.execute('INSERT INTO conversations VALUES(?,?,?,?,?,?,?,?,?,?)',(cid,t['id'],auth['style'],'open',time.time(),None,self.cfg['model'],digest(prompt_json),prompt_json,json.dumps(refs)))
                db.execute('INSERT INTO messages(conversation_id,seq,role,text,status,request_id,created,model) VALUES(?,?,?,?,?,?,?,?)',(cid,0,'assistant',GREETING,'success','opening',time.time(),'FIXED_GREETING'))
                self.event(db,t['id'],cid,'conversation_started',json.dumps(refs));return {'id':cid,'resumed':False}
    def state(self,auth,cid=None):
        with self.storage.connect() as db:
            t=self.tester(db,auth,True)
            result={'tester_id':t['id'],'bot_label':auth['style'].title(),'bot_name':auth['style'].title(),'style':auth['style'],'consented':bool(t['consent']),'suspended':bool(t['suspended']),
              'mode':self.cfg['mode'],'api_ready_for_requests':self.cfg['mode']=='live','contact':self.cfg['contact'],'support':self.cfg['support'],'delete_date':self.cfg['delete_date'],
              'conversations':[dict(r) for r in db.execute('SELECT c.id,c.status,c.started,c.ended,m.status AS memory_status FROM conversations c LEFT JOIN memories m ON c.id=m.conversation_id WHERE tester_id=? AND style=? ORDER BY c.started DESC',(t['id'],auth['style']))]}
            if cid:
                c=self.conversation(db,auth,cid,True);messages=[dict(r) for r in db.execute('SELECT seq,role,text,status,request_id,model FROM messages WHERE conversation_id=? ORDER BY seq',(cid,))]
                result['conversation']={k:c[k] for k in ['id','status','started']};result['conversation']['older_prompts']=c['prompt_version']!=digest(json.dumps(PROMPTS,sort_keys=True));result['messages']=messages
                result['memories']=[{'id':n['memory_id'],'completed_at':n['completed_at']} for n in self.selected_notes(db,c)]
                result['turns']=sum(m['role']=='user' and m['status']=='success' and not m['request_id'].startswith('correction') for m in messages)
            return result
    def send(self,auth,cid,text,request_id):
        if not isinstance(text,str) or not 1<=len(text.strip())<=1500:raise Error('Write a message of 1–1,500 characters.')
        if not isinstance(request_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',request_id):raise Error('Invalid message request ID.')
        mutex=self.lock(cid)
        if not mutex.acquire(blocking=False):raise Error('A reply is already in progress. Please wait or stop.',409)
        try:
            with self.storage.connect() as db:
                c=self.conversation(db,auth,cid)
                if c['status']!='open':raise Error('This conversation has ended.',409)
                if self.cfg['mode']=='setup':raise Error('OpenAI is not connected. Add your API key and enable live mode before chatting. No simulated reply was generated.',503)
                if re.search(r'suicid|self[ -]?harm|kill myself|want to die|end my life|hurt myself|harm someone|hurt someone|\babuse\b',text,re.I):
                    db.execute('UPDATE testers SET suspended=1 WHERE id=?',(c['tester_id'],))
                    db.execute("UPDATE conversations SET status='stopped',ended=? WHERE tester_id=? AND status='open'",(time.time(),c['tester_id']))
                    self.event(db,c['tester_id'],cid,'safety_keyword_stop');return {'stopped':True,'safety':True}
                existing=db.execute("SELECT * FROM messages WHERE conversation_id=? AND request_id=? AND role='user'",(cid,request_id)).fetchone()
                if existing and existing['text']!=text.strip():raise Error('A retry must keep its original message text.',409)
                if existing and existing['status']=='success':return {'ok':True,'duplicate':True}
                unresolved=db.execute("SELECT * FROM messages WHERE conversation_id=? AND role='user' AND status!='success'",(cid,)).fetchall()
                if any(m['request_id']!=request_id for m in unresolved):raise Error('Retry the unsent message first, or discard this conversation.',409)
                count=db.execute("SELECT count(*) FROM messages WHERE conversation_id=? AND role='user' AND status='success' AND flags!='memory_correction'",(cid,)).fetchone()[0]
                if count>=20:raise Error('This prototype chat has reached 20 messages. Finish it and start a new conversation.',409)
                if not existing:
                    seq=db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM messages WHERE conversation_id=?',(cid,)).fetchone()[0]
                    db.execute('INSERT INTO messages(conversation_id,seq,role,text,status,request_id,created) VALUES(?,?,?,?,?,?,?)',(cid,seq,'user',text.strip(),'pending',request_id,time.time()))
                else:db.execute("UPDATE messages SET status='pending' WHERE id=?",(existing['id'],))
                history=[dict(r) for r in db.execute("SELECT role,text FROM messages WHERE conversation_id=? AND status='success' AND request_id!='opening' ORDER BY seq",(cid,))]+[{'role':'user','text':text.strip()}]
                notes=self.selected_notes(db,c);prompts=json.loads(c['prompt_json'])
                if sum(len(m['text'].encode()) for m in history)+len(json.dumps(notes).encode())+len(c['prompt_json'].encode())>55000:raise Error('Please finish this long conversation and start another.',409)
            try:reply=self.provider.reply(prompts,c['style'],notes,history)
            except ProviderError as exc:
                with self.storage.connect() as db:
                    db.execute("UPDATE messages SET status='failed' WHERE conversation_id=? AND request_id=? AND role='user' AND status='pending'",(cid,request_id))
                    if db.execute('SELECT 1 FROM conversations WHERE id=?',(cid,)).fetchone():self.event(db,c['tester_id'],cid,'provider_error')
                raise Error(str(exc),503) from exc
            with self.storage.connect() as db:
                # It may have been deleted, reset or stopped while waiting.
                row=db.execute('SELECT status FROM conversations WHERE id=?',(cid,)).fetchone()
                if not row or row[0]!='open':return {'stopped':True}
                self.tester(db,auth)
                if SAFETY_RESPONSE.replace('’', "'").casefold() in reply['text'].replace('’', "'").casefold() or 'beyond what this chatbot can support' in reply['text'].casefold():
                    db.execute('UPDATE testers SET suspended=1 WHERE id=?',(c['tester_id'],));db.execute("UPDATE conversations SET status='stopped',ended=? WHERE tester_id=? AND status='open'",(time.time(),c['tester_id']));self.event(db,c['tester_id'],cid,'model_safety_stop');return {'stopped':True,'safety':True}
                seq=db.execute('SELECT MAX(seq)+1 FROM messages WHERE conversation_id=?',(cid,)).fetchone()[0]
                flags='over_80_words' if len(reply['text'].split())>=80 else ''
                db.execute("UPDATE messages SET status='success' WHERE conversation_id=? AND request_id=? AND role='user'",(cid,request_id))
                db.execute('INSERT INTO messages(conversation_id,seq,role,text,status,request_id,created,model,usage,flags) VALUES(?,?,?,?,?,?,?,?,?,?)',(cid,seq,'assistant',reply['text'],'success',request_id,time.time(),reply['model'],json.dumps(reply.get('usage',{})),flags))
                self.event(db,c['tester_id'],cid,'reply_saved',json.dumps([n['memory_id'] for n in notes]));return {'ok':True}
        finally:mutex.release()
    def finish(self,auth,cid):
        mutex=self.lock(cid)
        if not mutex.acquire(False):raise Error('Wait for the reply before finishing, or use Stop.',409)
        try:
            with self.storage.connect() as db:
                c=self.conversation(db,auth,cid)
                if c['status']=='completed':return {'ok':True}
                if c['status']!='open':raise Error('This conversation cannot be finished.',409)
                if db.execute("SELECT 1 FROM messages WHERE conversation_id=? AND role='user' AND status!='success'",(cid,)).fetchone():raise Error('Retry the pending message or discard this conversation first.',409)
                if not db.execute("SELECT 1 FROM messages WHERE conversation_id=? AND role='user' AND status='success' AND flags!='memory_correction'",(cid,)).fetchone():raise Error('Send at least one message before finishing.')
                db.execute("UPDATE conversations SET status='completed',ended=? WHERE id=?",(time.time(),cid))
                db.execute('INSERT OR IGNORE INTO memories VALUES(?,?,?,?,?,?,?,?,?)',(uid('M'),cid,'pending',None,'1',self.cfg['model'],c['prompt_version'],time.time(),None))
                self.event(db,c['tester_id'],cid,'conversation_finished')
        finally:mutex.release()
        return self.summarize(cid)
    def summarize(self,cid):
        mutex=self.lock('summary:'+cid)
        if not mutex.acquire(False):raise Error('Memory generation is already in progress.',409)
        try:
            with self.storage.connect() as db:
                c=db.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone();m=db.execute('SELECT * FROM memories WHERE conversation_id=?',(cid,)).fetchone()
                if not c or not m:raise Error('Summary unavailable.',404)
                if m['status'] in ('ready','excluded'):return {'ok':True,'memory_status':m['status']}
                transcript=[dict(r) for r in db.execute("SELECT role,text FROM messages WHERE conversation_id=? AND status='success' ORDER BY seq",(cid,))]
            try:notes=validate_notes(self.provider.summarize(json.loads(c['prompt_json']),transcript))
            except ProviderError as exc:
                with self.storage.connect() as db:
                    db.execute("UPDATE memories SET status='failed',error='summary_failed' WHERE conversation_id=? AND status!='excluded'",(cid,))
                return {'ok':True,'memory_status':'failed','warning':'Conversation saved; memory needs retry. '+str(exc)}
            with self.storage.connect() as db:
                changed=db.execute("UPDATE memories SET status='ready',notes=?,error=NULL WHERE conversation_id=? AND status IN ('pending','failed')",(json.dumps(notes,ensure_ascii=False),cid)).rowcount
                if changed:self.event(db,c['tester_id'],cid,'memory_ready')
                return {'ok':True,'memory_status':'ready' if changed else 'excluded'}
        finally:mutex.release()
    def stop(self,auth,cid,discard=False):
        with self.storage.connect() as db:
            c=self.conversation(db,auth,cid,True)
            if c['status']=='open':
                db.execute('UPDATE conversations SET status=?,ended=? WHERE id=?',('discarded' if discard else 'stopped',time.time(),cid));self.event(db,c['tester_id'],cid,'discarded' if discard else 'manual_stop')
        return {'ok':True}
    def invalidate(self,auth,cid,mid,correction):
        if not isinstance(correction,str) or not 1<=len(correction.strip())<=1000:raise Error('Describe the correction in 1–1,000 characters.')
        mutex=self.lock(cid)
        if not mutex.acquire(False):raise Error('Wait for the current reply before correcting memory.',409)
        try:
            with self.storage.connect() as db:
                c=self.conversation(db,auth,cid)
                if db.execute("SELECT 1 FROM messages WHERE conversation_id=? AND role='user' AND status!='success'",(cid,)).fetchone():raise Error('Retry the unanswered message before recording a correction, or discard this conversation.',409)
                if c['status']!='open' or mid not in json.loads(c['memory_refs']):raise Error('This memory is not used in this open conversation.',409)
                row=db.execute('SELECT m.id FROM memories m JOIN conversations c ON c.id=m.conversation_id WHERE m.id=? AND c.tester_id=? AND c.style=?',(mid,c['tester_id'],c['style'])).fetchone()
                if not row:raise Error('Memory unavailable.',404)
                db.execute("UPDATE memories SET status='excluded',error='user_correction' WHERE id=?",(mid,))
                refs=[r for r in json.loads(c['memory_refs']) if r!=mid];db.execute('UPDATE conversations SET memory_refs=? WHERE id=?',(json.dumps(refs),cid))
                seq=db.execute('SELECT MAX(seq)+1 FROM messages WHERE conversation_id=?',(cid,)).fetchone()[0]
                db.execute('INSERT INTO messages(conversation_id,seq,role,text,status,request_id,created,flags) VALUES(?,?,?,?,?,?,?,?)',(cid,seq,'user','Correction to earlier memory: '+correction.strip(),'success',uid('correction'),time.time(),'memory_correction'))
                self.event(db,c['tester_id'],cid,'memory_invalidated',mid)
        finally:mutex.release()
        return {'ok':True}
    def reset(self,tid,style):
        self.style(style)
        with self.storage.connect() as db:
            if not db.execute('SELECT 1 FROM testers WHERE id=?',(tid,)).fetchone():raise Error('Unknown tester.',404)
            db.execute("UPDATE memories SET status='excluded',error='researcher_reset' WHERE conversation_id IN (SELECT id FROM conversations WHERE tester_id=? AND style=?)",(tid,style))
            db.execute("UPDATE conversations SET status='discarded',ended=? WHERE tester_id=? AND style=? AND status='open'",(time.time(),tid,style));self.event(db,tid,None,'memory_reset',style)
        return {'ok':True}
    def delete(self,tid):
        with self.storage.connect() as db:
            if not db.execute('DELETE FROM testers WHERE id=?',(tid,)).rowcount:raise Error('Unknown tester.',404)
        return {'ok':True}
    def admin_state(self):
        with self.storage.connect() as db:
            return {'mode':self.cfg['mode'],'model':self.cfg['model'],'api_key_configured':self.cfg.get('api_key_configured',False),'testers':[dict(r) for r in db.execute('SELECT id,created,consent,active_style,suspended FROM testers ORDER BY created')],
              'conversations':[dict(r) for r in db.execute('SELECT c.id,c.tester_id,c.style,c.status,c.started,c.prompt_version,m.status AS memory_status FROM conversations c LEFT JOIN memories m ON m.conversation_id=c.id ORDER BY c.started DESC')]}
    def inspect(self,cid):
        with self.storage.connect() as db:
            c=db.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone()
            if not c:raise Error('Unknown conversation.',404)
            return {'conversation':dict(c),'messages':[dict(r) for r in db.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY seq',(cid,))], 'memory':dict(r) if (r:=db.execute('SELECT * FROM memories WHERE conversation_id=?',(cid,)).fetchone()) else None}
    def export(self):
        with self.storage.connect() as db:
            return {'mode':self.cfg['mode'],'exported_at':time.time(),'testers':[dict(r) for r in db.execute('SELECT id,created,consent,active_style,suspended FROM testers')],**{table:[dict(r) for r in db.execute('SELECT * FROM '+table)] for table in ['conversations','messages','memories','events']}}
