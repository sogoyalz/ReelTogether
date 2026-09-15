#!/bin/sh
set -eu
python upgrade_database.py
exec uvicorn main:app --host 0.0.0.0 --port 8000 --no-proxy-headers --no-access-log
