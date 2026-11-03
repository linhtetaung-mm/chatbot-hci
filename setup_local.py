"""Create private local settings without overwriting existing settings."""
from pathlib import Path
import secrets
root=Path(__file__).resolve().parent;path=root/'.env'
if path.exists():raise SystemExit('.env already exists; it has not been changed. Edit it privately if needed.')
content=(root/'.env.example').read_text().replace('replace-with-generated-secret',secrets.token_urlsafe(32))
with path.open('x') as f:f.write(content)
path.chmod(0o600)
print('Created private .env. Open it locally to find ADMIN_KEY; do not share it. Run python3 run.py for the API setup placeholder.')
