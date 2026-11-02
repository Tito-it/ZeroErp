# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Il login degli smoke bash, in un posto solo. Incluso (`source`) da ogni
#        smoke che fa il login, subito dopo `BASE_URL=`, al posto dei tre include
#        di prima: porta con se' `_smoke_https.sh` (HTTPS e provenienza come
#        Nginx), `_smoke_secondo_fattore.sh` (`curl_login`, la sfida TOTP) e
#        `_smoke_refresh.sh` (il cookie del refresh).
#        `smoke_login` fa il login + l'eventuale secondo passo + l'estrazione
#        del token, e se fallisce lo DICE ed esce: lo smoke non ripete niente.
# Uso:
#   BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
#   source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"
#   ...
#   smoke_login                       # -> TOKEN (e AUTH_STATUS/AUTH_BODY)
#   smoke_login -D "${TMPFILE}.hdr"   # salva gli header (cookie del refresh)
# Credenziali (le legge l'include, dagli argomenti dello smoke):
#   USERNAME = SMOKE_USER: l'utente `dev.smoke`, dedicato agli smoke e
#              creato dal provisioning di sviluppo (`manage.py
#              provision_utenti_sviluppo`, che stampa anche le variabili;
#              docs/it/dev/infra/comandi-utili-run-book.md §11). Prima era
#              `smoke`, creato a mano (2026-10-02). Nessun ripiego: senza
#              SMOKE_USER lo smoke si ferma e lo dice (fino al 2026-10-16
#              ripiegava sull'utente personale `tid`).
#   PASSWORD = primo argomento dello smoke, o SMOKE_PASSWORD; se manca la si
#              chiede a terminale (con `--senza-prompt`: errore ed uscita).
#   Uno smoke che vuole un utente diverso riassegna USERNAME/PASSWORD dopo
#   l'include (es. smoke-test-rls-emittente-operatore.sh).
# Opzioni di smoke_login:
#   -D FILE         passa `-D FILE` al login: gli header (il cookie del refresh)
#                   restano nel file. Implica il login vero.
#   --login-vero    mai SMOKE_TOKEN: lo smoke prova proprio il login (la sua
#                   risposta, la sessione che apre, il refresh).
#   --senza-prompt  password mancante = errore, non domanda a terminale.
#   --uscita N      codice d'uscita dei fallimenti (default 1).
# ⭐ Un solo login per una sessione di smoke: `eval "$(scripts/tests/smoke-login.sh)"`
#    esporta SMOKE_TOKEN, e `smoke_login` lo RIUSA senza login (niente attesa
#    del codice TOTP, niente tentativi sul freno) se:
#      - il claim `exp` dice che vale ancora piu' di SMOKE_TOKEN_MARGINE
#        secondi (default 180: la durata di uno smoke lungo);
#      - il backend lo accetta (`GET /api/v1/core/me/` 200: una sessione
#        revocata o un'identita' disattivata lo invalidano prima di `exp`);
#      - e' di USERNAME (lo username di `/me/`; il JWT porta solo `user_id`):
#        un token dell'utente generale non entra in uno smoke che ne vuole un
#        altro.
#    Altrimenti dice perche' e fa il login vero. ⚠️ L'access dura 10 minuti
#    (`SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]`, settings.py: access BREVE, decisione
#    2026-09-28): dopo ~7 minuti dall'export ogni smoke torna a fare il login
#    da se', che funziona come sempre. Per ripartire col login unico si rilancia
#    `smoke-login.sh`. Uno smoke non puo' aggiornare SMOKE_TOKEN della shell
#    che lo ha lanciato.
# Note: ⛔ Sotto `set -e` mai un ritorno non-zero silenzioso: ogni fallimento
#       stampa la causa ed esce col codice scelto. ⛔ `smoke_login` imposta
#       variabili dello smoke: si chiama diretto, mai dentro `$(...)`.
#       I login che il BB non copre restano espliciti con `curl_login` e un
#       commento `# login esplicito: <perche'>` (es. il secondo login di
#       smoke-test-core.sh, il login con password errata di audit-logging).
#       Presidio: `apps/core/tests/api/test_https_header.py` (SmokeBashTests).
# ------------------------------------------------------------

_SMOKE_DIR_AUTH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_SMOKE_DIR_AUTH}/_smoke_https.sh"
source "${_SMOKE_DIR_AUTH}/_smoke_secondo_fattore.sh"
source "${_SMOKE_DIR_AUTH}/_smoke_refresh.sh"

USERNAME="${SMOKE_USER:-}"
PASSWORD="${1:-${SMOKE_PASSWORD:-}}"
SMOKE_TOKEN_MARGINE="${SMOKE_TOKEN_MARGINE:-180}"
SMOKE_LOGIN_FONTE=""

_SMOKE_AUTH_ROSSO=$'\033[0;31m'
_SMOKE_AUTH_NC=$'\033[0m'

# Scopo: Il valore di un claim del JWT dato (payload base64url); vuoto se il
#        token non si legge o il claim manca. Non fallisce mai.
smoke_jwt_claim() {
  python3 - "$1" "$2" 2>/dev/null <<'PY' || true
import base64, json, sys
try:
    p = sys.argv[1].split(".")[1]
    v = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4))).get(sys.argv[2])
    print("" if v is None else v)
except Exception:
    pass
PY
}

