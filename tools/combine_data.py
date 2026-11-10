"""Turn the downloads into analysis-ready tables (standard library only; output opens in Excel).

Step 1, blind the scenario answers for the two coders (after the last final session):
  python3 tools/combine_data.py blind --final final.csv
    -> private/analysis/coders_scenarios.csv  (give ONLY this to the coders: code, scenario, answer)
    -> private/analysis/coders_key.csv        (keep private: code -> study ID)
  Collect scores independently, then merge by code: coder1, coder2 (0-3) and final (agreed score).

Step 2, combine everything:
  python3 tools/combine_data.py combine --chats chats.csv --baseline baseline.csv --final final.csv \\
      [--scores coders_scored.csv]
    -> private/analysis/chat_level.csv    one row per finished chat (for H1)
    -> private/analysis/person_level.csv  one row per participant: chat averages + counts + both forms + scenario score (H2-H6)
  Add --participants private-chatbot-records.json to retain enrolled people with zero chats.
  It also prints unweighted Cohen's kappa for the coders, a check of missing/duplicate study IDs, and averages per condition.

chats.csv = researcher page -> "One row per chat (CSV)". baseline.csv / final.csv = Google Sheets -> File -> Download -> CSV.
The study-ID column is found by a header containing "study id"; override with --id-column.
"""
import argparse,csv,json,math,os,random,re,statistics,sys
from collections import defaultdict
from pathlib import Path

def norm_id(v):
    v=re.sub(r'\s+','',str(v or '')).upper()
    m=re.fullmatch(r'([A-Z]+)0*(\d+)',v)
    return f'{m.group(1)}{int(m.group(2)):02d}' if m else v

