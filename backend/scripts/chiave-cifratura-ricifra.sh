#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Ri-cifra con la PRIMA chiave di DJANGO_FIELD_ENCRYPTION_KEYS tutti i
#        segreti salvati nel DB (`manage.py ricifra_campi_cifrati`), con le
#        chiavi scritte in backend/.env.systemd. Prima un dry-run, poi, dopo
#        conferma, la scrittura: tutto o niente.
#
# Uso: lo script lavora sempre sui file di backend/, da qualunque cartella lo
# si lanci; cambia solo il percorso da scrivere:
#   dalla radice del repo:  backend/scripts/chiave-cifratura-ricifra.sh
#   da backend/:            scripts/chiave-cifratura-ricifra.sh
# (sotto, gli esempi sono dalla radice del repo)
#
#   backend/scripts/chiave-cifratura-ricifra.sh
#       passo 2 di una ROTAZIONE, dopo chiave-cifratura-aggiungi.sh.
#   backend/scripts/chiave-cifratura-ricifra.sh --migrazione
#       UNA VOLTA per macchina: porta i segreti cifrati prima del 2026-09-28
#       (chiave derivata dalla SECRET_KEY) sulla chiave nuova.
#       ⛔ Va lanciato con la SECRET_KEY di allora ancora in uso: cambiarla
#          prima rende quei segreti illeggibili (vanno reinseriti a mano).
#
# Se un segreto non si apre con nessuna chiave il comando non scrive nulla e
# dice quale riga: quel segreto va reinserito (es. la password SMTP
# dall'account email), poi si rilancia.
#
# Procedura completa: docs/it/dev/sicurezza-e-qualita-statica.md,
# «Le chiavi dei dati cifrati».
# ------------------------------------------------------------
set -euo pipefail

# Il percorso assoluto dello script, preso PRIMA del `cd`: da li' in poi un
# "$0" relativo non indicherebbe piu' niente (serve a --help).
SELF="$(readlink -f "$0")"
cd "$(dirname "$SELF")/.."   # cartella backend

VAR="DJANGO_FIELD_ENCRYPTION_KEYS"
ENV_FILE=".env.systemd"
PY="./.venv/bin/python"

EXTRA=()
case "${1:-}" in
  "") ;;
  --migrazione) EXTRA=(--anche-chiave-da-secret-key) ;;
  -h|--help) sed -n '2,32p' "$SELF"; exit 0 ;;
  *) echo "Opzione sconosciuta: $1 (vedi --help)" >&2; exit 2 ;;
esac

[[ -f "$ENV_FILE" ]] || { echo "ERRORE: backend/$ENV_FILE non esiste." >&2; exit 1; }
[[ -x "$PY" ]] || { echo "ERRORE: manca la venv del backend ($PY)." >&2; exit 1; }

# Le stesse variabili del servizio: e' con queste chiavi che il backend leggera'.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
if [[ -z "${!VAR:-}" ]]; then
  echo "ERRORE: ${VAR} non e' in backend/$ENV_FILE." >&2
  echo "        Prima: backend/scripts/chiave-cifratura-aggiungi.sh" >&2
  exit 1
fi

echo "1) Verifica (dry-run): ogni segreto si apre? Nulla viene scritto."
"$PY" manage.py ricifra_campi_cifrati --dry-run "${EXTRA[@]}"

echo
read -r -p "2) Ri-cifro davvero con la prima chiave? [s/N] " risposta
if [[ "$risposta" != "s" && "$risposta" != "S" ]]; then
  echo "Niente di fatto."
  exit 0
fi
"$PY" manage.py ricifra_campi_cifrati "${EXTRA[@]}"

echo
echo "✅ Segreti ri-cifrati con la prima chiave."
echo "Prossimi passi:"
echo "  sudo systemctl restart zeroerp-gunicorn   (il servizio rilegge le chiavi)"
if [[ ${#EXTRA[@]} -eq 0 ]]; then
  echo "  backend/scripts/chiave-cifratura-aggiungi.sh --togli-vecchie   (chiude la rotazione)"
else
  echo "  da ora la SECRET_KEY si puo' cambiare senza perdere i segreti cifrati."
fi
