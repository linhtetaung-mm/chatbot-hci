"""Concealed, block-randomized 2x2 assignment list for the study.

  python3 tools/assignments.py generate --n 48            # writes private/assignments.csv (never overwrites)
  python3 tools/assignments.py load private/assignments.csv  # loads it into the database in your .env
  python3 tools/assignments.py status                      # how many study IDs are used / left

Every block of 4 study IDs contains each condition (Reassure/Guide x Persistent/Fresh) exactly once,
in random order. Scenario A/B alternates within each condition. Keep the CSV private: it reveals conditions.
"""
import argparse,csv,os,random,secrets,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
CONDITIONS=[('reassure','persistent'),('reassure','fresh'),('guide','persistent'),('guide','fresh')]
FIELDS=['study_id','seq','style','memory','scenario']

def generate(n,seed,prefix):
    rng=random.Random(seed);rows=[];seen={c:0 for c in CONDITIONS}
    while len(rows)<n:
        block=CONDITIONS[:];rng.shuffle(block)
        for style,memory in block:
            if len(rows)>=n:break
            scenario='AB'[seen[(style,memory)]%2]  # alternate A/B within each condition
            seen[(style,memory)]+=1
            rows.append({'study_id':f'{prefix}{len(rows)+1:02d}','seq':len(rows)+1,'style':style,'memory':memory,'scenario':scenario})
    return rows

def bot(mode):
    if mode:os.environ['CHATBOT_MODE']=mode
    from app.config import configuration
    from app.chatbot import Chatbot
    cfg=configuration()
    if cfg.get('storage_mode')!='persistent':raise SystemExit('Set STORAGE_MODE=persistent first; temporary storage would lose the list.')
    return Chatbot(cfg)

p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('action',choices=['generate','load','status'])
p.add_argument('file',nargs='?',default='private/assignments.csv')
p.add_argument('--n',type=int,default=48,help='Number of study IDs (use a multiple of 4).')
p.add_argument('--seed',type=int,help='Random seed. Default: a new secret random seed (recorded in the file name).')
p.add_argument('--prefix',default='P')
p.add_argument('--mode',choices=['setup','demo','live'],help='Override CHATBOT_MODE for this command only.')
a=p.parse_args()
if a.action=='generate':
    if a.n<4 or a.n%4:raise SystemExit('Use a multiple of 4 so every condition has the same number of IDs.')
    seed=a.seed if a.seed is not None else secrets.randbelow(10**9)
    path=Path(a.file)
    if path.exists():raise SystemExit(f'{path} already exists. Keep it; choose another file name if you really need a new list.')
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(generate(a.n,seed,a.prefix))
    os.chmod(path,0o600)
    Path(str(path)+'.seed').write_text(str(seed)+'\n')
    print(f'Wrote {a.n} study IDs to {path} (seed saved next to it). Keep this file private; do not open it in front of participants.')
elif a.action=='load':
    with open(a.file,newline='') as f:rows=list(csv.DictReader(f))
    if [r for r in rows if set(r)!=set(FIELDS)]:raise SystemExit('Unexpected columns in the assignment file.')
    b=bot(a.mode)
    try:print(f'Loaded {b.load_assignments(rows)} new study IDs ({len(rows)} in file; existing IDs are never changed).')
    finally:
        if hasattr(b.storage,'close'):b.storage.close()
else:
    b=bot(a.mode)
    try:
        with b.storage.connect() as db:
            total=db.execute('SELECT count(*) FROM assignments').fetchone()[0];used=db.execute('SELECT count(*) FROM assignments WHERE assigned IS NOT NULL').fetchone()[0]
        print(f'{used} of {total} study IDs used, {total-used} left.')
    finally:
        if hasattr(b.storage,'close'):b.storage.close()
