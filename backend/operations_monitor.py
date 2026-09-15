"""Poll local health and deliver deduplicated failure/recovery webhooks when configured."""
import json
import os
import signal
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen, HTTPRedirectHandler
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.jobs import BackgroundJob
from backup_health import backup_healthy
from job_health import worker_healthy


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def deliver(component, healthy):
    url=os.getenv("ALERT_WEBHOOK_URL","").strip()
    if not url:return False
    parsed=urlparse(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Alert endpoint must be an HTTPS URL without embedded credentials")
    payload={"service":"ReelTogether","component":component,"status":"recovered" if healthy else "failed",
             "text":f"ReelTogether {component}: {'recovered' if healthy else 'failed'}. Check your deployment."}
    headers={"Content-Type":"application/json"}
    token=os.getenv("ALERT_WEBHOOK_TOKEN","")
    if token:headers['Authorization']='Bearer '+token
    from urllib.request import build_opener
    with build_opener(NoRedirect()).open(Request(url,data=json.dumps(payload).encode(),headers=headers,method='POST'),timeout=5) as response:
        return 200 <= response.status < 300


def notify_changes(checks, state, sender=deliver):
    updated=dict(state)
    for component,healthy in checks.items():
        previous=state.get(component)
        # Start quiet when healthy. Failures are retried until delivery succeeds.
        if previous is None and healthy:
            updated[component]=True
        elif previous != healthy:
            try:
                if sender(component,healthy):updated[component]=healthy
            except Exception:
                pass
    return updated


def offsite_healthy(directory, interval):
    try:
        status=json.loads((directory/'offsite-status.json').read_text())
        return (isinstance(status,dict) and status.get('ok') is True
                and status.get('bucket')==os.getenv('BACKUP_S3_BUCKET')
                and 0 <= time.time()-status['verified_at'] < interval+900)
    except (OSError,ValueError,KeyError,TypeError):return False


def collect_checks():
    try:
        with urlopen(os.getenv('MONITOR_BACKEND_URL','http://backend:8000/health/ready'),timeout=5) as response:
            backend=response.status==200 and json.load(response).get('ready') is True
    except Exception:backend=False
    directory=Path(os.getenv('BACKUP_DIRECTORY','/data/backups'))
    interval=max(300,int(os.getenv('BACKUP_INTERVAL_SECONDS','86400')))
    checks={'backend':backend,'backups':backup_healthy(directory,interval),
            'worker':worker_healthy(os.getenv('JOB_HEARTBEAT_FILE','/data/operations/worker.json'))}
    if os.getenv('BACKUP_S3_BUCKET'):checks['offsite_backups']=offsite_healthy(directory,interval)
    try:
        with SessionLocal() as db:
            latest = {}
            for job in db.scalars(select(BackgroundJob).order_by(BackgroundJob.queued_at.desc())):
                latest.setdefault(job.name, job.status)
            checks['maintenance_jobs'] = all(status != 'failed' for status in latest.values())
    except Exception:checks['maintenance_jobs']=False
    return checks


def main():
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stop.set())
    root=Path(os.getenv('OPERATIONS_DIRECTORY','/data/operations'));root.mkdir(parents=True,exist_ok=True)
    path=root/'alerts.json'
    try:
        state=json.loads(path.read_text())
        if not isinstance(state,dict):state={}
    except (OSError,ValueError):state={}
    while not stop.is_set():
        checks=collect_checks()
        state=notify_changes(checks,state)
        pending=root/'alerts.tmp';pending.write_text(json.dumps(state));pending.chmod(0o600);pending.replace(path)
        report={'checked_at':time.time(),'checks':checks,'webhook_configured':bool(os.getenv('ALERT_WEBHOOK_URL'))}
        pending=root/'health.tmp';pending.write_text(json.dumps(report));pending.chmod(0o600);pending.replace(root/'health.json')
        stop.wait(60)


if __name__=='__main__':main()
