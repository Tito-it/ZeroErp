#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
set -a
# shellcheck source=/dev/null  # env.sh è un file runtime per-host, non in repo
source ./env.sh
set +a

# Modalita` default (compatibile con nginx reverse proxy):
# - bind loopback: 127.0.0.1:8000
# - workers: 3
# Per sviluppo con reload automatico:
#   ZEROERP_GUNICORN_RELOAD=1
# Esempio override systemd:
#   Environment=ZEROERP_GUNICORN_RELOAD=1
#   Environment=ZEROERP_GUNICORN_BIND=127.0.0.1:8000
# Accesso esterno via nginx: https://192.168.X.8/

BIND="${ZEROERP_GUNICORN_BIND:-127.0.0.1:8000}"
WORKERS="${ZEROERP_GUNICORN_WORKERS:-3}"
TIMEOUT="${ZEROERP_GUNICORN_TIMEOUT:-60}"
RELOAD_FLAG=""
if [ "${ZEROERP_GUNICORN_RELOAD:-0}" = "1" ]; then
  RELOAD_FLAG="--reload"
fi

exec .venv/bin/gunicorn zeroerp_backend.wsgi:application \
  --bind "${BIND}" \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  ${RELOAD_FLAG}
