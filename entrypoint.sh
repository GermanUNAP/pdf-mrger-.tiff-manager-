#!/bin/sh
set -e

echo "==> Starting entrypoint..."
echo "==> PORT=${PORT:-unset}"
echo "==> PWD=$(pwd)"
echo "==> Python: $(python --version 2>&1 || echo 'NOT FOUND')"
echo "==> Gunicorn: $(python -m gunicorn --version 2>&1 || echo 'NOT FOUND')"

PORT="${PORT:-10000}"
echo "==> Binding to 0.0.0.0:$PORT"

exec python -m gunicorn \
    --bind "0.0.0.0:$PORT" \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    "app:create_app()"
