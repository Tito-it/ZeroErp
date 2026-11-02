#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Gestisce DJANGO_FIELD_ENCRYPTION_KEYS (le chiavi Fernet dei segreti
#        cifrati nel DB) nei due file d'ambiente del backend, `env.sh` (shell)
#        e `.env.systemd` (servizio e timer), tenendoli IDENTICI.
#
# Uso: lo script lavora sempre sui file di backend/, da qualunque cartella lo
# si lanci; cambia solo il percorso da scrivere:
#   dalla radice del repo:  backend/scripts/chiave-cifratura-aggiungi.sh
#   da backend/:            scripts/chiave-cifratura-aggiungi.sh
# (sotto, gli esempi sono dalla radice del repo)
#
#   backend/scripts/chiave-cifratura-aggiungi.sh
#       genera una chiave nuova e la mette IN TESTA all'elenco. Se l'elenco
#       non c'e' ancora lo crea (prima installazione, o migrazione del
#       2026-09-28); se c'e', e' il passo 1 di una ROTAZIONE.
#   backend/scripts/chiave-cifratura-aggiungi.sh --togli-vecchie
#       passo 3 della rotazione: tiene solo la prima chiave. Prima verifica
#       (dry-run) che la prima chiave da sola apra TUTTI i segreti del DB.
#
# La procedura completa, e perche' esiste:
#   docs/it/dev/sicurezza-e-qualita-statica.md, «Le chiavi dei dati cifrati».
#   Rotazione: questo script → chiave-cifratura-ricifra.sh → questo script
#   con --togli-vecchie. Dopo ogni modifica: sudo systemctl restart zeroerp-gunicorn
#
# ⛔ Lo script non stampa MAI una chiave. Prima di scrivere salva una copia dei
#    due file in backend/var/backup-env/ (fuori da git, permessi 600): una
#    chiave persa rende illeggibili i segreti cifrati con lei.
# ------------------------------------------------------------
set -euo pipefail

# Il percorso assoluto dello script, preso PRIMA del `cd`: da li' in poi un
# "$0" relativo non indicherebbe piu' niente (serve a --help).
SELF="$(readlink -f "$0")"
cd "$(dirname "$SELF")/.."   # cartella backend

VAR="DJANGO_FIELD_ENCRYPTION_KEYS"
FILE_SHELL="env.sh"
FILE_SYSTEMD=".env.systemd"
PY="./.venv/bin/python"
BACKUP_DIR="var/backup-env"

MODO="aggiungi"
case "${1:-}" in
  "") ;;
  --togli-vecchie) MODO="togli-vecchie" ;;
  -h|--help) sed -n '2,34p' "$SELF"; exit 0 ;;
  *) echo "Opzione sconosciuta: $1 (vedi --help)" >&2; exit 2 ;;
esac

for f in "$FILE_SHELL" "$FILE_SYSTEMD"; do
  [[ -f "$f" ]] || { echo "ERRORE: backend/$f non esiste." >&2; exit 1; }
  permessi="$(stat -c '%a' "$f")"
  if [[ "$permessi" != "600" ]]; then
    echo "⚠️  backend/$f ha permessi $permessi: contiene segreti, dovrebbe essere 600 (chmod 600 $f)."
  fi
done
[[ -x "$PY" ]] || { echo "ERRORE: manca la venv del backend ($PY)." >&2; exit 1; }

# Scopo: il valore della variabile nel file (vuoto se assente). Piu' righe
#        per la stessa variabile sono un errore: quale vale dipende da chi legge.
leggi() {
  local file="$1" righe
  righe="$(grep -cE "^(export )?${VAR}=" "$file" || true)"
  if (( righe > 1 )); then
    echo "ERRORE: backend/$file ha $righe righe ${VAR}: lasciarne una sola." >&2
    exit 1
  fi
  sed -nE "s/^(export )?${VAR}=\"?([^\"]*)\"?[[:space:]]*$/\2/p" "$file"
}

# Scopo: scrive il valore nel file, sostituendo la riga o aggiungendola in coda.
scrivi() {
  local file="$1" valore="$2" prefisso="$3"
  if grep -qE "^(export )?${VAR}=" "$file"; then
    sed -i -E "s|^(export )?${VAR}=.*$|${prefisso}${VAR}=\"${valore}\"|" "$file"
  else
    {
      echo ""
      echo "# Chiavi Fernet dei segreti cifrati nel DB (crypto_service), separate dalla"
      echo "# SECRET_KEY. Cifra la prima, decifrano tutte. Si gestiscono con"
      echo "# backend/scripts/chiave-cifratura-aggiungi.sh, mai a mano."
      echo "${prefisso}${VAR}=\"${valore}\""
    } >> "$file"
  fi
}

