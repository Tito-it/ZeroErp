#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Django manage wrapper with env loading (systemd-style KEY=VALUE)
#
# Enabled options:
# - Loads environment variables from: ./.env.systemd
# - Uses venv interpreter if present: ./.venv/bin/python
#
# Convenience aliases:
# - ./manage-env.sh run
#     -> ./manage-env.sh runserver 127.0.0.1:8000
# - ./manage-env.sh run --open
#     -> ./manage-env.sh runserver 0.0.0.0:8000   (exposes dev server on all NICs)
#
# Notes:
# - Default behavior with no args is unchanged: shows Django help.
# - If you use --open, ensure your dev ALLOWED_HOSTS / firewall rules are appropriate.
# ------------------------------------------------------------------------------

# Always run from project backend dir (script directory)
cd "$(dirname "$0")"

# Load env vars for Django (systemd-compatible KEY=VALUE format)
ENV_FILE="./.env.systemd"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Create it from .env or point to the correct file." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Convenience alias: "run" -> runserver with safe default bind
if [[ "${1:-}" == "run" ]]; then
  shift
  if [[ "${1:-}" == "--open" ]]; then
    shift
    set -- runserver 0.0.0.0:8001 "$@"
  else
    set -- runserver 127.0.0.1:8001 "$@"
  fi
fi

# Use the venv python if present
if [[ -x "./.venv/bin/python" ]]; then
  exec "./.venv/bin/python" manage.py "$@"
fi

exec python manage.py "$@"
