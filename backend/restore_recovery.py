"""Restore to a NEW SQLite file, migrate it, and replay an independent erasure ledger.

This never replaces the active database or starts a service. Supply a current,
independently retained ledger and its signing key via ERASURE_LEDGER_KEY.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.engine import URL
from app.core.config import settings
from database_backup import copy_database,inspect_database
from app.services.erasure_ledger import replay


def restore_copy(source,destination,ledger,key):
    destination=Path(destination).resolve()
    before=copy_database(Path(source),destination)
    url=URL.create('sqlite',database=str(destination)).render_as_string(hide_password=False)
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=Path(__file__).parent,
        env={**os.environ,'DATABASE_URL':url},check=True)
    engine=create_engine(url)
    from sqlalchemy import event
    @event.listens_for(engine,'connect')
    def foreign_keys(connection,_):connection.execute('PRAGMA foreign_keys=ON')
    try:
        with Session(engine) as db:removed=replay(db,ledger,key)
    finally:engine.dispose()
    return {'copied_integrity':before['integrity'],'erased_accounts_removed':removed,
            'restored_integrity':inspect_database(destination)['integrity'],
            'activated':False,'note':'Run readiness and synthetic account/room checks before changing the configured database.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    parser.add_argument('--ledger',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(restore_copy(args.source,args.destination,args.ledger,settings.ERASURE_LEDGER_KEY),indent=2))
