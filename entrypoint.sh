#!/bin/sh
set -e
PORT="${PORT:-5000}"
exec python -m gunicorn --bind "0.0.0.0:$PORT" --workers 4 --timeout 120 "app:create_app()"
