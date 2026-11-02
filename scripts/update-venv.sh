# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU AGPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------       


#!/usr/bin/env bash

# come Eseguire 
#./update-venv.sh

# Aggiorna tutti i pacchetti nella venv, esegue 'pip check' e,
# se non ci sono conflitti, scrive requirements.txt

# Aggiorna tutti i pacchetti nella venv, esegue 'pip check' e,
# se non ci sono conflitti, scrive requirements.txt

# In alternativa usare questi comandi manualmente:

# python -m pip install --upgrade pip
# python -m pip list --outdated --format=json
# python -m pip install --upgrade <package_name>   # ⚠️ vede solo <package_name>: per
#   rispettare i vincoli dei vicini nominare TUTTO (vedi ancoraggio 2026-09-18)
# python -m pip check
# pip list --outdated --format=columns | ForEach-Object { if ($_ -match '^\S+') { pip install --upgrade $matches[0] } } -- aggiorna tutto
# python -m pip freeze > requirements.txt




set -euo pipefail

# ⛔ ANCORAGGIO (2026-08-26). Sotto c'e' un `pip freeze > requirements.txt` senza
#    percorso: prima di questa riga scriveva nella CARTELLA CORRENTE, quindi
#    lanciato da `backend/` sostituiva `backend/requirements.txt` — che e'
#    generato da `pip-compile` — con un freeze piatto, cancellando il lock.
#    ⚠️ Ed e' un errore facile: i due script si chiamano UGUALE
#    (`scripts/update-venv.sh` qui, `backend/scripts/update-venv.sh` la'), e il
#    fratello del backend e' gia' ancorato cosi'.
cd "$(dirname "$0")/.."

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "⚠️  Non sembra attiva una virtualenv (VIRTUAL_ENV non impostata)."
  read -r -p "Vuoi continuare lo stesso? [y/N] " RESP
  [[ "${RESP}" == "y" ]] || exit 1
fi

# ⛔ E non dev'essere la venv del BACKEND: qui si fa `pip freeze` di tutto
#    l'ambiente sul requirements.txt di radice, quindi con quella attiva la lista
#    degli strumenti di sviluppo diventerebbe l'elenco dei pacchetti Django.
#    ⚠️ Si vieta quella sbagliata invece di pretendere quella giusta: dove viva
#    l'ambiente degli strumenti e' una scelta della macchina (qui
#    ~/.venvs/zeroerp-tools), e cablarla renderebbe lo script inservibile
#    altrove. La venv del backend, invece, sta nel repo e la sappiamo.
VENV_BACKEND="$(pwd)/backend/.venv"
if [[ -n "${VIRTUAL_ENV:-}" \
      && "$(readlink -f "${VIRTUAL_ENV}")" == "$(readlink -f "${VENV_BACKEND}")" ]]; then
  echo "Venv sbagliata: questa e' quella del BACKEND, governata da pip-compile."
  echo "  attiva: ${VIRTUAL_ENV}"
  echo "Per il backend si usa backend/scripts/update-venv.sh."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python}"

# 1) Aggiorna pip
${PYTHON_BIN} -m pip install --upgrade pip

# 2) Elenco pacchetti scaduti — SOLO resoconto: l'aggiornamento e' al punto 2b
echo "🔎 Cerco pacchetti da aggiornare..."
export OUTDATED_JSON="$(${PYTHON_BIN} -m pip list --outdated --format=json || true)"

TO_UPDATE="$(${PYTHON_BIN} - <<'PY'
import sys, json, os
data = os.environ.get("OUTDATED_JSON","").strip()
if not data:
    sys.exit(0)
try:
    pkgs = json.loads(data)
    for p in pkgs:
        name = p.get("name")
        if name:
            print(f"{name}  {p.get('version','?')} -> {p.get('latest_version','?')}")
except Exception:
    sys.exit(0)
PY
)"

if [[ -z "${TO_UPDATE}" ]]; then
  echo "ℹ️  Nessuna versione nuova sull'indice (riconcilio comunque, vedi sotto)."
else
  echo "⟹ Scaduti:"
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    echo "   - $line"
  done <<< "${TO_UPDATE}"
fi

# 2b) UNA risoluzione su tutto l'ambiente, sempre.
# ⛔ ANCORAGGIO (2026-09-18). Prima qui c'era un ciclo `pip install --upgrade
#    <nome>` per ogni pacchetto scaduto. Ma il resolver di pip risolve SOLO cio'
#    che gli si nomina piu' le sue dipendenze: i vincoli dei vicini gia'
#    installati non li vede (avvisa e prosegue). Cosi' `filelock` e' salito a
#    4.0.0 mentre `virtualenv` (ultima, 21.7.14) pretende `filelock<4`, e il
#    `pip check` sotto ha bloccato il freeze. E lo script non si riparava da
#    solo: 4.0.0 e' l'ultima, quindi `filelock` NON risultava scaduto e il ciclo
#    non lo toccava piu'.
#    Il rimedio NON e' un pin `filelock<4`: sarebbe la fotografia di oggi, da
#    ricordarsi di togliere quando virtualenv allarghera' il vincolo. Si nomina
#    invece TUTTO l'ambiente in una sola chiamata: il resolver vede ogni vincolo,
#    sceglie la versione piu' alta compatibile (anche a costo di SCENDERE, qui
#    3.32.7) e quando il vincolo cadra' salira' da solo. Gira anche senza
#    scaduti proprio per riconciliare uno stato incoerente come quello.
#    Restano fuori solo le righe di freeze che non sono `nome==versione`
#    (editable, VCS): non e' il caso di questa venv.
mapfile -t INSTALLED < <(${PYTHON_BIN} -m pip freeze | grep -E '^[A-Za-z0-9_.-]+==' | cut -d= -f1 || true)
if [[ ${#INSTALLED[@]} -eq 0 ]]; then
  echo "⚠️  pip freeze non ha restituito pacchetti: niente da riconciliare."
else
  echo "⟹ Aggiorno: una sola risoluzione su ${#INSTALLED[@]} pacchetti..."
  ${PYTHON_BIN} -m pip install --upgrade "${INSTALLED[@]}"
fi

# 3) Verifica dipendenze
echo
echo "▶️  Eseguo 'pip check'..."
set +e
CHECK_OUT="$(${PYTHON_BIN} -m pip check 2>&1)"
STATUS=$?
set -e
echo "${CHECK_OUT}"

# 4) Freeze solo se OK
if [[ ${STATUS} -eq 0 ]]; then
  echo
  echo "✅ Dipendenze OK. Scrivo requirements.txt..."
  ${PYTHON_BIN} -m pip freeze > requirements.txt
  echo "📝 Fatto: requirements.txt aggiornato."
  exit 0
else
  echo "❌ Conflitti rilevati. requirements.txt NON aggiornato. Risolvi e riprova."
  exit ${STATUS}
fi