def read(path):
    with open(path,newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def find_col(rows,needle,override=None,required=True,path=''):
    cols=list(rows[0]) if rows else []
    if override:
        if override not in cols:raise SystemExit(f'Column not found in {path}: {override}')
        return override
    hits=[c for c in cols if needle in c.lower()]
    if not hits and required:raise SystemExit(f'No column containing "{needle}" in {path}. Use the option to name it. Columns: {cols}')
    if len(hits)>1 and required:raise SystemExit(f'Multiple columns match {needle!r} in {path}; specify the exact column name.')
    return hits[0] if hits else None

def write(path,rows,cols,exclusive=False):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    flags=os.O_WRONLY|os.O_CREAT|(os.O_EXCL if exclusive else os.O_TRUNC)
    fd=os.open(path,flags,0o600)
    os.fchmod(fd,0o600)
    with os.fdopen(fd,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
    print('wrote',path,f'({len(rows)} rows)')

def by_id(rows,idcol,label):
    out={}
    for r in rows:
        sid=norm_id(r.get(idcol))
        if not sid:continue
        if sid in out:print(f'WARNING: {sid} appears more than once in the {label} form; the LAST response is used.')
        out[sid]=r
    return out

def num(v):
    try:
        value=float(v)
        return value if math.isfinite(value) else None
    except (TypeError,ValueError):return None

def mean(vals):
    vals=[v for v in vals if v is not None]
    return round(statistics.mean(vals),2) if vals else ''

def kappa(a,b):
    if len(a)!=len(b):raise ValueError('Coder score lists must have the same length.')
    n=len(a)
    if not n:return None
    po=sum(x==y for x,y in zip(a,b))/n;cats=set(a)|set(b)
    pe=sum((a.count(c)/n)*(b.count(c)/n) for c in cats)
    return None if pe==1 else (po-pe)/(1-pe)

def score(value,code,column):
    if value is None or str(value).strip()=='':return None
    n=num(value)
    if n is None or not n.is_integer() or not 0<=n<=3:
        raise SystemExit(f'Invalid {column} score for {code}: expected an integer from 0 to 3.')
    return int(n)

def blind(args):
    rows=read(args.final);idc=find_col(rows,'study id',args.id_column,path=args.final)
    if args.answer_column:
        answers=[find_col(rows,'',args.answer_column,path=args.final)]
    else:
        answers=[c for c in rows[0] if 'imagine this happened' in c.lower()]
        if not answers:raise SystemExit('No scenario-answer columns found. Use --answer-column with the exact header.')
    letter=find_col(rows,'scenario',args.scenario_column,required=False,path=args.final)
    if letter in answers:letter=None
    # Apply the same existing duplicate policy as combine: last exported response per ID.
    people=by_id(rows,idc,'final');items=[];rng=random.SystemRandom()
    if len(people)>900:raise SystemExit('This coding export supports up to 900 unique study IDs.')
    codes=rng.sample(range(100,1000),len(people))
    for (sid,r),code in zip(people.items(),codes):
        present=[c for c in answers if r.get(c,'').strip()]
        if len(present)!=1:
            raise SystemExit(f'{sid}: expected exactly one non-empty scenario answer; found {len(present)}. Check form branching or specify --answer-column.')
        items.append({'code':f'S{code}','study_id':sid,'scenario':(r.get(letter) or '').strip()[:1].upper() if letter else '','answer':r[present[0]].strip()})
    rng.shuffle(items)
    out=Path(args.out)
    # Never silently replace the random key after coders have received their file.
    if any((out/name).exists() for name in ('coders_scenarios.csv','coders_key.csv')):
        raise SystemExit('Coding files already exist. Keep the original key, or choose a new --out directory for a separate run.')
    write(out/'coders_scenarios.csv',items,['code','scenario','answer'],exclusive=True)
    write(out/'coders_key.csv',items,['code','study_id'],exclusive=True)
    print('Give ONLY coders_scenarios.csv to the coders. Keep coders_key.csv private and unchanged.')

def roster(path):
    if not path:return {}
    if Path(path).suffix.lower()=='.json':
        with open(path,encoding='utf-8') as f:rows=json.load(f)['testers']
    else:rows=read(path)
    result={}
    for r in rows:
        if str(r.get('locked','1')).lower() not in ('1','true'):continue
        sid=norm_id(r.get('study_id'))
        if not sid:continue
        if sid in result:raise SystemExit(f'Duplicate study ID in participant roster: {sid}')
        result[sid]={'style':r.get('active_style',r.get('style','')),'memory':r.get('memory','')}
    return result

def combine(args):
    chats=[r for r in read(args.chats) if r.get('test_account','0')=='0']
    finished=[r for r in chats if r['status']=='completed']
    out=Path(args.out)
    chat_cols=['study_id','style','memory','chat_type','started_utc','minutes','user_messages','notes_used','pre_distress','post_distress','distress_change','support_needed','felt_understood','safety_stop']
    for r in chats:r['study_id']=norm_id(r['study_id'])
    people=defaultdict(list)
    for r in chats:people[norm_id(r['study_id'])].append(r)
    base=read(args.baseline) if args.baseline else [];fin=read(args.final) if args.final else []
    bmap=by_id(base,find_col(base,'study id',args.id_column,path=args.baseline),'baseline') if base else {}
    fmap=by_id(fin,find_col(fin,'study id',args.id_column,path=args.final),'final') if fin else {}
    enrolled=roster(args.participants)
    # Keep enrolled people with zero chats and form-only IDs visible; do not invent their condition.
    for sid in set(enrolled)|set(bmap)|set(fmap):people.setdefault(sid,[])
    scores={}
    if args.scores:
        srows=read(args.scores);key_rows=read(args.key);key={r['code']:norm_id(r['study_id']) for r in key_rows}
        if len(key)!=len(key_rows):raise SystemExit('Duplicate codes in the private coding key.')
        if not all(key) or not all(key.values()) or len(set(key.values()))!=len(key):raise SystemExit('Missing or duplicate study IDs in the private coding key.')
        seen=set();pairs=[]
        for r in srows:
            code=r.get('code','')
            if code in seen:raise SystemExit(f'Duplicate scored code: {code}')
            if code not in key:raise SystemExit(f'Scored code is missing from the private key: {code}')
            seen.add(code)
            a=score(r.get('coder1'),code,'coder1');b=score(r.get('coder2'),code,'coder2')
            final=score(r.get('final'),code,'final')
            if a is not None and b is not None:pairs.append((a,b))
            if final is None and a is not None and a==b:final=a
            if final is not None:scores[key[code]]=final
            else:print(f"WARNING: no agreed 'final' score for {code}")
        if pairs:
            k=kappa([p[0] for p in pairs],[p[1] for p in pairs]);agree=sum(a==b for a,b in pairs)/len(pairs)
            label='undefined (no marginal variation)' if k is None else f'{k:.2f}'
            print(f"Coders: {len(pairs)} answers scored twice, exact agreement {agree:.0%}, unweighted Cohen's kappa {label}.")
            print('This is a descriptive check; use the reliability method specified in your approved analysis plan.')
    bcols=[c for c in (base[0] if base else {}) ];fcols=[c for c in (fin[0] if fin else {})]
    rows=[]
    for sid,rs in sorted(people.items()):
        done=[r for r in rs if r['status']=='completed']
        count=lambda t:sum(r['chat_type']==t for r in done)
        conditions={(r['style'],r['memory']) for r in rs}
        if len(conditions)>1:raise SystemExit(f'Conflicting conditions in chat export for {sid}. Check source records.')
        condition=enrolled.get(sid) or (rs[0] if rs else {})
        if rs and enrolled.get(sid) and any(condition.get(k)!=rs[0].get(k) for k in ('style','memory')):raise SystemExit(f'Roster and chats disagree for {sid}.')
        if not condition:print(f'CHECK: {sid} appears only in forms; its assignment is unknown. Verify the study ID against the enrollment record.')
        row={'study_id':sid,'style':condition.get('style',''),'memory':condition.get('memory',''),'first_chat_done':count('first'),'home_chats':count('home'),'final_chat_done':count('final'),
             'chats_finished':len(done),'chats_stopped':sum(r['status'] in ('stopped','discarded') for r in rs),'chats_open':sum(r['status']=='open' for r in rs),'safety_stop':int(any(r['safety_stop']=='1' for r in rs)),
             'avg_pre_distress':mean([num(r['pre_distress']) for r in done]),'avg_post_distress':mean([num(r['post_distress']) for r in done]),
             'avg_distress_change':mean([num(r['distress_change']) for r in done]),'avg_support_needed':mean([num(r['support_needed']) for r in done]),
             'avg_felt_understood':mean([num(r['felt_understood']) for r in done]),'scenario_score':scores.get(sid,''),
             'has_baseline':int(sid in bmap),'has_final':int(sid in fmap)}
        for c in bcols:row['baseline: '+c]=bmap.get(sid,{}).get(c,'')
        for c in fcols:row['final: '+c]=fmap.get(sid,{}).get(c,'')
        rows.append(row)
    cols=list(rows[0]) if rows else []
    write(out/'chat_level.csv',finished,chat_cols)
    write(out/'person_level.csv',rows,cols)
    ids=set(enrolled)|{sid for sid,rs in people.items() if rs}
    for label,m in (('baseline',bmap),('final',fmap)):
        if m:
            extra=sorted(set(m)-ids);missing=sorted(ids-set(m))
            if extra:print(f'CHECK: {label} form has IDs with no enrollment/chat record (check ID): {", ".join(extra)}')
            if missing:print(f'CHECK: no {label} form for: {", ".join(missing)}')
    print('\nDescriptive averages only (participants who finished the final chat; not hypothesis tests):')
    groups=defaultdict(list)
    for r in rows:
        if r['final_chat_done']:groups[(r['style'],r['memory'])].append(r)
    print(f"{'condition':22s} {'n':>3s} {'distress change':>16s} {'home chats':>11s} {'scenario':>9s}")
    for (s,m),g in sorted(groups.items()):
        print(f"{s+' + '+m:22s} {len(g):3d} {mean([num(r['avg_distress_change']) for r in g]):>16} {mean([num(r['home_chats']) for r in g]):>11} {mean([num(r['scenario_score']) for r in g]):>9}")

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    sub=p.add_subparsers(dest='cmd',required=True)
    b=sub.add_parser('blind');b.add_argument('--final',required=True);b.add_argument('--out',default='private/analysis')
    b.add_argument('--id-column');b.add_argument('--answer-column');b.add_argument('--scenario-column')
    c=sub.add_parser('combine');c.add_argument('--chats',required=True);c.add_argument('--baseline');c.add_argument('--final')
    c.add_argument('--participants',help='All-records JSON export or enrolled-participant CSV; retains people with zero chats');c.add_argument('--scores');c.add_argument('--key',default='private/analysis/coders_key.csv');c.add_argument('--out',default='private/analysis');c.add_argument('--id-column')
    a=p.parse_args()
    blind(a) if a.cmd=='blind' else combine(a)

if __name__=='__main__':main()
