"""Study-version checks: locked 2x2 assignment, memory condition, ratings, chat types and neutral participant view."""
import csv,io,json,sqlite3,tempfile,unittest,uuid,sys
from pathlib import Path
from app.chatbot import Chatbot,Error
from tests.test_chatbot import FakeProvider
CONSENT=dict.fromkeys(['adult','mild','voluntary','data_consent'],True)
def assignment_rows():
    rows=[]
    for i,(style,memory) in enumerate([('guide','fresh'),('reassure','persistent'),('guide','persistent'),('reassure','fresh')],1):
        rows.append({'study_id':f'P{i:02d}','seq':i,'style':style,'memory':memory,'scenario':'A' if i%2 else 'B'})
    return rows
class StudyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.cfg={'mode':'demo','model':'gpt-6-luna','reasoning':'none','db':self.tmp.name+'/study.sqlite3','admin_key':'UNIT-TEST-ONLY-ADMIN-SECRET-12345','api_key':'','port':8766,'origin':'http://127.0.0.1:8766','contact':'team@example.invalid','support':'Hotline 1323','delete_date':'2026-12-19','limits':{'TESTER_MINUTE_API_LIMIT':1000,'TESTER_DAILY_CHAT_LIMIT':1000},'min_guided_messages':3}
        self.p=FakeProvider();self.bot=Chatbot(self.cfg,self.p);self.assertEqual(self.bot.load_assignments(assignment_rows()),4)
    def tearDown(self):self.tmp.cleanup()
    def participant(self):
        e=self.bot.enroll();a=self.bot.authenticate(self.bot.login(e['code']));self.bot.consent(a,CONSENT);return e,a
    def chat(self,a,chat_type='home',messages=1,rate=True):
        cid=self.bot.start(a,chat_type,40)['id']
        for _ in range(messages):self.bot.send(a,cid,'My teammate ignored my idea.',str(uuid.uuid4()))
        self.bot.finish(a,cid)
        if rate:self.bot.rate(a,cid,{'post_distress':20,'support_needed':6,'felt_understood':5})
        return cid
    def test_enroll_follows_list_order_and_locks_condition(self):
        e,a=self.participant();self.assertEqual(e['study_id'],'P01');self.assertEqual(a['style'],'guide')
        with self.assertRaises(Error):self.bot.assign(e['id'],'reassure')
        with self.assertRaises(Error):self.bot.reset(e['id'],'guide')
        self.assertEqual(self.bot.authenticate(self.bot.handoff(e['id'],'reassure'))['style'],'guide')
        for expected in ['P02','P03','P04']:self.assertEqual(self.bot.enroll()['study_id'],expected)
        with self.assertRaises(Error):self.bot.enroll()
    def test_fresh_never_receives_notes_and_persistent_does(self):
        fresh_e,fresh=self.participant();pers_e,pers=self.participant()
        for a in (fresh,pers):self.chat(a);self.chat(a)
        fc=self.bot.start(fresh,'home',30)['id'];pc=self.bot.start(pers,'home',30)['id']
        self.p.calls.clear()
        self.bot.send(fresh,fc,'Hello again',str(uuid.uuid4()));self.assertEqual(self.p.calls[-1]['notes'],[])
        self.bot.send(pers,pc,'Hello again',str(uuid.uuid4()));self.assertEqual(len(self.p.calls[-1]['notes']),2)
        self.assertEqual(json.loads(self.bot.inspect(fc)['conversation']['memory_refs']),[])
        with self.bot.storage.connect() as db:self.assertEqual(db.execute("SELECT count(*) FROM memories m JOIN conversations c ON c.id=m.conversation_id WHERE c.tester_id=? AND m.status='ready'",(fresh_e['id'],)).fetchone()[0],2)
    def test_ratings_are_required_and_saved_once(self):
        e,a=self.participant()
        with self.assertRaises(Error):self.bot.start(a)
        with self.assertRaises(Error):self.bot.start(a,'home',101)
        cid=self.chat(a,rate=False);self.assertEqual(self.bot.state(a)['pending_rating'],cid)
        with self.assertRaises(Error):self.bot.rate(a,cid,{'post_distress':20,'support_needed':8,'felt_understood':5})
        self.bot.rate(a,cid,{'post_distress':10,'support_needed':6,'felt_understood':5});self.bot.rate(a,cid,{'post_distress':90,'support_needed':1,'felt_understood':1})
        self.assertIsNone(self.bot.state(a)['pending_rating'])
        with self.bot.storage.connect() as db:r=db.execute('SELECT * FROM chat_meta WHERE conversation_id=?',(cid,)).fetchone()
        self.assertEqual((r['chat_type'],r['pre_distress'],r['post_distress'],r['support_needed']),('home',40,10,6))
    def test_minimum_messages_only_for_guided_chats(self):
        e,a=self.participant();cid=self.bot.start(a,'first',50)['id']
        self.bot.send(a,cid,'One',str(uuid.uuid4()))
        with self.assertRaises(Error):self.bot.finish(a,cid)
        for t in ('Two','Three'):self.bot.send(a,cid,t,str(uuid.uuid4()))
        self.bot.finish(a,cid);self.bot.rate(a,cid,{'post_distress':10,'support_needed':4,'felt_understood':4})
        self.chat(a,'home',1)
    def test_participant_view_is_neutral(self):
        e,a=self.participant();self.chat(a);cid=self.bot.start(a,'home',30)['id'];s=self.bot.state(a,cid)
        self.assertEqual(s['bot_name'],'Chatbot');self.assertNotIn('style',s);self.assertEqual(s['memories'],[]);self.assertEqual(s['conversations'],[])
        self.assertNotIn('guide',json.dumps(s).lower());self.assertNotIn('reassure',json.dumps(s).lower())
        admin=self.bot.admin_state();row=[t for t in admin['testers'] if t['id']==e['id']][0];self.assertNotIn('memory',row);self.assertNotIn('active_style',row)
    def test_short_codes_are_forgiving(self):
        e=self.bot.enroll();self.assertRegex(e['code'],r'^[A-Z2-9]{4}-[A-Z2-9]{4}$')
        self.bot.authenticate(self.bot.login(e['code'].replace('-','').lower()))
        self.bot.authenticate(self.bot.login(' '+e['code'].lower()+' '))
    def test_chat_csv_export(self):
        e,a=self.participant();self.chat(a,'home',2)
        rows=list(csv.DictReader(io.StringIO(self.bot.export_chats())))
        self.assertEqual(rows[0]['study_id'],'P01');self.assertEqual(rows[0]['distress_change'],'-20');self.assertEqual(rows[0]['user_messages'],'2');self.assertEqual(rows[0]['memory'],'fresh')
    def test_old_schema_is_upgraded_in_place(self):
        path=self.tmp.name+'/old.sqlite3';db=sqlite3.connect(path)
        from app.storage import SCHEMA
        db.executescript(SCHEMA);db.execute("INSERT INTO settings VALUES('schema','1'),('mode','demo'),('model','gpt-6-luna')")
        db.execute("INSERT INTO testers VALUES('Told','x',1.0,NULL,'guide',0)");db.commit();db.close()
        b=Chatbot({**self.cfg,'db':path},self.p)
        with b.storage.connect() as d:
            row=d.execute("SELECT * FROM testers WHERE id='Told'").fetchone();self.assertEqual((row['memory'],row['locked']),('persistent',0))
            self.assertEqual(d.execute("SELECT value FROM settings WHERE key='schema'").fetchone()[0],'2')
    def test_assignment_generator_is_balanced(self):
        sys.argv=['x'];src=Path('tools/assignments.py').read_text().split('p=argparse.ArgumentParser')[0];ns={'__file__':'tools/assignments.py'};exec(src,ns)
        rows=ns['generate'](48,11,'P')
        for i in range(0,48,4):self.assertEqual(len({(r['style'],r['memory']) for r in rows[i:i+4]}),4)
    def test_greeting_comes_from_the_same_set_for_every_condition(self):
        from app.chatbot import GREETINGS
        for _ in range(4):
            e,a=self.participant();cid=self.bot.start(a,'home',20)['id'];self.assertIn(self.bot.state(a,cid)['messages'][0]['text'],GREETINGS)
    def test_combine_tool_normalises_ids(self):
        from tools.combine_data import norm_id,kappa
        for raw in ['p7','P07',' P 07','p007']:self.assertEqual(norm_id(raw),'P07')
        self.assertAlmostEqual(kappa([0,1,2,3],[0,1,2,3]),1.0)

    def test_cannot_bypass_pending_participant_ratings(self):
        e,a=self.participant();cid=self.chat(a,rate=False)
        with self.assertRaisesRegex(Error,'three questions'):self.bot.start(a,'home',30)
        self.bot.rate(a,cid,{'post_distress':20,'support_needed':6,'felt_understood':5})
        self.assertIn('id',self.bot.start(a,'home',30))

    def test_resume_and_invalid_start_do_not_retry_summaries(self):
        from unittest.mock import patch
        e=self.bot.enroll();a=self.bot.authenticate(self.bot.login(e['code']))
        with patch.object(self.bot,'retry_pending_summaries') as retry:
            with self.assertRaises(Error):self.bot.start(a,'home',30)
            retry.assert_not_called()
            self.bot.consent(a,CONSENT);cid=self.bot.start(a,'home',30)['id']
            retry.assert_called_once();retry.reset_mock()
            self.assertEqual(self.bot.start(a,'home',30),{'id':cid,'resumed':True})
            retry.assert_not_called()

    def test_replacing_lost_code_preserves_assignment_and_records(self):
        e,a=self.participant();cid=self.chat(a);token=self.bot.login(e['code'])
        replacement=self.bot.reissue_code(e['id'])
        with self.assertRaises(Error):self.bot.login(e['code'])
        with self.assertRaises(Error):self.bot.authenticate(token)
        new_auth=self.bot.authenticate(self.bot.login(replacement['code']))
        self.assertEqual(new_auth['style'],a['style'])
        self.assertEqual(self.bot.state(new_auth,cid)['study_id'],e['study_id'])
        self.assertEqual(self.bot.inspect(cid)['conversation']['status'],'completed')
        with self.bot.storage.connect() as db:
            row=db.execute('SELECT study_id,memory,locked FROM testers WHERE id=?',(e['id'],)).fetchone()
            self.assertEqual((row['study_id'],row['memory'],row['locked']),(e['study_id'],'fresh',1))
            self.assertEqual(db.execute('SELECT count(*) FROM testers').fetchone()[0],1)
            self.assertNotIn(replacement['code'],json.dumps(self.bot.export()))

    def test_admin_finished_counts_include_all_types_and_zero_counts(self):
        e,a=self.participant();self.chat(a,'first',3);self.chat(a,'home',2)
        other=self.bot.enroll()
        people={p['id']:p for p in self.bot.admin_state()['testers']}
        self.assertEqual(people[e['id']]['finished_chats'],{'first':1,'home':1,'final':0})
        self.assertEqual(people[other['id']]['finished_chats'],{'first':0,'home':0,'final':0})
    def test_more_ids_can_be_added_later_and_deleted_ids_are_not_reused(self):
        e,a=self.participant();self.bot.delete(e['id'])
        for _ in range(3):self.bot.enroll()
        with self.assertRaises(Error):self.bot.enroll()
        r=self.bot.add_study_ids(4);self.assertEqual((r['added'],r['first'],r['last']),(4,'P05','P08'))
        ids=[self.bot.enroll()['study_id'] for _ in range(4)];self.assertEqual(ids,['P05','P06','P07','P08'])
        with self.bot.storage.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM assignments WHERE seq>4").fetchone()[0],4)
            self.assertIsNone(db.execute("SELECT tester_id FROM assignments WHERE study_id='P01'").fetchone()[0])
        second=[dict(r,study_id='Q'+r['study_id'][1:]) for r in assignment_rows()]
        self.assertEqual(self.bot.load_assignments(second),4)
        with self.assertRaises(Error):self.bot.add_study_ids(5)
if __name__=='__main__':unittest.main()
