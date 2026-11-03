"""Check local settings without making API requests or claiming readiness."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import configuration,has_api_key
try:
    c=configuration()
    print('Mode:',c['mode']);print('Model:',c['model']);print('Real API key supplied (not verified):',has_api_key(c['api_key']));print('Local address:',c['origin']);print('Database:',c['db'])
    if c['mode']=='setup':print('STATUS: API NOT CONNECTED. Interface placeholder only; no AI replies or summaries.')
    elif c['mode']=='demo':print('STATUS: SIMULATED EXAMPLES. This does not test real conversation or memory quality.')
    else:print('STATUS: LIVE SETTINGS PRESENT. Actual API access and response quality have not been verified by this check.')
    print('Phase 1 still requires live API checks, style/memory review and at least one supervised human usability test. No API request made.')
except ValueError as e:raise SystemExit(str(e))
