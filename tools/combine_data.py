"""Turn the downloads into analysis-ready tables (standard library only; output opens in Excel).

Step 1, blind the scenario answers for the two coders (after the last final session):
  python3 tools/combine_data.py blind --final final.csv
    -> private/analysis/coders_scenarios.csv  (give ONLY this to the coders: code, scenario, answer)
    -> private/analysis/coders_key.csv        (keep private: code -> study ID)
  The coders add three columns to their copy: coder1, coder2 (independent 0-3 scores) and final (agreed score).

Step 2, combine everything:
  python3 tools/combine_data.py combine --chats chats.csv --baseline baseline.csv --final final.csv \\
      [--scores coders_scored.csv]
    -> private/analysis/chat_level.csv    one row per finished chat (for H1)
    -> private/analysis/person_level.csv  one row per participant: chat averages + counts + both forms + scenario score (H2-H6)
  It also prints Cohen's kappa for the coders, a check of missing/duplicate study IDs, and averages per condition.

chats.csv = researcher page -> "One row per chat (CSV)". baseline.csv / final.csv = Google Sheets -> File -> Download -> CSV.
The study-ID column is found by a header containing "study id"; override with --id-column.
"""
import argparse,csv,os,random,re,statistics,sys
from collections import defaultdict
from pathlib import Path

def norm_id(v):
    v=re.sub(r'\s+','',str(v or '')).upper()
    m=re.fullmatch(r'([A-Z]+)0*(\d+)',v)
    return f'{m.group(1)}{int(m.group(2)):02d}' if m else v

