"""Upgrade SQLite safely, backing up existing data before applying schema changes.

Use --adopt-existing once for a legacy create_all database without Alembic history.
"""
import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.db.base import Base
from app import models  # noqa: F401


def upgrade(adopt_existing=False):
    url = make_url(settings.DATABASE_URL)
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    unmanaged = "movies" in tables and "alembic_version" not in tables
    if unmanaged:
        if not adopt_existing:
            raise SystemExit("Legacy database detected. Run python upgrade_database.py --adopt-existing once; a backup is created first.")
        expected = set(Base.metadata.tables) - {"accounts", "login_sessions", "watchlist_entries", "movie_feedback", "movie_nights", "night_members", "night_votes"}
        if tables != expected:
            raise SystemExit("Legacy schema has unexpected tables; refusing automatic adoption.")
        for name, table in Base.metadata.tables.items():
            if name not in expected:
                continue
            expected_columns = set(table.columns.keys())
            if name == "movies":
                expected_columns -= {"enrichment_data", "provider_metadata"}
            actual = {column["name"] for column in inspector.get_columns(name)}
            if actual != expected_columns:
                raise SystemExit(f"Unexpected columns in {name}; refusing automatic adoption.")
    config = Config(str(Path(__file__).with_name("alembic.ini")))
    config.set_main_option("script_location", str(Path(__file__).with_name("alembic")))
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    if not unmanaged and current == ScriptDirectory.from_config(config).get_current_head():
        engine.dispose()
        print("Database is already at the current migration")
        return
    engine.dispose()
    if url.get_backend_name() == "sqlite" and url.database and Path(url.database).is_file():
        path = Path(url.database).resolve()
        backup = path.with_name(path.name + ".backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"))
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)
        backup.chmod(0o600)
        print(f"Backup: {backup}")
    config = Config(str(Path(__file__).with_name("alembic.ini")))
    config.set_main_option("script_location", str(Path(__file__).with_name("alembic")))
    if unmanaged:
        command.stamp(config, "20260324_0002")
    command.upgrade(config, "head")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adopt-existing", action="store_true")
    upgrade(parser.parse_args().adopt_existing)
