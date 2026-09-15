"""Periodic verified SQLite backups for a single persistent-volume deployment."""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from sqlalchemy.engine import make_url
from app.core.config import settings
from database_backup import copy_database
from backup_health import file_digest
from offsite_backup import publish_backup

logger = logging.getLogger("backups")


def backup_once(source: Path, directory: Path):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = "catalog-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".sqlite"
    backup = directory / name
    report = copy_database(source, backup)
    # Exercise restoration into a disposable file and compare its complete contents.
    with TemporaryDirectory(prefix="restore-check-", dir=directory) as temporary:
        restored = copy_database(backup, Path(temporary) / "restored.sqlite")
        if report != restored:
            raise ValueError("Restored backup differs from source backup")
    status = {"ok": True, "verified_at": time.time(), "backup": name, "sha256": file_digest(backup)}
    pending = directory / "status.tmp"
    pending.write_text(json.dumps(status))
    pending.chmod(0o600)
    pending.replace(directory / "status.json")
    # Retain only files created by this worker, after a verified replacement exists.
    for old in sorted(directory.glob("catalog-*.sqlite"))[:-14]:
        old.unlink()
    publish_backup(backup, directory)
    return status


def main():
    logging.basicConfig(level=logging.INFO)
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise SystemExit("Backups require file-backed SQLite")
    directory = Path(os.getenv("BACKUP_DIRECTORY", "/data/backups"))
    interval = max(300, int(os.getenv("BACKUP_INTERVAL_SECONDS", "86400")))
    while True:
        try:
            backup_once(Path(url.database), directory)
            logger.info("Backup and restore verification succeeded")
            time.sleep(interval)
        except Exception as error:
            logger.error("Backup failed: %s", type(error).__name__)
            time.sleep(300)


if __name__ == "__main__":
    main()
