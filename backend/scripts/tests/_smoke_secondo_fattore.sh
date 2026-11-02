# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Incluso (`source`) da `_smoke_auth.sh`, dopo `_smoke_https.sh`: gli
#        smoke includono `_smoke_auth.sh` e fanno il login con `smoke_login`.
#        Dal 2026-10-02 (brief-be-fe-sicurezza-header-token-mfa §3.4-bis) un
#        accesso col secondo fattore attivo risponde al login con una SFIDA e
#        nessun token. `curl_login` si usa al posto di `curl` per la chiamata
#        di login: se arriva la sfida fa il secondo passo col codice calcolato
#        dal segreto in SMOKE_TOTP_SECRET, e restituisce ESATTAMENTE cio' che lo
#        script si aspetta dal login di prima — `{"access": ...}` in testa al
#        corpo, il cookie del refresh nel file degli header, lo status.
#        Senza sfida (utente senza secondo fattore) e' `curl` e basta.
# Uso: come curl, con le stesse opzioni (`-o`, `-w`, `-D` comprese):
#   curl_login -s -w '\n%{http_code}' -D "$HDR" -H "Content-Type: application/json" \
#       -d "{...}" "${BASE_URL}/api/v1/admin/token/" > "$TMPFILE"
# Note: il segreto e' la chiave mostrata alla configurazione (pagina Sicurezza)
#       dell'utente degli smoke (SMOKE_USER), esportata come le altre variabili
#       d'ambiente (env.sh). Il codice lo calcola `_smoke_totp_codice.py` col
#       python del venv del backend, che aspetta un passo nuovo se l'ultimo e'
#       gia' stato usato: il DB ne accetta uno solo per intervallo.
#       Presidio: `test_https_header.test_ogni_login_degli_smoke_passa_da_curl_login`.
# ------------------------------------------------------------

_SMOKE_DIR_SF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMOKE_PYTHON="${SMOKE_PYTHON:-${_SMOKE_DIR_SF}/../../.venv/bin/python}"

curl_login() {
  local out_file="" w_fmt="" hdr_file="" url="" args=()
  while (($#)); do
    case "$1" in
      -o) out_file="$2"; shift 2 ;;
      -w) w_fmt="$2"; shift 2 ;;
      -D) hdr_file="$2"; shift 2 ;;
      *) [[ "$1" == *"/token/"* ]] && url="$1"; args+=("$1"); shift ;;
    esac
  done

  local corpo hdr status
  corpo="$(mktemp)"; hdr="$(mktemp)"
  status=$(curl "${args[@]}" -o "$corpo" -D "$hdr" -w '%{http_code}')

  if [[ "$status" == "200" ]] && grep -q '"two_factor_required": *true' "$corpo"; then
    local sfida codice
    sfida=$("$SMOKE_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["sfida"])' "$corpo")
    if codice=$("$SMOKE_PYTHON" "${_SMOKE_DIR_SF}/_smoke_totp_codice.py"); then
      status=$(curl -s -o "$corpo" -D "$hdr" -w '%{http_code}' \
      -H "Content-Type: application/json" \
      -d "{\"sfida\":\"${sfida}\",\"codice\":\"${codice}\"}" \
        "${url%token/}token/secondo-fattore/")
      # Il secondo passo risponde nell'envelope ({"data": {...}}): lo script
      # legge `.access` in testa, come dal login senza secondo fattore.
      if [[ "$status" == "200" ]]; then
        "$SMOKE_PYTHON" -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p))["data"]; json.dump(d, open(p, "w"))' "$corpo"
      fi
    else
      # ⛔ Mai un ritorno non-zero: gli smoke lanciano il login con
      #    `2>/dev/null` e `set -e`, e lo script si chiuderebbe IN SILENZIO al
      #    passo 0 (collaudo di Tid, 2026-10-02). Un login fallito, invece, lo
      #    script lo dichiara dal suo ramo d'errore, con questa frase.
      local perche
      if [[ -z "${SMOKE_TOTP_SECRET:-}" ]]; then
        perche="manca SMOKE_TOTP_SECRET (la chiave mostrata alla configurazione, pagina Sicurezza)"
      else
        perche="SMOKE_TOTP_SECRET c'e' ma il codice non si calcola con ${SMOKE_PYTHON} (vedi il messaggio sul terminale)"
      fi
      printf '{"error": {"code": "SMOKE_SECONDO_FATTORE", "message": "Il login chiede il secondo fattore: %s."}}' "$perche" > "$corpo"
      : > "$hdr"
      status=401
    fi
  fi

  [[ -n "$hdr_file" ]] && cp "$hdr" "$hdr_file"
  if [[ -n "$out_file" ]]; then cp "$corpo" "$out_file"; else cat "$corpo"; fi
  [[ -n "$w_fmt" ]] && printf '%b' "${w_fmt//%\{http_code\}/$status}"
  rm -f "$corpo" "$hdr"
}
