"""Persistent, atomic API-attempt quotas. No chat content or access codes."""
import hashlib,time
from contextlib import contextmanager
from .provider import ProviderError
DEFAULTS={'TESTER_DAILY_API_LIMIT':50,'GLOBAL_DAILY_API_LIMIT':250,'GLOBAL_TOTAL_API_LIMIT':500,'TESTER_MINUTE_API_LIMIT':3,'GLOBAL_CONCURRENT_API_LIMIT':5}
class UsageLimits:
    def __init__(self,storage,cfg):self.storage=storage;self.limits={**DEFAULTS,**cfg.get('limits',{})}
    @contextmanager
    def reserve(self,tester,kind):
        now=time.time();day=int(now//86400)*86400;tester_hash=hashlib.sha256(tester.encode()).hexdigest();limits=self.limits
        with self.storage.connect() as db:
            db.begin_serialized()
            paused=db.execute("SELECT value FROM settings WHERE key='api_paused'").fetchone()
            if paused and paused[0]=='1':raise ProviderError('AI requests are paused by the researcher. No request was sent.')
            # Single Gunicorn worker; these reservations also survive process restarts.
            # Provider network timeout is 55s. Leases expire after 120s for crashed requests.
            checks=[
                ('SELECT count(*) FROM api_attempts',(),limits['GLOBAL_TOTAL_API_LIMIT'],'This testing database has reached its total API-attempt limit.'),
                ('SELECT count(*) FROM api_attempts WHERE started>=?',(day,),limits['GLOBAL_DAILY_API_LIMIT'],'The app has reached its daily AI limit.'),
                ('SELECT count(*) FROM api_attempts WHERE tester_hash=? AND started>=?',(tester_hash,day),limits['TESTER_DAILY_API_LIMIT'],'Your daily AI limit has been reached.'),
                ('SELECT count(*) FROM api_attempts WHERE tester_hash=? AND started>?',(tester_hash,now-60),limits['TESTER_MINUTE_API_LIMIT'],'Please wait a minute before requesting another AI response.'),
                ("SELECT count(*) FROM api_attempts WHERE status='active' AND started>?",(now-120,),limits['GLOBAL_CONCURRENT_API_LIMIT'],'The AI service is busy. Please retry shortly.'),
                ("SELECT count(*) FROM api_attempts WHERE tester_hash=? AND status='active' AND started>?",(tester_hash,now-120),1,'An AI request for this tester is already running.')]
            for query,args,limit,message in checks:
                if db.execute(query,args).fetchone()[0]>=limit:raise ProviderError(message+' No request was sent.')
            attempt=db.execute("INSERT INTO api_attempts(tester_hash,kind,started,status) VALUES(?,?,?,'active') RETURNING id",(tester_hash,kind,now)).fetchone()[0]
        status='failed'
        try:
            yield
            status='completed'
        finally:
            with self.storage.connect() as db:db.execute('UPDATE api_attempts SET status=?,finished=? WHERE id=?',(status,time.time(),attempt))
    def state(self):
        day=int(time.time()//86400)*86400
        with self.storage.connect() as db:
            paused=db.execute("SELECT value FROM settings WHERE key='api_paused'").fetchone()
            return {'paused':bool(paused and paused[0]=='1'),'attempts_total':db.execute('SELECT count(*) FROM api_attempts').fetchone()[0],
                    'attempts_today':db.execute('SELECT count(*) FROM api_attempts WHERE started>=?',(day,)).fetchone()[0],'limits':self.limits}
