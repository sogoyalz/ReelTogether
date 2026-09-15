"""Create and verify SQLite backups. Restore only to a new, unused file."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from sqlalchemy.engine import make_url
from app.core.config import settings


def inspect_database(path: Path):
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Database integrity or foreign-key check failed')
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts, hashes = {}, {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            rows = db.execute(f'SELECT * FROM {quoted}').fetchall()
            counts[table] = len(rows)
            encoded = sorted(json.dumps(row, default=str, separators=(',', ':')) for row in rows)
            hashes[table] = hashlib.sha256('\n'.join(encoded).encode()).hexdigest()
        return {'integrity': integrity, 'row_counts': counts, 'content_hashes': hashes}


def copy_database(source: Path, destination: Path):
    source, destination = source.resolve(), destination.resolve()
    if not source.is_file():
        raise ValueError('Source database does not exist')
    if destination.exists():
        raise ValueError('Destination already exists; refusing to replace a database')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive file creation prevents accidentally clobbering another database.
    with destination.open('xb'):
        pass
    destination.chmod(0o600)
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    return inspect_database(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    backup = sub.add_parser('backup')
    backup.add_argument('destination', type=Path)
    restore = sub.add_parser('restore-copy')
    restore.add_argument('source', type=Path)
    restore.add_argument('destination', type=Path)
    verify = sub.add_parser('verify')
    verify.add_argument('source', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'backup':
            url = make_url(settings.DATABASE_URL)
            if url.get_backend_name() != 'sqlite' or not url.database or url.database == ':memory:':
                raise ValueError('This command supports file-backed SQLite only')
            report = copy_database(Path(url.database), args.destination)
        elif args.command == 'restore-copy':
            report = copy_database(args.source, args.destination)
        else:
            report = inspect_database(args.source.resolve())
        print(json.dumps(report, indent=2))
    except (ValueError, sqlite3.DatabaseError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
