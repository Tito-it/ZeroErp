#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Django test wrapper with env loading.
#
# Usage:
# - ./manage-test.sh
#     -> runs full Django test suite
# - ./manage-test.sh apps.vendite.tests
#     -> runs a specific test module/class/test
# - ./manage-test.sh apps.vendite.tests -v 2
#     -> forwards extra manage.py test options
#
#-v 2 è il livello di verbosity (dettaglio output) del test runner Django.
#-v 0: quasi silenzioso
#-v 1: default
#-v 2: più dettagli (nome di ogni test eseguito + stato)   Standard choice
#-v 3: ancora più verboso (debug extra)
# ------------------------------------------------------------------------------

# Always run from backend dir (script directory)
cd "$(dirname "$0")"

# Load env vars (same policy as manage-env.sh)
ENV_FILE="./.env.systemd"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Create it from .env or point to the correct file." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Build test command
if [[ $# -eq 0 ]]; then
  set -- test
else
  TARGET="$1"
  shift
  set -- test "$TARGET" "$@"
fi

# Use venv python if present
if [[ -x "./.venv/bin/python" ]]; then
  exec "./.venv/bin/python" manage.py "$@"
fi

exec python manage.py "$@"
