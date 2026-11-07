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
    hosted=os.getenv('DEPLOYMENT','local')=='render' or os.getenv('RENDER')=='true'
    origin=(os.getenv('PUBLIC_ORIGIN') or ('https://'+os.environ['RENDER_EXTERNAL_HOSTNAME'] if os.getenv('RENDER_EXTERNAL_HOSTNAME') else c['origin'])).rstrip('/')
    parsed=urlsplit(origin)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('PUBLIC_ORIGIN must be a plain origin, for example https://your-app.onrender.com.')
    if hosted:
        if parsed.scheme!='https':raise ValueError('Render requires an HTTPS PUBLIC_ORIGIN.')
        if storage_mode=='persistent' and (not Path(c['db']).is_absolute() or not str(Path(c['db']).resolve()).startswith('/var/data/')):
            raise ValueError('Render CHATBOT_DB must be inside the persistent disk at /var/data/.')
        if storage_mode=='persistent' and not Path('/var/data').is_mount():raise ValueError('Attach a Render persistent disk at /var/data before starting.')
    limits={}
    for name,default in {'TESTER_DAILY_API_LIMIT':50,'GLOBAL_DAILY_API_LIMIT':250,'GLOBAL_TOTAL_API_LIMIT':500,'TESTER_MINUTE_API_LIMIT':3,'GLOBAL_CONCURRENT_API_LIMIT':5,'TESTER_DAILY_CHAT_LIMIT':4}.items():
        value=int(os.getenv(name,str(default)))
        if value<1:raise ValueError(name+' must be a positive integer.')
        limits[name]=value
    c.update(origin=origin,hosted=hosted,secure_cookie=parsed.scheme=='https',allowed_host=parsed.netloc,limits=limits)
    c['api_key_configured']=has_api_key(c['api_key'])
    return c
