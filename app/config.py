"""Local and hosted configuration. Never print credentials."""
from urllib.parse import urlsplit
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load_env():
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text().splitlines():
            line=line.strip()
            if line and not line.startswith('#') and '=' in line:
                k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('\"').strip("'"))
API_KEY_PLACEHOLDER='PASTE_YOUR_OPENAI_API_KEY_HERE'
def has_api_key(value):
    """Recognise missing/example values without relying on one key prefix."""
    if not isinstance(value,str):return False
    value=value.strip()
    if not value:return False
    lowered=value.lower()
    return lowered not in {'sk-...','your-private-api-key','your_api_key','your_openai_api_key','your_openai_api_key_here','paste_your_openai_api_key_here'} and not lowered.startswith(('replace','placeholder','paste_','your-'))

def configuration():
    load_env();mode=os.getenv('CHATBOT_MODE','setup');port=int(os.getenv('PORT','8766'))
    if mode not in ('setup','demo','live'):raise ValueError('CHATBOT_MODE must be setup, demo or live.')
    if not 1024<=port<=65535:raise ValueError('Choose PORT from 1024 to 65535.')
    key=os.getenv('ADMIN_KEY','')
    if len(key)<24 or key.startswith('replace'):raise ValueError('Run python3 setup_local.py first to create your private settings.')
    c={'mode':mode,'port':port,'origin':f'http://127.0.0.1:{port}','admin_key':key,
       'api_key':os.getenv('OPENAI_API_KEY','').strip(),'model':(os.getenv('OPENAI_MODEL') or 'gpt-6-luna'),
       'reasoning':os.getenv('OPENAI_REASONING_EFFORT','none'),'contact':(os.getenv('RESEARCHER_CONTACT') or 'The researcher supervising this test'),
       'support':os.getenv('SUPPORT_CONTACTS','Ask your supervising researcher for local support contacts.'),
       'delete_date':os.getenv('DELETE_DATE','2026-12-19'),
       'db':str(ROOT/(os.getenv('CHATBOT_DB') or f'data/chatbots-{mode}.sqlite3'))}
    if mode=='live' and not has_api_key(c['api_key']):raise ValueError('OpenAI API key is missing or still a placeholder. Add your real key privately to .env, or use CHATBOT_MODE=setup. No API request was sent.')
    if mode=='live' and (not has_api_key(c['api_key']) or not os.getenv('RESEARCHER_CONTACT') or os.getenv('HUMAN_TEST_REVIEW')!='confirmed'):
        raise ValueError('Live mode needs OPENAI_API_KEY, RESEARCHER_CONTACT and HUMAN_TEST_REVIEW=confirmed after the applicable course review.')
    storage_mode=os.getenv('STORAGE_MODE','temporary')
    if storage_mode not in ('temporary','persistent'):raise ValueError('STORAGE_MODE must be temporary or persistent.')
    c['storage_mode']=storage_mode
    backend=os.getenv('DATABASE_BACKEND','sqlite').strip().lower()
    if backend not in ('sqlite','supabase'):raise ValueError('DATABASE_BACKEND must be sqlite or supabase.')
    schema=os.getenv('DATABASE_SCHEMA','').strip() or 'hci_'+mode
    import re
    if not re.fullmatch(r'hci_[a-z0-9_]{1,48}',schema):raise ValueError('DATABASE_SCHEMA must start with hci_ and contain only lowercase letters, digits and underscores.')
    c.update(database_backend=backend,database_url=os.getenv('DATABASE_URL','').strip(),database_schema=schema,
             database_sslrootcert=os.getenv('DATABASE_SSLROOTCERT','system').strip() or 'system')
    if backend=='supabase':
        if storage_mode!='persistent':raise ValueError('Supabase requires STORAGE_MODE=persistent; temporary mode would discard chats.')
        from .postgres import validate_database_url
        validate_database_url(c['database_url'])
    hosted=os.getenv('DEPLOYMENT','local')=='render' or os.getenv('RENDER')=='true'
    origin=(os.getenv('PUBLIC_ORIGIN') or ('https://'+os.environ['RENDER_EXTERNAL_HOSTNAME'] if os.getenv('RENDER_EXTERNAL_HOSTNAME') else c['origin'])).rstrip('/')
    parsed=urlsplit(origin)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('PUBLIC_ORIGIN must be a plain origin, for example https://your-app.onrender.com.')
    if hosted:
        if parsed.scheme!='https':raise ValueError('Render requires an HTTPS PUBLIC_ORIGIN.')
        if backend=='sqlite' and storage_mode=='persistent' and (not Path(c['db']).is_absolute() or not str(Path(c['db']).resolve()).startswith('/var/data/')):
            raise ValueError('Render CHATBOT_DB must be inside the persistent disk at /var/data/.')
        if backend=='sqlite' and storage_mode=='persistent' and not Path('/var/data').is_mount():raise ValueError('Attach a Render persistent disk at /var/data before starting.')
    limits={}
    for name,default in {'TESTER_DAILY_API_LIMIT':80,'GLOBAL_DAILY_API_LIMIT':800,'GLOBAL_TOTAL_API_LIMIT':3000,'TESTER_MINUTE_API_LIMIT':6,'GLOBAL_CONCURRENT_API_LIMIT':12,'TESTER_DAILY_CHAT_LIMIT':6}.items():
        value=int(os.getenv(name,str(default)))
        if value<1:raise ValueError(name+' must be a positive integer.')
        limits[name]=value
    # Study settings: how long a sign-in lasts (participants use their own phone for several days)
    # and the minimum number of participant messages before Finish in the two guided chats.
    session_hours=int(os.getenv('SESSION_HOURS','168'))
    if not 1<=session_hours<=336:raise ValueError('SESSION_HOURS must be between 1 and 336.')
    min_guided=int(os.getenv('MIN_GUIDED_MESSAGES','6'))
    if not 1<=min_guided<=20:raise ValueError('MIN_GUIDED_MESSAGES must be between 1 and 20.')
    # Hosted: wait up to 90 s for the previous copy to release the database during a deploy. Local/tools: fail at once.
    c['database_lock_wait']=float(os.getenv('DATABASE_LOCK_WAIT','90' if hosted else '0'))
    c.update(origin=origin,hosted=hosted,secure_cookie=parsed.scheme=='https',allowed_host=parsed.netloc,limits=limits,session_hours=session_hours,min_guided_messages=min_guided)
    import json
    try:accounts=json.loads(os.getenv('RESEARCHER_ACCOUNTS_JSON','[]'))
    except ValueError:raise ValueError('RESEARCHER_ACCOUNTS_JSON must be a JSON list.')
    if not isinstance(accounts,list):raise ValueError('Researcher accounts must be a list.')
    names=set();keys={key}
    for account in accounts:
        if not isinstance(account,dict) or set(account)!={'name','role','key'}:raise ValueError('Each researcher account needs name, role and key.')
        if not isinstance(account['name'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',account['name']) or account['name'] in names:raise ValueError('Use unique short researcher account names.')
        if account['role'] not in ('admin','facilitator') or not isinstance(account['key'],str) or len(account['key'])<24 or account['key'] in keys:raise ValueError('Use an admin/facilitator role and a unique researcher key of at least 24 characters.')
        names.add(account['name']);keys.add(account['key'])
    c['researcher_accounts']=accounts
    c['api_key_configured']=has_api_key(c['api_key'])
    return c
