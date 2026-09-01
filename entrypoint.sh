#!/bin/sh
set -e
uv run manage.py migrate --noinput
exec uv run gunicorn danso.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 2
