"""Check freshness and existence/integrity of the last verified backup."""
import hashlib
import json
import os
import time
from pathlib import Path


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def backup_healthy(directory: Path, interval: int = 86400) -> bool:
    try:
        status = json.loads((directory / "status.json").read_text())
        if not isinstance(status, dict) or status.get("ok") is not True:
            return False
        name = status["backup"]
        if not isinstance(name, str) or Path(name).name != name:
            return False
        backup = directory / name
        return (0 <= time.time() - status["verified_at"] < max(300, interval) + 900
                and backup.is_file() and not backup.is_symlink()
                and backup.stat().st_size > 0 and file_digest(backup) == status["sha256"])
    except (OSError, ValueError, KeyError, TypeError):
        return False


if __name__ == "__main__":
    try:
        healthy = backup_healthy(Path(os.getenv("BACKUP_DIRECTORY", "/data/backups")), int(os.getenv("BACKUP_INTERVAL_SECONDS", "86400")))
    except ValueError:
        healthy = False
    raise SystemExit(0 if healthy else 1)
