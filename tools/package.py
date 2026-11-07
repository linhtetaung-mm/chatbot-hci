"""Build a clean shareable ZIP; private runtime records are always excluded."""
from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
def public_files():
    allowed={'app','tests','tools','docs'}
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(ROOT)
        if any(x in ('__pycache__','.venv','.git') for x in rel.parts):continue
        if len(rel.parts)>1 and rel.parts[0] not in allowed:continue
        if p.suffix in ('.pyc','.log','.sqlite3','.zip','.db','.pem','.key') or '.sqlite3' in p.name or p.name=='.env' or p.name.startswith('.env.') and p.name!='.env.example':continue
        if len(rel.parts)==1 and p.name not in {'README.md','HOW_TO_USE.md','VERIFICATION.md','requirements.txt','run.py','setup_local.py','.env.example','.gitignore','MANIFEST.json'}:continue
        yield p
files=[p for p in public_files() if p.name!='MANIFEST.json']
manifest={'version':'phase1-1.4-progress-guide','files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(ROOT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
out=ROOT.parent/(ROOT.name+'.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for p in public_files():z.write(p,ROOT.name+'/'+str(p.relative_to(ROOT)))
print('Shareable package:',out)
print('Private .env, data, exports, backups and caches excluded.')
