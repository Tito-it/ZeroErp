# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Incluso da ogni smoke bash (`source`), subito dopo `BASE_URL=`, di
#        norma attraverso `_smoke_auth.sh` (il login degli smoke).
#        Gli smoke parlano con Gunicorn DIRETTO, in HTTP su loopback; fuori
#        da DEBUG Django redirige in HTTPS (`SECURE_SSL_REDIRECT`), e senza
#        questo file ogni chiamata sarebbe un 301.
#        Ci si dichiara HTTPS come fa Nginx (`X-Forwarded-Proto: https`, letto
#        da `SECURE_PROXY_SSL_HEADER`). E' legittimo perche' Gunicorn ascolta
#        solo su loopback: lo puo' dire solo un processo di questa macchina.
#        ⭐ E si dichiara la PROVENIENZA come fa Nginx (`X-Forwarded-For`,
#        `$proxy_add_x_forwarded_for`): dal 2026-09-25 il login la pretende per
#        il freno sulla credenziale e, senza, risponde `E_AUTH_CHIAMATA_NON_VALIDA`
#        (fail-closed, `get_client_ip`). Il valore e' vero: lo smoke parte da
#        questa macchina, 127.0.0.1. Ripetuto `DJANGO_TRUSTED_PROXY_COUNT` volte
#        (default 1), perche' il backend legge l'N-esimo valore da destra.
# Note: ⭐ `curl` diventa una funzione, quindi vale per OGNI chiamata dello
#       script, anche dentro `$(...)` e negli helper, senza toccarle una per
#       una. ⛔ Una chiamata `command curl` la aggirerebbe.
#       Presidio: `apps/core/tests/api/test_https_header.py` (ogni smoke che usa
#       `BASE_URL` include questo file).
# ------------------------------------------------------------

_smoke_xff=127.0.0.1
for ((_i = 1; _i < ${DJANGO_TRUSTED_PROXY_COUNT:-1}; _i++)); do _smoke_xff+=", 127.0.0.1"; done
SMOKE_X_FORWARDED_FOR="$_smoke_xff"
unset _smoke_xff _i

# ⭐ Dal 2026-10-20 una POST che scrive senza `Idempotency-Key` e' un 400
#    (brief-be-verifica-documentazione-api §A5): la chiave la mette questa
#    funzione, una per chiamata, come l'interceptor del frontend. Solo sulle
#    POST — la regola del backend — e solo se la chiamata non ne porta una sua
#    (gli smoke che provano il replay la passano apposta). Una POST la si
#    riconosce da `-X POST`/`--request POST`, o da un corpo senza `-X`, che per
#    curl vuol dire POST.
_smoke_e_post_senza_chiave() {
  local metodo="" corpo=0 prec=""
  for a in "$@"; do
    case "$prec" in
      -X|--request) metodo="$a" ;;
      -H|--header) [[ "${a,,}" == idempotency-key:* ]] && return 1 ;;
    esac
    case "$a" in
      -d|--data|--data-raw|--data-binary|--data-urlencode|-F|--form|--json) corpo=1 ;;
      --data=*|--data-raw=*|--data-binary=*|--json=*) corpo=1 ;;
    esac
    prec="$a"
  done
  [[ "${metodo^^}" == POST || ( -z "$metodo" && $corpo -eq 1 ) ]]
}

curl() {
  local chiave=()
  if _smoke_e_post_senza_chiave "$@"; then
    chiave=(-H "Idempotency-Key: smoke-$(date +%s%N)-${RANDOM}")
  fi
  command curl -H "X-Forwarded-Proto: https" \
               -H "X-Forwarded-For: ${SMOKE_X_FORWARDED_FOR}" "${chiave[@]}" "$@"
}
