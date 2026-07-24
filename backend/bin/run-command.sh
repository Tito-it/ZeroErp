#!/usr/bin/env bash
# Wrapper generico per eseguire un management command Django come processo
# headless (systemd oneshot / timer). Speculare a start-gunicorn.sh: carica
# l'env non-segreto da env.sh (export shell); i segreti (DB_PASSWORD,
# DB_SYSTEM_FATTURAZIONE_*, DJANGO_SECRET_KEY) li inietta systemd via
# EnvironmentFile=.env.systemd nell'unit. Riusabile da qualsiasi worker/cron
# (draina_coda_lavori, draina_coda_stampa, run_fatturazione_batch, ...).
#
# Uso:   bin/run-command.sh <command> [args...]
# Es.:   bin/run-command.sh draina_coda_lavori --limit 200
set -e
cd "$(dirname "$0")/.."
set -a
# shellcheck source=/dev/null  # env.sh è un file runtime per-host, non in repo
source ./env.sh
set +a
exec .venv/bin/python manage.py "$@"
