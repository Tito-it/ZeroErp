#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
set -a
source ./env.sh
set +a
exec .venv/bin/gunicorn zeroerp_backend.wsgi:application --bind 127.0.0.1:8000 --workers 3
