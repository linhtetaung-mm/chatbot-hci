"""Disposable, loopback-only demo server for browser checks. Never reads .env."""
import json
import signal
import sys
import tempfile
from pathlib import Path
from wsgiref.simple_server import make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import server
from app.chatbot import Chatbot


def main():
    def terminate(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminate)
    with tempfile.TemporaryDirectory(prefix='hci-ui-') as folder:
        cfg = {
            'mode': 'demo', 'model': 'BROWSER_TEST_DEMO', 'reasoning': '',
            'db': str(Path(folder) / 'test.sqlite3'), 'storage_mode': 'persistent',
            'database_backend': 'sqlite', 'admin_key': 'BROWSER-TEST-ONLY-ADMIN-KEY-123456',
            'researcher_accounts': [{'name':'fixture_facilitator','role':'facilitator','key':'BROWSER-TEST-FACILITATOR-KEY-123456'}],
            'api_key': '', 'contact': 'team@example.invalid',
            'support': 'Use the contacts on your study information sheet',
            'delete_date': '2026-12-19', 'limits': {
                'TESTER_MINUTE_API_LIMIT': 1000, 'TESTER_DAILY_API_LIMIT': 1000,
                'TESTER_DAILY_CHAT_LIMIT': 1000, 'GLOBAL_DAILY_API_LIMIT': 10000,
                'GLOBAL_TOTAL_API_LIMIT': 10000,
            },
        }
        server.bot = Chatbot(cfg)
        server.bot.set_enrollment_plan({'groups':[{'style':s,'memory':m,'label':s.title()+' / '+m.title(),'target':12} for s in ('reassure','guide') for m in ('persistent','fresh')]})
        codes = [server.bot.create_tester(style, memory)['code']
                 for style in ('reassure', 'guide') for memory in ('persistent', 'fresh')]
        for style,memory,count in [('reassure','persistent',3),('reassure','fresh',2),('guide','persistent',4),('guide','fresh',1)]:
            for _ in range(count):server.bot.enroll_configured('manual',style+':'+memory,'Synthetic browser fixture; not study data')
        with make_server('127.0.0.1', 0, server.application,
                         server_class=server.Threaded, handler_class=server.Quiet) as httpd:
            origin = f'http://127.0.0.1:{httpd.server_port}'
            cfg.update(origin=origin, allowed_host=f'127.0.0.1:{httpd.server_port}')
            print(json.dumps({'origin': origin, 'admin': cfg['admin_key'], 'facilitator': cfg['researcher_accounts'][0]['key'], 'codes': codes}), flush=True)
            httpd.serve_forever()


if __name__ == '__main__':
    main()
