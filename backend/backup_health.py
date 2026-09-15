"""Exit nonzero when the last verified backup is overdue."""
import json
import os
import time
from pathlib import Path
try:
    status = json.loads((Path(os.getenv("BACKUP_DIRECTORY", "/data/backups")) / "status.json").read_text())
    interval = max(300, int(os.getenv("BACKUP_INTERVAL_SECONDS", "86400")))
    healthy = status.get("ok") is True and 0 <= time.time() - status["verified_at"] < interval + 900
except (OSError, ValueError, KeyError, TypeError):
    healthy = False
raise SystemExit(0 if healthy else 1)
