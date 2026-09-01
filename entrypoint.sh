#!/bin/sh
set -e
uv run manage.py migrate --noinput

# Create superuser if DJANGO_SUPERUSER_USERNAME is set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  uv run manage.py createsuperuser --noinput || true
fi

exec uv run gunicorn danso.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 2
