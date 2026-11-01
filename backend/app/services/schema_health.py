"""Check every mapped column so readiness detects incomplete migrations."""
from sqlalchemy import select
from app import models  # noqa: F401
from app.db.base import Base


def assert_schema_ready(db):
    for table in Base.metadata.sorted_tables:
        db.execute(select(table).limit(0))