# Scopo: Se SMOKE_TOKEN si puo' riusare per USERNAME. Imposta
#        _SMOKE_TOKEN_PERCHE (vuoto = riusabile, altrimenti il motivo) e
#        _SMOKE_TOKEN_RESTO (secondi di validita'). Ritorna sempre 0.
_smoke_token_riusabile() {
  local tok="$1" exp utente
  _SMOKE_TOKEN_PERCHE=""; _SMOKE_TOKEN_RESTO=0
  exp="$(smoke_jwt_claim "$tok" exp)"
  if ! [[ "$exp" =~ ^[0-9]+$ ]]; then
    _SMOKE_TOKEN_PERCHE="non e' un JWT leggibile"; return 0
  fi
  _SMOKE_TOKEN_RESTO=$((exp - $(date +%s)))
  if ((_SMOKE_TOKEN_RESTO <= SMOKE_TOKEN_MARGINE)); then
    _SMOKE_TOKEN_PERCHE="scaduto o in scadenza (${_SMOKE_TOKEN_RESTO}s, margine ${SMOKE_TOKEN_MARGINE}s)"
    return 0
  fi
  utente="$(curl -s -H "Authorization: Bearer ${tok}" "${BASE_URL}/api/v1/core/me/" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["utente"]["username"])' 2>/dev/null || true)"
  if [[ -z "$utente" ]]; then
    _SMOKE_TOKEN_PERCHE="il backend non lo accetta (GET /api/v1/core/me/)"
  elif [[ "$utente" != "$USERNAME" ]]; then
    _SMOKE_TOKEN_PERCHE="e' di '${utente}', non di '${USERNAME}'"
  fi
  return 0
}

# Scopo: Il login dello smoke: TOKEN pronto, o un messaggio e l'uscita.
#        Imposta TOKEN, AUTH_STATUS, AUTH_BODY (vuoto se riusa SMOKE_TOKEN) e
#        SMOKE_LOGIN_FONTE (`login` | `SMOKE_TOKEN`). Opzioni: vedi testata.
smoke_login() {
  local hdr_file="" uscita=1 prompt=1 vero=0
  while (($#)); do
    case "$1" in
      -D) hdr_file="$2"; vero=1; shift 2 ;;
      --login-vero) vero=1; shift ;;
      --senza-prompt) prompt=0; shift ;;
      --uscita) uscita="$2"; shift 2 ;;
      *) echo -e "${_SMOKE_AUTH_ROSSO}ERRORE: smoke_login, opzione sconosciuta '$1'${_SMOKE_AUTH_NC}"; exit 2 ;;
    esac
  done
  TOKEN=""; AUTH_STATUS=""; AUTH_BODY=""; SMOKE_LOGIN_FONTE=""

  if [[ -z "$USERNAME" ]]; then
    echo -e "${_SMOKE_AUTH_ROSSO}ERRORE: utente degli smoke non impostato (SMOKE_USER)${_SMOKE_AUTH_NC}"
    exit "$uscita"
  fi

  if [[ -n "${SMOKE_TOKEN:-}" ]]; then
    if ((vero)); then
      echo "  (SMOKE_TOKEN non usato: questo smoke prova il login vero)"
    else
      _smoke_token_riusabile "$SMOKE_TOKEN"
      if [[ -z "$_SMOKE_TOKEN_PERCHE" ]]; then
        TOKEN="$SMOKE_TOKEN"; AUTH_STATUS=200; SMOKE_LOGIN_FONTE="SMOKE_TOKEN"
        echo "  (login: riuso SMOKE_TOKEN di '${USERNAME}', vale ancora ${_SMOKE_TOKEN_RESTO}s)"
        return 0
      fi
      echo "  (SMOKE_TOKEN non riusabile: ${_SMOKE_TOKEN_PERCHE}; faccio il login)"
    fi
  fi

  if [[ -z "$PASSWORD" ]] && ((prompt)); then
    echo -n "Password per utente '${USERNAME}': "
    read -rs PASSWORD || true
    echo ""
  fi
  if [[ -z "$PASSWORD" ]]; then
    echo -e "${_SMOKE_AUTH_ROSSO}Password mancante${_SMOKE_AUTH_NC} (arg1 o SMOKE_PASSWORD)"
    exit "$uscita"
  fi

  local corpo credenziali opz_hdr=()
  [[ -n "$hdr_file" ]] && opz_hdr=(-D "$hdr_file")
  # JSON costruito da python: una password con virgolette o barre resta valida.
  credenziali="$(python3 -c 'import json,sys; print(json.dumps({"username": sys.argv[1], "password": sys.argv[2]}))' \
    "$USERNAME" "$PASSWORD")"
  corpo="$(mktemp)"
  curl_login -s -w '\n%{http_code}' "${opz_hdr[@]}" \
    -H "Content-Type: application/json" \
    -d "$credenziali" \
    "${BASE_URL}/api/v1/admin/token/" > "$corpo" 2>/dev/null || true
  AUTH_STATUS="$(tail -1 "$corpo")"
  AUTH_BODY="$(sed '$d' "$corpo")"
  rm -f "$corpo"

  if [[ "$AUTH_STATUS" != "200" ]]; then
    echo -e "${_SMOKE_AUTH_ROSSO}ERRORE: autenticazione fallita (HTTP ${AUTH_STATUS:-?})${_SMOKE_AUTH_NC}"
    echo "$AUTH_BODY" | head -c 300
    echo ""
    exit "$uscita"
  fi
  TOKEN="$(printf '%s' "$AUTH_BODY" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("access") or "")' 2>/dev/null || true)"
  if [[ -z "$TOKEN" ]]; then
    echo -e "${_SMOKE_AUTH_ROSSO}ERRORE: token JWT non trovato nella risposta${_SMOKE_AUTH_NC}"
    exit "$uscita"
  fi
  SMOKE_LOGIN_FONTE="login"
  return 0
}
