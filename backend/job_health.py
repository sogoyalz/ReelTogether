import json
import os
import time
from pathlib import Path


def worker_healthy(path):
    try:
        status=json.loads(Path(path).read_text())
        return isinstance(status,dict) and 0 <= time.time()-status["heartbeat"] < 90
    except (OSError,ValueError,KeyError,TypeError):
        return False


if __name__=="__main__":
    raise SystemExit(0 if worker_healthy(os.getenv("JOB_HEARTBEAT_FILE","/data/operations/worker.json")) else 1)
