"""Conversation lifecycle, authorization and isolated memory."""
import hashlib,json,secrets,threading,time,re,sqlite3
from pathlib import Path
from .storage import create_storage
from .limits import UsageLimits
from .provider import Provider,ProviderError,validate_notes,SAFETY_RESPONSE
PROMPTS=json.loads(Path(__file__).with_name('prompts.json').read_text())
# Same small set for every condition, picked at random, so returning participants do not see one fixed line.
GREETINGS=("Hi, I’m here to listen. What’s on your mind today?","Hello! How has your day been?","Hi there. Is there anything you’d like to talk through?","Welcome. What would you like to talk about today?")
GREETING=GREETINGS[0]
STYLES=('reassure','guide')
MEMORY=('persistent','fresh')
CHAT_TYPES=('first','home','final')
CODE_ALPHABET='ABCDEFGHJKMNPQRSTUVWXYZ23456789'  # no 0/O, 1/I/L: easy to type on a phone
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def new_code():
    raw=''.join(secrets.choice(CODE_ALPHABET) for _ in range(8));return raw[:4]+'-'+raw[4:]
def normalize_code(code):return re.sub(r'[\s-]','',code).upper()
def scale(value,low,high,label):
    if isinstance(value,bool) or not isinstance(value,int) or not low<=value<=high:raise Error(label)
    return value
def uid(prefix):return prefix+secrets.token_hex(8)
class Error(Exception):
    def __init__(self,message,status=400):self.message=message;self.status=status
