"""Local-only configuration. Never print credentials."""
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
    c['api_key_configured']=has_api_key(c['api_key'])
    return c
