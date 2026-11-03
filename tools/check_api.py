"""Six synthetic API calls only with --execute. No tester data is used."""
import argparse,sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import configuration
from app.chatbot import PROMPTS
from app.provider import Provider,ProviderError
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
if not a.execute:
    print('Dry run: six synthetic requests planned (reply, summary, return reply for each style). --execute may incur API charges. No requests made.')
    raise SystemExit(0)
c=configuration()
if c['mode']!='live':raise SystemExit('Configure live mode and a real key first. Setup/demo results are never treated as a successful API test.')
provider=Provider(c);checks=[]
try:
    for style in ['reassure','guide']:
        history=[{'role':'user','text':'My group presentation was postponed and I felt disappointed after preparing.'}]
        reply=provider.reply(PROMPTS,style,[],history)
        notes=provider.summarize(PROMPTS,history+[{'role':'assistant','text':reply['text']}])
        context=[{'memory_id':'synthetic-check','completed_at':time.time(),'notes':notes}]
        returned=provider.reply(PROMPTS,style,context,[{'role':'user','text':'Last time I mentioned a presentation. Do you remember what happened?'}])
        checks.append({'style':style,'first_reply':reply,'summary':notes,'return_reply':returned})
        print(style,'| actual model:',reply['model']);print('First reply:',reply['text']);print('Summary:',json.dumps(notes,ensure_ascii=False));print('Return reply:',returned['text'])
    path=Path(__file__).resolve().parents[1]/'private/api-check.json';path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({'checked_at':time.time(),'configured_model':c['model'],'synthetic_only':True,'checks':checks,'human_review_required':True},indent=2));path.chmod(0o600)
    print('Six API calls completed; synthetic evidence saved to private/api-check.json. Inspect accuracy, style and recall yourself. This does not certify Phase 1 completion.')
except ProviderError as exc:raise SystemExit(str(exc)+' Some earlier requests may have incurred charges; no success receipt was saved for this run.')
