"""Dry-run by default. Purge only expired temporary records, in bounded batches.

Account data and backups are not removed by this command. --apply requires the
operator to approve the printed policy. Keep the independent erasure ledger.
"""
import argparse,json
from datetime import timedelta
from sqlalchemy import delete,select,func
from app.db.session import SessionLocal
from app.models.account import LoginSession
from app.models.movie_night import MovieNight
from app.models.jobs import BackgroundJob
from app.services.authentication import now


def purge(db,*,apply=False,batch=500):
    policies=[(LoginSession,LoginSession.token_hash,LoginSession.expires_at < now()),
        (MovieNight,MovieNight.id,MovieNight.expires_at < now()-timedelta(days=30)),
        (BackgroundJob,BackgroundJob.id,(BackgroundJob.active_name.is_(None)) & (BackgroundJob.finished_at < now()-timedelta(days=30)))]
    report={}
    for model,key,condition in policies:
        ids=list(db.scalars(select(key).where(condition).limit(batch)))
        report[model.__tablename__]={'eligible_total':db.scalar(select(func.count()).select_from(model).where(condition)), 'batch_size':len(ids)}
        if apply and ids:db.execute(delete(model).where(key.in_(ids)))
    if apply:db.commit()
    return {'applied':apply,'records':report,'policy':'Expired sessions; rooms expired over 30 days; inactive job history over 30 days. Repeat to drain further batches.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    with SessionLocal() as db:print(json.dumps(purge(db,apply=args.apply),indent=2))
