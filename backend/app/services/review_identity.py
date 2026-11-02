"""Stable review keys across SQLite naive and PostgreSQL aware timestamps."""
from datetime import timezone


def review_key(author, created_at, source, external_id=None):
    if external_id:
        return source, "id", external_id
    timestamp = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at.astimezone(timezone.utc)
    return author.strip().casefold(), timestamp.isoformat(), source
