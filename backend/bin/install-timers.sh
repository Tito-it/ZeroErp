#!/usr/bin/env bash
# Installa gli unit systemd dei worker DRAINER (Fase C cockpit fatturazione):
#   - zeroerp-coda-lavori  (coda generica dbops.coda_lavori)  → ABILITATO
#   - zeroerp-coda-stampa  (coda stampa vendite.fatture_stampa_coda) → SOLO scritto,
#     NON abilitato: richiede prima i GRANT del ruolo batch (vedi
#     docs/it/dev/work-in-progress/brief-db-grant-batch-coda-stampa.md).
#
# Idempotente: riscrive gli unit a ogni run. Da eseguire come root:
#   sudo backend/bin/install-timers.sh
#
# Modalità validazione (usata dalla CI, niente root/systemctl): renderizza i
# template in una cartella e basta, per darli in pasto a `systemd-analyze verify`:
#   backend/bin/install-timers.sh --render-only <DIR>
#
# Convenzione: mirror di play-book-operativo-backend.md §15/§16. Gli unit usano
# il wrapper bin/run-command.sh (env.sh) + EnvironmentFile=.env.systemd (segreti,
# incl. DB_SYSTEM_FATTURAZIONE_* per i job di sistema / la coda stampa).
#
# Fonte di verità UNICA degli unit: i template versionati in
# backend/deploy/systemd/*.service|*.timer (reviewabili in PR). Questo script NON
# li genera più con heredoc inline: li renderizza sostituendo i placeholder
# per-host (__APP_DIR__, __APP_USER__, __ONCALENDAR__). Modifiche agli unit → si
# editano i template, non questo script.
set -euo pipefail

# Modalità: install (default, scrive in /etc/systemd/system e abilita) oppure
# render-only (solo rendering in DIR, per la validazione CI).
RENDER_ONLY=0
DEST_DIR="/etc/systemd/system"
if [ "${1:-}" = "--render-only" ]; then
  RENDER_ONLY=1
  DEST_DIR="${2:?--render-only richiede una directory di output}"
  mkdir -p "$DEST_DIR"
fi

if [ "$RENDER_ONLY" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then
  echo "Esegui come root: sudo $0" >&2
  exit 1
fi

# APP_DIR = la cartella backend (questo script vive in backend/bin/).
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# APP_USER = proprietario della cartella app (portabile fra host).
APP_USER="$(stat -c '%U' "$APP_DIR")"
WRAPPER="${APP_DIR}/bin/run-command.sh"
ENV_FILE="${APP_DIR}/.env.systemd"
TEMPLATE_DIR="${APP_DIR}/deploy/systemd"

# Sanity: il wrapper (target degli ExecStart) e i template devono esistere.
[ -x "$WRAPPER" ] || { echo "Manca il wrapper eseguibile: $WRAPPER" >&2; exit 1; }
[ -d "$TEMPLATE_DIR" ] || { echo "Manca la cartella template: $TEMPLATE_DIR" >&2; exit 1; }
# L'env file è un segreto runtime per-host: richiesto solo per l'installazione
# reale, non per la validazione (la CI non ce l'ha e non ne ha bisogno).
if [ "$RENDER_ONLY" -eq 0 ]; then
  [ -f "$ENV_FILE" ] || { echo "Manca l'env file: $ENV_FILE" >&2; exit 1; }
fi

echo "APP_DIR=$APP_DIR  APP_USER=$APP_USER  DEST=$DEST_DIR  render_only=$RENDER_ONLY"

# Scopo: renderizza la coppia template service+timer (backend/deploy/systemd/)
# sostituendo i placeholder per-host, e la scrive in $DEST_DIR.
render_unit() {
  local name="$1" oncalendar="$2" kind tpl
  for kind in service timer; do
    tpl="${TEMPLATE_DIR}/${name}.${kind}"
    [ -f "$tpl" ] || { echo "Manca il template: $tpl" >&2; exit 1; }
    # '|' come delimitatore sed: APP_DIR è un path con '/'.
    sed -e "s|__APP_DIR__|${APP_DIR}|g" \
        -e "s|__APP_USER__|${APP_USER}|g" \
        -e "s|__ONCALENDAR__|${oncalendar}|g" \
        "$tpl" > "${DEST_DIR}/${name}.${kind}"
  done
  echo "  scritto ${name}.service + ${name}.timer (OnCalendar=${oncalendar})"
}

echo "Rendering unit dai template ($TEMPLATE_DIR)..."
# Coda generica: ogni minuto (tunable a *:*:0/30 = ogni 30 SECONDI per UI più
# reattiva; NB *:0/30 sarebbe ogni 30 minuti).
render_unit "zeroerp-coda-lavori" "*:0/1"
# Coda stampa: ogni 2 min (tunable, P-5). NON abilitato qui (gate GRANT DB).
render_unit "zeroerp-coda-stampa" "*:0/2"

# In render-only (CI) ci si ferma qui: niente daemon-reload né enable.
if [ "$RENDER_ONLY" -eq 1 ]; then
  echo "OK render-only: unit in $DEST_DIR"
  exit 0
fi

systemctl daemon-reload

# Abilita SOLO la coda generica (smoke reale ok). La coda stampa resta scritta ma
# disabilitata finché il team DB non applica i GRANT del ruolo batch.
systemctl enable --now zeroerp-coda-lavori.timer
echo
echo "OK: zeroerp-coda-lavori.timer abilitato."
echo "    zeroerp-coda-stampa.timer scritto ma NON abilitato (attende GRANT DB:"
echo "    docs/it/dev/work-in-progress/brief-db-grant-batch-coda-stampa.md)."
echo "    Dopo i GRANT:  sudo systemctl enable --now zeroerp-coda-stampa.timer"
echo
systemctl list-timers 'zeroerp-coda-*' --no-pager || true