def read(path):
    with open(path,newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def find_col(rows,needle,override=None,required=True,path=''):
    if override:return override
    cols=list(rows[0]) if rows else []
    hits=[c for c in cols if needle in c.lower()]
    if not hits and required:raise SystemExit(f'No column containing "{needle}" in {path}. Use the option to name it. Columns: {cols}')
    return hits[0] if hits else None

def write(path,rows,cols):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',newline='',encoding='utf-8') as f:
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
    try:return float(v)
    except (TypeError,ValueError):return None

def mean(vals):
    vals=[v for v in vals if v is not None]
    return round(statistics.mean(vals),2) if vals else ''

def kappa(a,b):
    n=len(a)
    if not n:return None
    po=sum(x==y for x,y in zip(a,b))/n;cats=set(a)|set(b)
    pe=sum((a.count(c)/n)*(b.count(c)/n) for c in cats)
    return 1.0 if pe==1 else (po-pe)/(1-pe)

def blind(args):
    rows=read(args.final);idc=find_col(rows,'study id',args.id_column,path=args.final)
    ans=find_col(rows,'imagine this happened',args.answer_column,path=args.final)
    letter=find_col(rows,'scenario',args.scenario_column,required=False)
    if letter==ans:letter=None
    items=[];rng=random.Random()
    codes=rng.sample(range(100,1000),len(rows))
    for r,code in zip(rows,codes):
        items.append({'code':f'S{code}','study_id':norm_id(r[idc]),'scenario':(r.get(letter) or '').strip()[:1].upper() if letter else '','answer':r[ans].strip()})
    rng.shuffle(items)
    out=Path(args.out)
    write(out/'coders_scenarios.csv',items,['code','scenario','answer'])
    write(out/'coders_key.csv',items,['code','study_id'])
    print('Give coders_scenarios.csv to the coders. Keep coders_key.csv private.')

def combine(args):
    chats=[r for r in read(args.chats) if r.get('test_account','0')=='0']
    finished=[r for r in chats if r['status']=='completed']
    out=Path(args.out)
    chat_cols=['study_id','style','memory','chat_type','started_utc','minutes','user_messages','notes_used','pre_distress','post_distress','distress_change','support_needed','felt_understood','safety_stop']
    for r in finished:r['study_id']=norm_id(r['study_id'])
    write(out/'chat_level.csv',finished,chat_cols)
    people=defaultdict(list)
    for r in chats:people[norm_id(r['study_id'])].append(r)
    base=read(args.baseline) if args.baseline else [];fin=read(args.final) if args.final else []
    bmap=by_id(base,find_col(base,'study id',args.id_column,path=args.baseline),'baseline') if base else {}
    fmap=by_id(fin,find_col(fin,'study id',args.id_column,path=args.final),'final') if fin else {}
    scores={}
    if args.scores:
        srows=read(args.scores);key={r['code']:norm_id(r['study_id']) for r in read(args.key)}
        pairs=[(int(float(r['coder1'])),int(float(r['coder2']))) for r in srows if num(r.get('coder1')) is not None and num(r.get('coder2')) is not None]
        if pairs:
            k=kappa([p[0] for p in pairs],[p[1] for p in pairs]);agree=sum(a==b for a,b in pairs)/len(pairs)
            print(f'Coders: {len(pairs)} answers scored twice, exact agreement {agree:.0%}, Cohen\'s kappa {k:.2f} (target 0.70 or more)')
        for r in srows:
            final=num(r.get('final'))
            if final is None and num(r.get('coder1'))==num(r.get('coder2')):final=num(r.get('coder1'))
            if r['code'] in key and final is not None:scores[key[r['code']]]=final
            elif r['code'] in key:print(f"WARNING: no agreed 'final' score for {r['code']}")
    bcols=[c for c in (base[0] if base else {}) ];fcols=[c for c in (fin[0] if fin else {})]
    rows=[]
    for sid,rs in sorted(people.items()):
        done=[r for r in rs if r['status']=='completed']
        count=lambda t:sum(r['chat_type']==t for r in done)
        row={'study_id':sid,'style':rs[0]['style'],'memory':rs[0]['memory'],'first_chat_done':count('first'),'home_chats':count('home'),'final_chat_done':count('final'),
             'chats_finished':len(done),'chats_stopped':sum(r['status']!='completed' for r in rs),'safety_stop':int(any(r['safety_stop']=='1' for r in rs)),
             'avg_pre_distress':mean([num(r['pre_distress']) for r in done]),'avg_post_distress':mean([num(r['post_distress']) for r in done]),
             'avg_distress_change':mean([num(r['distress_change']) for r in done]),'avg_support_needed':mean([num(r['support_needed']) for r in done]),
             'avg_felt_understood':mean([num(r['felt_understood']) for r in done]),'scenario_score':scores.get(sid,''),
             'has_baseline':int(sid in bmap),'has_final':int(sid in fmap)}
        for c in bcols:row['baseline: '+c]=bmap.get(sid,{}).get(c,'')
        for c in fcols:row['final: '+c]=fmap.get(sid,{}).get(c,'')
        rows.append(row)
    cols=list(rows[0]) if rows else []
    write(out/'person_level.csv',rows,cols)
    ids=set(people)
    for label,m in (('baseline',bmap),('final',fmap)):
        if m:
            extra=sorted(set(m)-ids);missing=sorted(ids-set(m))
            if extra:print(f'CHECK: {label} form has IDs with no chats (typo?): {", ".join(extra)}')
            if missing:print(f'CHECK: no {label} form for: {", ".join(missing)}')
    print('\nAverages per condition (participants who finished the final chat):')
    groups=defaultdict(list)
    for r in rows:
        if r['final_chat_done']:groups[(r['style'],r['memory'])].append(r)
    print(f"{'condition':22s} {'n':>3s} {'distress change':>16s} {'home chats':>11s} {'scenario':>9s}")
    for (s,m),g in sorted(groups.items()):
        print(f"{s+' + '+m:22s} {len(g):3d} {mean([num(r['avg_distress_change']) for r in g]):>16} {mean([num(r['home_chats']) for r in g]):>11} {mean([num(r['scenario_score']) for r in g]):>9}")

p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
sub=p.add_subparsers(dest='cmd',required=True)
b=sub.add_parser('blind');b.add_argument('--final',required=True);b.add_argument('--out',default='private/analysis')
b.add_argument('--id-column');b.add_argument('--answer-column');b.add_argument('--scenario-column')
c=sub.add_parser('combine');c.add_argument('--chats',required=True);c.add_argument('--baseline');c.add_argument('--final')
c.add_argument('--scores');c.add_argument('--key',default='private/analysis/coders_key.csv');c.add_argument('--out',default='private/analysis');c.add_argument('--id-column')
a=p.parse_args()
blind(a) if a.cmd=='blind' else combine(a)