class Chatbot:
    def __init__(self,cfg,provider=None):
        self.cfg=cfg;self.temporary=cfg.get('storage_mode')=='temporary'
        self.storage=create_storage(cfg)
        self.provider=provider or Provider(cfg)
        self.locks={};self.guard=threading.Lock();self.usage=UsageLimits(self.storage,cfg)
    def lock(self,key):
        with self.guard:return self.locks.setdefault(key,threading.Lock())
    def event(self,db,tester,cid,name,detail=''):
        db.execute('INSERT INTO events(tester_id,conversation_id,event,created,detail) VALUES(?,?,?,?,?)',(tester,cid,name,time.time(),detail))
    def style(self,style):
        if style not in STYLES:raise Error('Choose Reassure or Guide.')
        return style
    def create_tester(self,style='reassure',memory='persistent'):
        """Team/pilot test account. Not part of the study sample; its condition can be changed."""
        self.style(style)
        if memory not in MEMORY:raise Error('Choose persistent or fresh memory.')
        code=new_code();tid=uid('T')
        with self.storage.connect() as db:
            self._insert_tester(db,tid,code,style,memory,None,False);self.event(db,tid,None,'tester_created')
        return {'id':tid,'code':code}
    def _insert_tester(self,db,tid,code,style,memory,study_id,locked):
        db.execute('INSERT INTO testers(id,code_hash,created,consent,active_style,suspended,study_id,memory,locked) VALUES(?,?,?,?,?,?,?,?,?)',(tid,digest(normalize_code(code)),time.time(),None,style,0,study_id,memory,1 if locked else 0))
    def load_assignments(self,rows):
        """Load a concealed, pre-randomized assignment list. Existing study IDs are never changed.
        New IDs are queued AFTER every existing ID, in the file's order, so a second list can be added later."""
        added=0
        with self.storage.connect() as db:
            db.begin_serialized()
            base=db.execute('SELECT COALESCE(MAX(seq),0) FROM assignments').fetchone()[0]
            for r in sorted(rows,key=lambda r:int(r['seq'])):
                self.style(r['style'])
                if r['memory'] not in MEMORY or r['scenario'] not in ('A','B'):raise Error('Invalid assignment row: '+str(r.get('study_id')))
                if db.execute('SELECT 1 FROM assignments WHERE study_id=?',(r['study_id'],)).fetchone():continue
                added+=1
                db.execute('INSERT INTO assignments(study_id,seq,style,memory,scenario) VALUES(?,?,?,?,?)',(r['study_id'],base+added,r['style'],r['memory'],r['scenario']))
        return added
    def add_study_ids(self,count,prefix='P'):
        """Researcher button: append `count` new study IDs (a multiple of 4) in freshly shuffled blocks of 4,
        numbered after the highest existing ID with this prefix. Conditions stay concealed."""
        if isinstance(count,bool) or not isinstance(count,int) or count<4 or count>48 or count%4:raise Error('Add 4, 8, 12 ... up to 48 study IDs at a time.')
        if not re.fullmatch(r'[A-Z]{1,3}',prefix):raise Error('Invalid prefix.')
        rng=secrets.SystemRandom();conds=[(s,m) for s in STYLES for m in MEMORY]
        with self.storage.connect() as db:
            existing=db.execute('SELECT study_id,style,memory FROM assignments').fetchall()
            nums=[int(r['study_id'][len(prefix):]) for r in existing if r['study_id'].startswith(prefix) and r['study_id'][len(prefix):].isdigit()]
            seen={c:sum(1 for r in existing if (r['style'],r['memory'])==c) for c in conds}
        start=max(nums,default=0);rows=[]
        for b in range(count//4):
            block=conds[:];rng.shuffle(block)
            for style,memory in block:
                n=start+len(rows)+1;rows.append({'study_id':f'{prefix}{n:02d}','seq':len(rows)+1,'style':style,'memory':memory,'scenario':'AB'[seen[(style,memory)]%2]});seen[(style,memory)]+=1
        added=self.load_assignments(rows)
        with self.storage.connect() as db:self.event(db,None,None,'study_ids_added',json.dumps({'count':added,'first':rows[0]['study_id'],'last':rows[-1]['study_id']}))
        return {'added':added,'first':rows[0]['study_id'],'last':rows[-1]['study_id']}
    def enroll(self):
        """Give the next unused study ID, in list order, to a new participant. The condition is locked."""
        if self.temporary:
            raise Error('Participant enrollment needs persistent storage. Use a test account for a temporary preview.',409)
        with self.storage.connect() as db:
            db.begin_serialized()
            a=db.execute('SELECT * FROM assignments WHERE assigned IS NULL ORDER BY seq LIMIT 1').fetchone()
            if not a:raise Error('No unused study IDs are left. Load more with tools/assignments.py.',409)
            code=new_code();tid=uid('T')
            self._insert_tester(db,tid,code,a['style'],a['memory'],a['study_id'],True)
            db.execute('UPDATE assignments SET tester_id=?,assigned=? WHERE study_id=?',(tid,time.time(),a['study_id']))
            self.event(db,tid,None,'enrolled',a['study_id'])
            return {'id':tid,'study_id':a['study_id'],'code':code,'scenario':a['scenario']}
    def enrollment_plan(self,db):
        row=db.execute("SELECT value FROM settings WHERE key='enrollment_plan'").fetchone()
        return json.loads(row['value']) if row else None
    def set_enrollment_plan(self,data):
        groups=data.get('groups')
        if not isinstance(groups,list) or len(groups)!=4:raise Error('Configure all four support × memory settings for this study.')
        seen=set();clean=[]
        for g in groups:
            if not isinstance(g,dict):raise Error('Each setting needs a label, support style, memory and target.')
            style=self.style(g.get('style'));memory=g.get('memory');label=g.get('label');target=g.get('target')
            if memory not in MEMORY or (style,memory) in seen:raise Error('Use each support × memory combination exactly once.')
            if not isinstance(label,str) or not 1<=len(label.strip())<=80:raise Error('Give each setting a label of 1–80 characters.')
            scale(target,1,1000,'Each target must be a whole number from 1 to 1,000.')
            seen.add((style,memory));clean.append({'id':style+':'+memory,'style':style,'memory':memory,'label':label.strip(),'target':target})
        if len({g['label'].casefold() for g in clean})!=4:raise Error('Use different labels for the four settings.')
        with self.storage.connect() as db:
            db.begin_serialized()
            for g in clean:
                assigned=db.execute('SELECT count(*) FROM assignments WHERE assigned IS NOT NULL AND style=? AND memory=?',(g['style'],g['memory'])).fetchone()[0]
                if g['target']<assigned:raise Error('A target cannot be below the number already assigned to that setting.')
            plan={'groups':clean,'version':digest(json.dumps(clean,sort_keys=True))}
            db.execute("INSERT INTO settings(key,value) VALUES('enrollment_plan',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(plan),))
            db.execute("DELETE FROM settings WHERE key='enrollment_queue'")
            self.event(db,None,None,'enrollment_plan_updated',json.dumps(plan))
        return {'ok':True}
    def enroll_configured(self,mode='random',setting=None,reason=''):
        if self.temporary:raise Error('Enrollment requires persistent storage.',409)
        if mode not in ('random','manual'):raise Error('Choose randomized or manual assignment.')
        if mode=='manual' and (not isinstance(reason,str) or not 5<=len(reason.strip())<=1000):raise Error('Record a reason of 5–1,000 characters for manual assignment.')
        with self.storage.connect() as db:
            db.begin_serialized();plan=self.enrollment_plan(db)
            if not plan:raise Error('Ask the administrator to configure the four study settings first.',409)
            counts={g['id']:db.execute('SELECT count(*) FROM assignments WHERE assigned IS NOT NULL AND style=? AND memory=?',(g['style'],g['memory'])).fetchone()[0] for g in plan['groups']}
            eligible={g['id']:g for g in plan['groups'] if counts[g['id']]<g['target']}
            if mode=='manual':
                if setting not in eligible:raise Error('That setting is unavailable or has reached its target.',409)
                selected=eligible[setting]
                db.execute("DELETE FROM settings WHERE key='enrollment_queue'")
            else:
                row=db.execute("SELECT value FROM settings WHERE key='enrollment_queue'").fetchone()
                queue=[key for key in json.loads(row['value']) if key in eligible] if row else []
                if not queue:
                    if not eligible:raise Error('All configured enrollment targets have been reached.',409)
                    rounds=secrets.choice((1,2));queue=[]
                    for key,g in eligible.items():queue.extend([key]*min(rounds,g['target']-counts[key]))
                    secrets.SystemRandom().shuffle(queue)
                selected=eligible[queue.pop(0)]
                db.execute("INSERT INTO settings(key,value) VALUES('enrollment_queue',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(queue),))
            rows=db.execute('SELECT study_id,seq FROM assignments').fetchall()
            number=max([int(r['study_id'][1:]) for r in rows if re.fullmatch(r'P[0-9]+',r['study_id'])]+[0])+1
            study_id=f'P{number:03d}';seq=max([r['seq'] for r in rows]+[0])+1
            # Balance scenario exposure within the selected setting without exposing future allocations.
            scenario='AB'[counts[selected['id']]%2];code=new_code();tid=uid('T');now=time.time()
            self._insert_tester(db,tid,code,selected['style'],selected['memory'],study_id,True)
            db.execute('INSERT INTO assignments(study_id,seq,style,memory,scenario,tester_id,assigned) VALUES(?,?,?,?,?,?,?)',(study_id,seq,selected['style'],selected['memory'],scenario,tid,now))
            self.event(db,tid,None,'enrolled',study_id)
            self.event(db,tid,None,'assignment_method',json.dumps({'method':mode,'reason':reason.strip() if mode=='manual' else '', 'plan_version':plan['version'],'setting':selected['id']}))
            return {'id':tid,'study_id':study_id,'code':code,'scenario':scenario}
    def allocation_report(self,db):
        plan=self.enrollment_plan(db);labels={g['id']:g for g in plan['groups']} if plan else {}
        groups=[]
        for style in STYLES:
            for memory in MEMORY:
                key=style+':'+memory;setting=labels.get(key,{})
                people=[dict(r) for r in db.execute('SELECT id,study_id,consent,suspended FROM testers WHERE locked=1 AND active_style=? AND memory=? ORDER BY study_id',(style,memory))]
                assigned=db.execute('SELECT count(*) FROM assignments WHERE assigned IS NOT NULL AND style=? AND memory=?',(style,memory)).fetchone()[0]
                groups.append({'id':key,'label':setting.get('label',style.title()+' × '+memory.title()),'style':style,'memory':memory,'target':setting.get('target'),'assigned_total':assigned,'participants':people,'count':len(people)})
        return {'groups':groups,'plan':plan}
    def token(self,db,tid,role,style):
        token=secrets.token_urlsafe(32)
        db.execute('INSERT INTO logins VALUES(?,?,?,?,?)',(digest(token),tid,role,style,time.time()+3600*self.cfg.get('session_hours',168)));return token
    def reissue_code(self,tid):
        """Replace a lost login code without re-enrollment, condition changes or data loss."""
        code=new_code()
        with self.storage.connect() as db:
            t=db.execute('SELECT id,study_id FROM testers WHERE id=?',(tid,)).fetchone()
            if not t:raise Error('Unknown tester.',404)
            db.execute('UPDATE testers SET code_hash=? WHERE id=?',(digest(normalize_code(code)),tid))
            db.execute("DELETE FROM logins WHERE tester_id=? AND role='tester'",(tid,))
            self.event(db,tid,None,'access_code_reissued')
            return {'id':tid,'study_id':t['study_id'],'code':code}
    def login(self,code,admin=False):
        if not isinstance(code,str) or len(code)>200:raise Error('Invalid access code.',401)
        with self.storage.connect() as db:
            if admin:
                if secrets.compare_digest(code,self.cfg['admin_key']):return self.token(db,None,'admin',None)
                for account in self.cfg.get('researcher_accounts',[]):
                    if secrets.compare_digest(code,account['key']):return self.token(db,None,account['role'],account['name']+':'+digest(account['key'])[:16])
                raise Error('Invalid access code.',401)
            t=db.execute('SELECT * FROM testers WHERE code_hash=?',(digest(code),)).fetchone() or db.execute('SELECT * FROM testers WHERE code_hash=?',(digest(normalize_code(code)),)).fetchone()
            if not t:raise Error('Invalid access code.',401)
            return self.token(db,t['id'],'tester',t['active_style'])
    def handoff(self,tid,style=None):
        with self.storage.connect() as db:
            t=db.execute('SELECT * FROM testers WHERE id=?',(tid,)).fetchone()
            if not t:raise Error('Unknown tester.',404)
            # Study participants keep their locked condition; only test accounts can switch style.
            if t['locked'] or not style:style=t['active_style']
            self.style(style)
            db.execute('UPDATE testers SET active_style=? WHERE id=?',(style,tid))
            self.event(db,tid,None,'handoff',style);return self.token(db,tid,'tester',style)
    def authenticate(self,token,role=None):
        with self.storage.connect() as db:
            row=db.execute('SELECT * FROM logins WHERE hash=? AND expires>?',(digest(token),time.time())).fetchone()
            if not row or (role and row['role']!=role):raise Error('Please sign in.',401)
            if row['role'] in ('admin','facilitator') and row['style']:
                valid=any(row['role']==a['role'] and row['style']==a['name']+':'+digest(a['key'])[:16] for a in self.cfg.get('researcher_accounts',[]))
                if not valid:raise Error('Please sign in.',401)
            return dict(row)
    def logout(self,token):
        with self.storage.connect() as db:
            auth=db.execute('SELECT tester_id FROM logins WHERE hash=?',(digest(token),)).fetchone()
            db.execute('DELETE FROM logins WHERE hash=?',(digest(token),))
            if self.temporary and auth and auth['tester_id']:
                db.execute('DELETE FROM conversations WHERE tester_id=?',(auth['tester_id'],))
                db.execute('DELETE FROM events WHERE tester_id=?',(auth['tester_id'],))
                db.execute('UPDATE testers SET consent=NULL WHERE id=?',(auth['tester_id'],))
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
        if self.temporary:return []
        notes=[]
        for ref in json.loads(c['memory_refs']):
            row=db.execute("SELECT m.*,c.ended FROM memories m JOIN conversations c ON c.id=m.conversation_id WHERE m.id=? AND c.tester_id=? AND c.style=? AND c.status='completed' AND m.status='ready'",(ref,c['tester_id'],c['style'])).fetchone()
            if row:notes.append({'memory_id':row['id'],'completed_at':row['ended'],'notes':json.loads(row['notes'])})
        return notes
    def retry_pending_summaries(self,auth):
        """Before a new chat, retry recent failed/pending notes once. Failures do not prevent starting.

        Retries are synchronous and can take time; resuming an open chat does not run them.
        """
        if self.temporary:return
        with self.storage.connect() as db:
            rows=db.execute("SELECT c.id FROM conversations c JOIN memories m ON m.conversation_id=c.id WHERE c.tester_id=? AND c.style=? AND c.status='completed' AND m.status IN ('pending','failed') ORDER BY c.ended DESC LIMIT 3",(auth['tester_id'],auth['style'])).fetchall()
        for r in rows:
            try:self.summarize(r['id'])
            except Error:pass
    def start(self,auth,chat_type='home',pre_distress=None):
        if chat_type not in CHAT_TYPES:raise Error('Unknown chat type.')
        if pre_distress is not None:scale(pre_distress,0,100,'Choose how upset you feel, from 0 to 100.')
        with self.lock('start:'+auth['tester_id']+auth['style']):
            with self.storage.connect() as db:
                t=self.tester(db,auth)
                if not t['consent']:raise Error('Please complete consent first.',409)
                old=db.execute("SELECT id FROM conversations WHERE tester_id=? AND style=? AND status='open'",(t['id'],auth['style'])).fetchone()
                if old:return {'id':old[0],'resumed':True}
                if t['locked'] and db.execute("SELECT 1 FROM conversations c JOIN chat_meta x ON x.conversation_id=c.id WHERE c.tester_id=? AND c.status='completed' AND x.rated IS NULL",(t['id'],)).fetchone():
                    raise Error('Please submit the three questions from your finished chat before starting another.',409)
                if t['locked'] and pre_distress is None:raise Error('Please answer how upset you feel before starting.')
            self.retry_pending_summaries(auth)
            with self.storage.connect() as db:
                t=self.tester(db,auth)
                # Last three finished chats whose notes are ready. A note that is still failing is skipped and logged,
                # so a participant at home is never blocked. Fresh memory receives no earlier notes at all.
                rows=db.execute("SELECT m.id,m.status FROM conversations c JOIN memories m ON m.conversation_id=c.id WHERE c.tester_id=? AND c.style=? AND c.status='completed' AND m.status!='excluded' ORDER BY c.ended DESC,c.id DESC LIMIT 3",(t['id'],auth['style'])).fetchall()
                skipped=[r['id'] for r in rows if r['status']!='ready']
                rows=[r for r in rows if r['status']=='ready']
                if t['memory']=='fresh':rows=[]
                # Serialize quota check and creation, across both support styles.
                db.begin_serialized()
                day=int(time.time()//86400)*86400
                counter_key='temporary_chat_count:'+digest(t['id'])+':'+str(day)
                if self.temporary:
                    counter=db.execute('SELECT value FROM settings WHERE key=?',(counter_key,)).fetchone()
                    created=int(counter[0]) if counter else 0
                else:created=db.execute('SELECT count(*) FROM conversations WHERE tester_id=? AND started>=?',(t['id'],day)).fetchone()[0]
                if created>=self.cfg.get('limits',{}).get('TESTER_DAILY_CHAT_LIMIT',4):raise Error('Daily new-chat limit reached. Return after midnight UTC or contact the researcher.',429)
                if self.temporary:db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(counter_key,str(created+1)))
                refs=[r['id'] for r in reversed(rows)];cid=uid('C');prompt_json=json.dumps(PROMPTS,sort_keys=True)
                db.execute('INSERT INTO conversations VALUES(?,?,?,?,?,?,?,?,?,?)',(cid,t['id'],auth['style'],'open',time.time(),None,self.cfg['model'],digest(prompt_json),prompt_json,json.dumps(refs)))
                db.execute('INSERT INTO messages(conversation_id,seq,role,text,status,request_id,created,model) VALUES(?,?,?,?,?,?,?,?)',(cid,0,'assistant',secrets.choice(GREETINGS),'success','opening',time.time(),'FIXED_GREETING'))
                db.execute('INSERT INTO chat_meta(conversation_id,chat_type,pre_distress) VALUES(?,?,?)',(cid,chat_type,pre_distress))
                if skipped and t['memory']!='fresh':self.event(db,t['id'],cid,'memory_not_ready_skipped',json.dumps(skipped))
                self.event(db,t['id'],cid,'conversation_started',json.dumps(refs));return {'id':cid,'resumed':False}
    def state(self,auth,cid=None):
        with self.storage.connect() as db:
            t=self.tester(db,auth,True);participant=bool(t['locked'])
            # Same neutral name for every condition; the participant view never shows the assigned style or memory.
            result={'tester_id':t['id'],'study_id':t['study_id'],'participant':participant,'bot_label':'Chatbot','bot_name':'Chatbot','consented':bool(t['consent']),'suspended':bool(t['suspended']),
              'database_backend':self.cfg.get('database_backend','sqlite'),'storage_mode':self.cfg.get('storage_mode','persistent'),'mode':self.cfg['mode'],'api_ready_for_requests':self.cfg['mode']=='live','contact':self.cfg['contact'],'support':self.cfg['support'],'delete_date':self.cfg['delete_date'],
              'conversations':[], 'study_materials':self.study_materials(db)}
            rows=db.execute('SELECT c.id,c.status,c.started,c.ended,x.chat_type,x.rated FROM conversations c LEFT JOIN chat_meta x ON x.conversation_id=c.id WHERE c.tester_id=? AND c.style=? ORDER BY c.started,c.id',(t['id'],auth['style'])).fetchall()
            titles={r['conversation_id']:r['detail'] for r in db.execute("SELECT conversation_id,detail FROM events WHERE tester_id=? AND event='conversation_title' ORDER BY id",(t['id'],))}
            result['conversations']=[dict(r,number=i+1,title=titles.get(r['id'],'')) for i,r in reversed(list(enumerate(rows)))]
            if not participant:result['style']=auth['style']
            open_row=db.execute("SELECT id FROM conversations WHERE tester_id=? AND style=? AND status='open'",(t['id'],auth['style'])).fetchone()
            result['open_conversation']=open_row['id'] if open_row else None
            pending=db.execute("SELECT c.id FROM conversations c JOIN chat_meta x ON x.conversation_id=c.id WHERE c.tester_id=? AND c.status='completed' AND x.rated IS NULL ORDER BY c.ended DESC LIMIT 1",(t['id'],)).fetchone()
            result['pending_rating']=pending['id'] if pending else None
            if cid:
                c=self.conversation(db,auth,cid,True);messages=[dict(r) for r in db.execute('SELECT seq,role,text,status,request_id,model FROM messages WHERE conversation_id=? ORDER BY seq',(cid,))]
                result['conversation']={k:c[k] for k in ['id','status','started','ended']};result['conversation']['older_prompts']=c['prompt_version']!=digest(json.dumps(PROMPTS,sort_keys=True));result['messages']=messages
                record=next((r for r in result['conversations'] if r['id']==cid),{})
                result['conversation'].update(number=record.get('number'),title=record.get('title',''))
                result['memories']=[] if participant else [{'id':n['memory_id'],'completed_at':n['completed_at']} for n in self.selected_notes(db,c)]
                meta=db.execute('SELECT chat_type FROM chat_meta WHERE conversation_id=?',(cid,)).fetchone()
                result['conversation']['chat_type']=meta['chat_type'] if meta else None
                result['min_messages']=self.cfg.get('min_guided_messages',6) if meta and meta['chat_type'] in ('first','final') else 1
                result['turns']=sum(m['role']=='user' and m['status']=='success' and not m['request_id'].startswith('correction') for m in messages)
            return result
    def study_materials(self,db):
        row=db.execute("SELECT value FROM settings WHERE key='study_materials'").fetchone()
        return json.loads(row['value']) if row else {'instructions':'','baseline_url':'','final_url':''}
    def set_study_materials(self,data):
        from urllib.parse import urlsplit
        material={key:data.get(key,'') for key in ('instructions','baseline_url','final_url')}
        if any(not isinstance(value,str) for value in material.values()):raise Error('Study materials must be text.')
        if len(material['instructions'])>3000:raise Error('Keep instructions under 3,000 characters.')
        for key in ('baseline_url','final_url'):
            url=material[key].strip();material[key]=url
            parsed=urlsplit(url)
            if url and (len(url)>1500 or parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password):raise Error('Questionnaire links must be complete HTTPS URLs without credentials.')
        with self.storage.connect() as db:
            db.execute("INSERT INTO settings(key,value) VALUES('study_materials',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(material),))
            self.event(db,None,None,'study_materials_updated')
        return {'ok':True}
    def rename(self,auth,cid,title):
        if not isinstance(title,str) or len(title.strip())>80:raise Error('Use a title of up to 80 characters.')
        with self.storage.connect() as db:
            c=self.conversation(db,auth,cid,True)
            self.event(db,c['tester_id'],cid,'conversation_title',title.strip())
        return {'ok':True}
    def archive_view(self,auth,cid):
        with self.storage.connect() as db:
            c=self.conversation(db,auth,cid,True)
            self.event(db,c['tester_id'],cid,'archive_viewed')
        return {'ok':True}
    def correct_detail(self,auth,cid,text):
        """Same repair affordance in both arms; exclude supplied notes, never rewrite raw history."""
        if not isinstance(text,str) or not 1<=len(text.strip())<=1000:raise Error('Write the correction in 1–1,000 characters.')
        mutex=self.lock(cid)
        if not mutex.acquire(False):raise Error('Wait for the current reply before correcting a detail.',409)
        try:
            with self.storage.connect() as db:
                c=self.conversation(db,auth,cid)
                if c['status']!='open':raise Error('Corrections can be added to an open conversation.',409)
                if db.execute("SELECT 1 FROM messages WHERE conversation_id=? AND role='user' AND status!='success'",(cid,)).fetchone():raise Error('Retry the unanswered message first.',409)
                refs=json.loads(c['memory_refs'])
                for mid in refs:
                    db.execute("UPDATE memories SET status='excluded',error='participant_detail_correction' WHERE id=? AND conversation_id IN (SELECT id FROM conversations WHERE tester_id=? AND style=?)",(mid,c['tester_id'],c['style']))
                # Keep the initial references for exposure/audit; selected_notes excludes invalidated notes.
                seq=db.execute('SELECT MAX(seq)+1 FROM messages WHERE conversation_id=?',(cid,)).fetchone()[0]
                db.execute('INSERT INTO messages(conversation_id,seq,role,text,status,request_id,created,flags) VALUES(?,?,?,?,?,?,?,?)',(cid,seq,'user','Correction: '+text.strip(),'success',uid('correction'),time.time(),'memory_correction'))
                self.event(db,c['tester_id'],cid,'participant_detail_correction',json.dumps({'excluded_refs':refs}))
        finally:mutex.release()
        return {'ok':True}
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
            try:
                with self.usage.reserve(c['tester_id'],'reply'):
                    reply=self.provider.reply(prompts,c['style'],notes,history)
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
                flags='over_60_words' if len(reply['text'].split())>60 else ''
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
                sent=db.execute("SELECT count(*) FROM messages WHERE conversation_id=? AND role='user' AND status='success' AND flags!='memory_correction'",(cid,)).fetchone()[0]
                if not sent:raise Error('Send at least one message before finishing.')
                meta=db.execute('SELECT chat_type FROM chat_meta WHERE conversation_id=?',(cid,)).fetchone()
                needed=self.cfg.get('min_guided_messages',6)
                if meta and meta['chat_type'] in ('first','final') and sent<needed:raise Error(f'In this session, please send at least {needed} messages before finishing ({sent} so far).',409)
                db.execute("UPDATE conversations SET status='completed',ended=? WHERE id=?",(time.time(),cid))
                db.execute('INSERT INTO memories(id,conversation_id,status,notes,schema_version,model,prompt_version,created,error) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(conversation_id) DO NOTHING',(uid('M'),cid,'pending',None,'1',self.cfg['model'],c['prompt_version'],time.time(),None))
                self.event(db,c['tester_id'],cid,'conversation_finished')
                if self.temporary:
                    db.execute('DELETE FROM conversations WHERE id=?',(cid,))
                    return {'ok':True,'memory_status':'disabled'}
        finally:mutex.release()
        return self.summarize(cid)
    def summarize(self,cid):
        if self.temporary:raise Error('Saved memory is disabled for temporary team testing.',409)
        mutex=self.lock('summary:'+cid)
        if not mutex.acquire(False):raise Error('Memory generation is already in progress.',409)
        try:
            with self.storage.connect() as db:
                c=db.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone();m=db.execute('SELECT * FROM memories WHERE conversation_id=?',(cid,)).fetchone()
                if not c or not m:raise Error('Summary unavailable.',404)
                if m['status'] in ('ready','excluded'):return {'ok':True,'memory_status':m['status']}
                transcript=[dict(r) for r in db.execute("SELECT role,text FROM messages WHERE conversation_id=? AND status='success' ORDER BY seq",(cid,))]
            try:
                with self.usage.reserve(c['tester_id'],'summary'):
                    notes=validate_notes(self.provider.summarize(json.loads(c['prompt_json']),transcript))
            except ProviderError as exc:
                with self.storage.connect() as db:
                    db.execute("UPDATE memories SET status='failed',error='summary_failed' WHERE conversation_id=? AND status!='excluded'",(cid,))
                return {'ok':True,'memory_status':'failed','warning':'Conversation saved; memory needs retry. '+str(exc)}
            with self.storage.connect() as db:
                changed=db.execute("UPDATE memories SET status='ready',notes=?,error=NULL WHERE conversation_id=? AND status IN ('pending','failed')",(json.dumps(notes,ensure_ascii=False),cid)).rowcount
                if changed:self.event(db,c['tester_id'],cid,'memory_ready')
                return {'ok':True,'memory_status':'ready' if changed else 'excluded'}
        finally:mutex.release()
    def rate(self,auth,cid,data):
        """After-chat ratings: distress now (0-100), support needed and felt understood (1-7). Saved once."""
        post=scale(data.get('post_distress'),0,100,'Choose how upset you feel now, from 0 to 100.')
        need=scale(data.get('support_needed'),1,7,'Answer each question from 1 to 7.')
        understood=scale(data.get('felt_understood'),1,7,'Answer each question from 1 to 7.')
        with self.storage.connect() as db:
            t=self.tester(db,auth,True)
            c=db.execute('SELECT c.status,x.rated FROM conversations c JOIN chat_meta x ON x.conversation_id=c.id WHERE c.id=? AND c.tester_id=?',(cid,t['id'])).fetchone()
            if not c or c['status']!='completed':raise Error('This chat cannot be rated.',409)
            if c['rated'] is None:
                db.execute('UPDATE chat_meta SET post_distress=?,support_needed=?,felt_understood=?,rated=? WHERE conversation_id=?',(post,need,understood,time.time(),cid))
                self.event(db,t['id'],cid,'rated')
        return {'ok':True}
    def stop(self,auth,cid,discard=False):
        with self.storage.connect() as db:
            c=self.conversation(db,auth,cid,True)
            if self.temporary:
                db.execute('DELETE FROM conversations WHERE id=?',(cid,));return {'ok':True}
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
            t=db.execute('SELECT locked FROM testers WHERE id=?',(tid,)).fetchone()
            if not t:raise Error('Unknown tester.',404)
            if t['locked']:raise Error('Study participants keep their memory as assigned. Memory reset is only for test accounts.',409)
            db.execute("UPDATE memories SET status='excluded',error='researcher_reset' WHERE conversation_id IN (SELECT id FROM conversations WHERE tester_id=? AND style=?)",(tid,style))
            db.execute("UPDATE conversations SET status='discarded',ended=? WHERE tester_id=? AND style=? AND status='open'",(time.time(),tid,style));self.event(db,tid,None,'memory_reset',style)
        return {'ok':True}
    def delete(self,tid):
        with self.storage.connect() as db:
            if not db.execute('DELETE FROM testers WHERE id=?',(tid,)).rowcount:raise Error('Unknown tester.',404)
        return {'ok':True}
    def set_paused(self,paused):
        if not isinstance(paused,bool):raise Error('A pause choice is required.')
        with self.storage.connect() as db:
            db.execute("INSERT INTO settings(key,value) VALUES('api_paused',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",('1' if paused else '0',))
        return {'ok':True}
    def assign(self,tid,style,memory=None):
        self.style(style)
        if memory is not None and memory not in MEMORY:raise Error('Choose persistent or fresh memory.')
        with self.storage.connect() as db:
            t=db.execute('SELECT locked,memory FROM testers WHERE id=?',(tid,)).fetchone()
            if not t:raise Error('Unknown tester.',404)
            if t['locked']:raise Error('Study participants keep their assigned condition. Only test accounts can be changed.',409)
            db.execute('UPDATE testers SET active_style=?,memory=? WHERE id=?',(style,memory or t['memory'],tid))
            # Revoke earlier tester sessions so the next sign-in uses the new style.
            db.execute("DELETE FROM logins WHERE tester_id=? AND role='tester'",(tid,))
            self.event(db,tid,None,'remote_style_assigned',style)
        return {'ok':True}
    def admin_state(self,role='admin'):
        with self.storage.connect() as db:
            testers=[]
            finished={}
            for c in db.execute("SELECT c.tester_id,x.chat_type,count(*) AS n FROM conversations c JOIN chat_meta x ON x.conversation_id=c.id WHERE c.status='completed' GROUP BY c.tester_id,x.chat_type").fetchall():
                finished.setdefault(c['tester_id'],{})[c['chat_type']]=c['n']
            for r in db.execute('SELECT id,created,consent,active_style,suspended,study_id,memory,locked FROM testers ORDER BY created').fetchall():
                row=dict(r)
                row['finished_chats']={k:finished.get(row['id'],{}).get(k,0) for k in CHAT_TYPES}
                if row['locked'] or role=='facilitator':row.pop('active_style');row.pop('memory')
                testers.append(row)
            unused=db.execute('SELECT count(*) FROM assignments WHERE assigned IS NULL').fetchone()[0]
            conversations=[dict(r) for r in db.execute('SELECT c.id,c.tester_id,c.style,c.status,c.started,c.ended,c.prompt_version,m.status AS memory_status,x.chat_type,x.rated FROM conversations c LEFT JOIN memories m ON m.conversation_id=c.id LEFT JOIN chat_meta x ON x.conversation_id=c.id ORDER BY c.started DESC')]
            if role=='facilitator':
                for row in conversations:row.pop('style');row.pop('prompt_version')
            return {'role':role,'database_backend':self.cfg.get('database_backend','sqlite'),'storage_mode':self.cfg.get('storage_mode','persistent'),'mode':self.cfg['mode'],'model':self.cfg['model'],'api_key_configured':self.cfg.get('api_key_configured',False),'usage':self.usage.state(),'unused_study_ids':unused,'testers':testers,'study_materials':self.study_materials(db),'conversations':conversations,'enrollment_ready':bool(self.enrollment_plan(db)),**({'allocation':self.allocation_report(db)} if role=='admin' else {})}
    def inspect(self,cid):
        with self.storage.connect() as db:
            c=db.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone()
            if not c:raise Error('Unknown conversation.',404)
            return {'conversation':dict(c),'messages':[dict(r) for r in db.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY seq',(cid,))], 'memory':dict(r) if (r:=db.execute('SELECT * FROM memories WHERE conversation_id=?',(cid,)).fetchone()) else None}
    def export(self):
        if self.temporary:raise Error('Record downloads are disabled for temporary team testing.',403)
        with self.storage.connect() as db:
            return {'mode':self.cfg['mode'],'exported_at':time.time(),'testers':[dict(r) for r in db.execute('SELECT id,created,consent,active_style,suspended,study_id,memory,locked FROM testers')],**{table:[dict(r) for r in db.execute('SELECT * FROM '+table)] for table in ['conversations','messages','memories','events','chat_meta','assignments']}}
    CHAT_COLUMNS=['study_id','tester_id','test_account','style','memory','conversation_id','chat_type','status','started_utc','ended_utc','minutes','user_messages','notes_used','pre_distress','post_distress','distress_change','support_needed','felt_understood','safety_stop','prompt_version','model']
    def export_chats(self):
        """One row per chat for analysis (CSV). Contains the condition: keep away from blind coders."""
        if self.temporary:raise Error('Record downloads are disabled for temporary team testing.',403)
        import csv,io
        from datetime import datetime,timezone
        iso=lambda x:datetime.fromtimestamp(x,timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if x else ''
        blank=lambda v:'' if v is None else v
        out=io.StringIO();w=csv.writer(out);w.writerow(self.CHAT_COLUMNS)
        with self.storage.connect() as db:
            safety={r['conversation_id'] for r in db.execute("SELECT conversation_id FROM events WHERE event IN ('safety_keyword_stop','model_safety_stop')").fetchall()}
            message_counts={r['conversation_id']:r['n'] for r in db.execute("SELECT conversation_id,count(*) AS n FROM messages WHERE role='user' AND status='success' AND flags!='memory_correction' GROUP BY conversation_id").fetchall()}
            rows=db.execute('SELECT c.*,t.study_id,t.memory,t.locked,x.chat_type,x.pre_distress,x.post_distress,x.support_needed,x.felt_understood FROM conversations c JOIN testers t ON t.id=c.tester_id LEFT JOIN chat_meta x ON x.conversation_id=c.id ORDER BY t.study_id,c.started').fetchall()
            for r in rows:
                n=message_counts.get(r['id'],0)
                change=r['post_distress']-r['pre_distress'] if r['post_distress'] is not None and r['pre_distress'] is not None else ''
                w.writerow([blank(r['study_id']),r['tester_id'],0 if r['locked'] else 1,r['style'],r['memory'],r['id'],blank(r['chat_type']),r['status'],iso(r['started']),iso(r['ended']),round((r['ended']-r['started'])/60,1) if r['ended'] else '',n,len(json.loads(r['memory_refs'])),
                            blank(r['pre_distress']),blank(r['post_distress']),change,blank(r['support_needed']),blank(r['felt_understood']),1 if r['id'] in safety else 0,r['prompt_version'][:12],r['model']])
        return out.getvalue()
