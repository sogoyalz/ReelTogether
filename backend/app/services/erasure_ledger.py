"""Authenticated deletion receipts stored independently of database snapshots."""
import fcntl
import hashlib
import hmac
import json
import os
import uuid
from pathlib import Path
from sqlalchemy import select, delete
from app.core.config import settings
from app.models.account import Account, AccountErasure
from app.services.authentication import now


def signed_record(receipt, key):
    body = {'erasure_key': receipt.erasure_key, 'requested_at': receipt.requested_at.isoformat()}
    encoded = json.dumps(body, sort_keys=True, separators=(',',':')).encode()
    return {**body, 'signature':hmac.new(key.encode(),encoded,hashlib.sha256).hexdigest()}


def publish_pending(db):
    if not settings.ERASURE_LEDGER_PATH:
        if settings.is_production:
            raise RuntimeError('Erasure ledger is required')
        return 0
    if len(settings.ERASURE_LEDGER_KEY) < 32:
        raise RuntimeError('Erasure ledger signing key is required')
    rows = list(db.scalars(select(AccountErasure).where(AccountErasure.exported_at.is_(None)).limit(1000)))
    if not rows:
        return 0
    path = Path(settings.ERASURE_LEDGER_PATH)
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    # Append before acknowledgement. A crash before marking exported may append
    # duplicate receipts; replay is idempotent. Never overwrite the whole ledger.
    descriptor = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    with os.fdopen(descriptor,'a') as file:
        fcntl.flock(file,fcntl.LOCK_EX)
        for row in rows:file.write(json.dumps(signed_record(row,settings.ERASURE_LEDGER_KEY),sort_keys=True)+'\n')
        file.flush();os.fsync(file.fileno())
    for row in rows:row.exported_at=now()
    db.commit()
    return len(rows)


def receipt_keys(path, key):
    if len(key) < 32:
        raise ValueError('A valid erasure ledger key is required')
    keys=set()
    # Validate the complete ledger before touching any restored row.
    with Path(path).open() as file:
        fcntl.flock(file, fcntl.LOCK_SH)
        for line in file:
            record=json.loads(line)
            if set(record) != {'erasure_key','requested_at','signature'}:
                raise ValueError('Invalid erasure receipt')
            identity=str(uuid.UUID(record['erasure_key']))
            encoded=json.dumps({'erasure_key':identity,'requested_at':record['requested_at']},sort_keys=True,separators=(',',':')).encode()
            expected=hmac.new(key.encode(),encoded,hashlib.sha256).hexdigest()
            if not isinstance(record['signature'],str) or not record['signature'].isascii() or not hmac.compare_digest(expected,record['signature']):
                raise ValueError('Invalid erasure receipt signature')
            keys.add(identity)
    return keys


def replay(db, path, key):
    keys = receipt_keys(path, key)
    removed=0
    ordered=sorted(keys)
    for offset in range(0,len(ordered),500):
        removed += db.execute(delete(Account).where(Account.erasure_key.in_(ordered[offset:offset+500]))).rowcount
    db.commit()
    return removed
