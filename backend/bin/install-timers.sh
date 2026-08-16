#!/usr/bin/env bash
# Installa gli unit systemd dei worker headless:
#   - zeroerp-coda-lavori             (drainer dbops.coda_lavori)          → ABILITATO
#   - zeroerp-coda-stampa             (drainer vendite.fatture_stampa_coda) → ABILITATO
#   - zeroerp-fatturazione-immediata  (batch, corsia GIORNALIERO)          → scritto, SPENTO
#   - zeroerp-fatturazione-differita  (batch, corsia MASSIVO)              → scritto, SPENTO
#
# ⚠️ PERCHE' LE DUE CORSIE SI SCRIVONO MA NON SI ACCENDONO (decisione di Tid,
# 2026-08-16). Non e' una dimenticanza ne' un gate in attesa di un prerequisito:
# e' una differenza di NATURA. I drainer processano una coda — a coda vuota non
# fanno niente, e accenderli su un host nuovo e' senza conseguenze. Il batch
# invece EMETTE DOCUMENTI: accenderlo di riflesso, come effetto collaterale di
# un `sudo install-timers.sh`, vorrebbe dire iniziare a fatturare su un host che
# nessuno ha dichiarato pronto. Lo script li scrive e stampa il comando per
# accenderli, cosi' la decisione resta di chi installa.
#
# Fino al 2026-08-04 la coda stampa veniva scritta ma NON abilitata, in attesa
# dei GRANT del ruolo batch. Quei GRANT sono applicati (brief archiviato in
# docs/it/dev/work-done/brief-db-grant-batch-coda-stampa.md) e il timer gira in
# esercizio: lasciare il gate avrebbe consegnato a ogni host nuovo una coda
# stampa spenta, con un rimando a un vincolo che non esiste piu'.
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
# Coda stampa: ogni 2 min (tunable, P-5).
render_unit "zeroerp-coda-stampa" "*:0/2"
# Batch fatturazione, corsia immediata: ogni 2 min (near-real-time; il giro
# frequente fa anche da catch-up dei run falliti).
render_unit "zeroerp-fatturazione-immediata" "*:0/2"
# Batch fatturazione, corsia differita: il 1° del mese alle 02:00.
render_unit "zeroerp-fatturazione-differita" "*-*-01 02:00"

# In render-only (CI) ci si ferma qui: niente daemon-reload né enable.
if [ "$RENDER_ONLY" -eq 1 ]; then
  echo "OK render-only: unit in $DEST_DIR"
  exit 0
fi

systemctl daemon-reload

# Entrambi i timer: i GRANT del ruolo batch sulla coda stampa sono applicati
# (vedi testata). Un host nuovo deve partire con lo stesso assetto di quello in
# esercizio, non con meta' worker da accendere a mano.
systemctl enable --now zeroerp-coda-lavori.timer
systemctl enable --now zeroerp-coda-stampa.timer
echo
echo "OK: zeroerp-coda-lavori.timer e zeroerp-coda-stampa.timer abilitati."
echo
# Le corsie del batch sono state SCRITTE ma non abilitate (vedi testata): qui si
# dice come accenderle, invece di lasciarle scoperte in un file che nessuno apre.
echo "Batch fatturazione: unit installate ma NON attive (emettono documenti)."
echo "Per accenderle, quando l'host e' dichiarato pronto:"
echo "  systemctl enable --now zeroerp-fatturazione-immediata.timer   # ogni 2 min"
echo "  systemctl enable --now zeroerp-fatturazione-differita.timer   # 1o del mese 02:00"
echo "Prerequisito: DB_SYSTEM_FATTURAZIONE_* in ${ENV_FILE} (senza, il run"
echo "fallisce rumorosamente: nessun ripiego su zeroerp_app)."
echo
systemctl list-timers 'zeroerp-*' --all --no-pager || true
