"""Recoverable maintenance worker. Run separately from the API in Compose."""
import json
import logging
import os
import signal
import threading
import time
from pathlib import Path
from app.core.config import settings
from app.services.background_jobs import job_registry

logger=logging.getLogger("maintenance")


def handlers():
    from app.services.startup_jobs import _run_startup_sync, _run_tmdb_sync, _run_youtube_refresh, _run_ai_refresh
    return {"startup-sync":_run_startup_sync,"tmdb-sync":_run_tmdb_sync,"youtube-refresh":_run_youtube_refresh,"ai-refresh":_run_ai_refresh}


def write_heartbeat():
    target=os.getenv("JOB_HEARTBEAT_FILE")
    if target:
        path=Path(target);path.parent.mkdir(parents=True,exist_ok=True)
        pending=path.with_name(path.name+"."+str(os.getpid())+".tmp")
        pending.write_text(json.dumps({"heartbeat":time.time()}));pending.chmod(0o600);pending.replace(path)


def execute_job(registry, job, available_handlers=None):
    stop=threading.Event()
    def renew():
        while not stop.wait(20):
            try:
                if not registry.heartbeat(job.id,job.lease_token):return
                write_heartbeat()
            except Exception:
                logger.error("Worker heartbeat failed")
    keeper=threading.Thread(target=renew,daemon=True);keeper.start()
    started=time.monotonic()
    try:
        result=(available_handlers or handlers())[job.name]() or {}
        if not isinstance(result,dict):raise ValueError("Invalid job result")
        result["elapsed_ms"]=int((time.monotonic()-started)*1000)
        if len(json.dumps(result))>32768:result={"summary":"Completed; detailed result exceeds storage limit"}
        registry.finish(job.id,job.lease_token,result=result)
    except Exception as error:
        logger.error("Maintenance operation failed: %s",type(error).__name__)
        registry.finish(job.id,job.lease_token,error=type(error).__name__)
    finally:
        stop.set();keeper.join(timeout=2)


def run_worker(stop, registry=None):
    registry=registry or job_registry
    while not stop.is_set():
        try:
            write_heartbeat()
            if settings.ENABLE_PERIODIC_SYNC:
                if settings.tmdb_api_configured:registry.schedule_due("tmdb-sync")
                if settings.youtube_api_configured:registry.schedule_due("youtube-refresh")
            job=registry.claim()
            if job:
                execute_job(registry,job)
                continue
        except Exception as error:
            logger.error("Worker iteration failed: %s",type(error).__name__)
        stop.wait(2)


if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    stop=threading.Event()
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,lambda *_:stop.set())
    run_worker(stop)
