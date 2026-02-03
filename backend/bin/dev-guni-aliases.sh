#!/usr/bin/env bash

# Alias/funzioni shell per togglare rapidamente Gunicorn in modalita` sviluppo.
# Uso:
#   source /home/tid/apps/ZeroErp/backend/bin/dev-guni-aliases.sh
#   dev-guni-on
#   dev-guni-off

ZEROERP_GUNI_SERVICE="${ZEROERP_GUNI_SERVICE:-zeroerp-gunicorn.service}"
ZEROERP_GUNI_OVERRIDE_DIR="${ZEROERP_GUNI_OVERRIDE_DIR:-/etc/systemd/system/zeroerp-gunicorn.service.d}"
ZEROERP_GUNI_OVERRIDE_FILE="${ZEROERP_GUNI_OVERRIDE_FILE:-${ZEROERP_GUNI_OVERRIDE_DIR}/10-dev-reload.conf}"

dev-guni-on() {
  echo "[dev-guni-on] abilito autoreload per ${ZEROERP_GUNI_SERVICE}"
  sudo mkdir -p "${ZEROERP_GUNI_OVERRIDE_DIR}"
  sudo tee "${ZEROERP_GUNI_OVERRIDE_FILE}" >/dev/null <<'EOF'
[Service]
Environment=ZEROERP_GUNICORN_RELOAD=1
Environment=ZEROERP_GUNICORN_BIND=127.0.0.1:8000
Environment=ZEROERP_GUNICORN_WORKERS=1
EOF
  sudo systemctl daemon-reload
  sudo systemctl restart "${ZEROERP_GUNI_SERVICE}"
  sudo systemctl status "${ZEROERP_GUNI_SERVICE}" --no-pager
}

dev-guni-off() {
  echo "[dev-guni-off] disabilito autoreload per ${ZEROERP_GUNI_SERVICE}"
  sudo rm -f "${ZEROERP_GUNI_OVERRIDE_FILE}"
  sudo systemctl daemon-reload
  sudo systemctl restart "${ZEROERP_GUNI_SERVICE}"
  sudo systemctl status "${ZEROERP_GUNI_SERVICE}" --no-pager
}

dev-guni-status() {
  sudo systemctl status "${ZEROERP_GUNI_SERVICE}" --no-pager
}

dev-guni-logs() {
  sudo journalctl -u "${ZEROERP_GUNI_SERVICE}" -n "${1:-80}" --no-pager
}