# Scopo: copia di sicurezza dei due file prima di toccarli.
backup() {
  local stamp
  # I nanosecondi: due giri nello stesso secondo non si sovrascrivono la copia.
  stamp="$(date +%Y%m%d-%H%M%S-%N)"
  mkdir -p "$BACKUP_DIR"
  chmod 700 "$BACKUP_DIR"
  for f in "$FILE_SHELL" "$FILE_SYSTEMD"; do
    cp -p --no-clobber "$f" "$BACKUP_DIR/${f#.}.$stamp"
    chmod 600 "$BACKUP_DIR/${f#.}.$stamp"
  done
  echo "Copia dei due file in backend/$BACKUP_DIR/ (*.$stamp)."
}

conferma() {
  local risposta
  read -r -p "$1 [s/N] " risposta
  [[ "$risposta" == "s" || "$risposta" == "S" ]]
}

attuale="$(leggi "$FILE_SHELL")"
attuale_systemd="$(leggi "$FILE_SYSTEMD")"
if [[ "$attuale" != "$attuale_systemd" ]]; then
  echo "ERRORE: ${VAR} e' diversa fra backend/$FILE_SHELL e backend/$FILE_SYSTEMD." >&2
  echo "        Allinearle a mano prima di proseguire: lo script non sceglie quale vale." >&2
  exit 1
fi

# Le chiavi con la stessa regola di `settings.parse_chiavi_cifratura`: spazi ai
# bordi tolti, voci vuote scartate («k1, ,k2,» sono due chiavi, non quattro).
# Da qui in poi l'elenco si riscrive sempre in questa forma pulita.
chiavi=()
IFS=',' read -r -a grezze <<< "$attuale"
for c in "${grezze[@]}"; do
  c="${c//[[:space:]]/}"
  if [[ -n "$c" ]]; then chiavi+=("$c"); fi
done
n_attuali="${#chiavi[@]}"
attuale="$(IFS=','; echo "${chiavi[*]}")"

if [[ "$MODO" == "aggiungi" ]]; then
  if (( n_attuali > 0 )); then
    echo "${VAR} c'e' gia' ($n_attuali chiave/i). Aggiungerne una in testa e' una ROTAZIONE:"
    echo "dopo servono chiave-cifratura-ricifra.sh e poi --togli-vecchie."
    conferma "Aggiungo una chiave nuova in testa?" || { echo "Niente di fatto."; exit 0; }
  fi
  nuova="$("$PY" -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  valore="$nuova${attuale:+,$attuale}"
  backup
  scrivi "$FILE_SHELL" "$valore" "export "
  scrivi "$FILE_SYSTEMD" "$valore" ""
  echo "✅ Chiave nuova in testa: ora ${VAR} ha $((n_attuali + 1)) chiave/i, nei due file."
  echo "Prossimo passo:"
  if (( n_attuali == 0 )); then
    echo "  backend/scripts/chiave-cifratura-ricifra.sh --migrazione   (segreti cifrati prima del 2026-09-28)"
  else
    echo "  backend/scripts/chiave-cifratura-ricifra.sh"
  fi
  echo "  poi: sudo systemctl restart zeroerp-gunicorn"
  exit 0
fi

# --- --togli-vecchie ---
if (( n_attuali <= 1 )); then
  echo "${VAR} ha $n_attuali chiave: non c'e' niente da togliere."
  exit 0
fi
prima="${chiavi[0]}"
echo "Verifico che la sola prima chiave apra tutti i segreti del DB (dry-run)..."
if ! (
  set -a
  # shellcheck disable=SC1090
  source "$FILE_SYSTEMD"
  set +a
  export "${VAR}=${prima}"
  "$PY" manage.py ricifra_campi_cifrati --dry-run
); then
  echo "ERRORE: con la sola prima chiave qualche segreto non si apre." >&2
  echo "        Lanciare prima backend/scripts/chiave-cifratura-ricifra.sh. Niente e' stato toccato." >&2
  exit 1
fi
conferma "Tolgo le $((n_attuali - 1)) chiave/i vecchie e tengo solo la prima?" || { echo "Niente di fatto."; exit 0; }
backup
scrivi "$FILE_SHELL" "$prima" "export "
scrivi "$FILE_SYSTEMD" "$prima" ""
echo "✅ ${VAR} ha ora una sola chiave, nei due file."
echo "Prossimo passo: sudo systemctl restart zeroerp-gunicorn"
