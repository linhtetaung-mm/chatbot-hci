"""Start the local prototype from any working directory."""
from app.server import main
if __name__=='__main__':
    try:main()
    except ValueError as exc:raise SystemExit(str(exc))
