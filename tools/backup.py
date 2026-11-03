"""Create a consistent SQLite backup. Does not overwrite existing backups."""
import argparse,sqlite3
from contextlib import closing
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('destination');a=p.parse_args()
source=Path(a.source);dest=Path(a.destination)
if not source.is_file():raise SystemExit('Source database does not exist.')
if dest.exists():raise SystemExit('Destination exists; choose a new dated filename.')
dest.parent.mkdir(parents=True,exist_ok=True)
with closing(sqlite3.connect(source)) as src,closing(sqlite3.connect(dest)) as out:
    src.backup(out);out.commit()
dest.chmod(0o600);print('Private consistent backup created. Do not upload it to GitHub.')
