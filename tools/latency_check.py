"""Measure where chat time goes: database round trips and the OpenAI reply. Prints timings only, no secrets.

  python3 tools/latency_check.py            # database only (no cost)
  python3 tools/latency_check.py --openai  # also 3 real replies with the study prompt (tiny cost)
Run with the app stopped is not required: this does not take the app's database lock.
"""
import argparse,json,statistics,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import configuration
p=argparse.ArgumentParser();p.add_argument('--openai',action='store_true');a=p.parse_args()
cfg=configuration()
if cfg.get('database_backend')=='supabase':
    import psycopg
    from app.postgres import connection_options
    t0=time.perf_counter();conn=psycopg.connect(cfg['database_url'],**connection_options(cfg));connect_ms=(time.perf_counter()-t0)*1000
    times=[]
    for _ in range(15):
        t=time.perf_counter();conn.execute('SELECT 1').fetchone();times.append((time.perf_counter()-t)*1000)
    conn.close()
    rtt=statistics.median(times)
    print(f'Supabase: connect {connect_ms:.0f} ms, one round trip (median of 15) {rtt:.0f} ms')
    print(f'  A chat message currently needs about 60 database round trips -> about {60*rtt/1000:.1f} s of waiting per message, before the AI even answers.')
else:print('Database: local SQLite (round trips are under 1 ms).')
if a.openai:
    if cfg['mode']!='live':raise SystemExit('Set CHATBOT_MODE=live to time real OpenAI replies.')
    from app.provider import Provider
    from app.chatbot import PROMPTS
    prov=Provider(cfg);times=[]
    for i in range(3):
        t=time.perf_counter();r=prov.reply(PROMPTS,'guide',[],[{'role':'user','text':'I studied all week but did badly on my exam.'}]);times.append(time.perf_counter()-t)
        print(f'OpenAI reply {i+1}: {times[-1]:.1f} s, {len(r["text"].split())} words, input tokens {r.get("usage",{}).get("input_tokens","?")}, cached {((r.get("usage",{}).get("input_tokens_details") or {}).get("cached_tokens","?"))}')
    print(f'OpenAI median: {statistics.median(times):.1f} s for a whole reply (no streaming).')
