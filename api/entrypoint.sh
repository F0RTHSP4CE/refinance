#!/usr/bin/env sh
set -e

cd /opt/api

echo "[entrypoint] alembic upgrade head"
alembic upgrade head

echo "[entrypoint] seeding bootstrap data"
python -m app.scripts.seed

echo "[entrypoint] starting uvicorn"
exec uvicorn app.app:app --host 0.0.0.0 --port 8000 --log-config=uvicorn-log.yml "$@"
