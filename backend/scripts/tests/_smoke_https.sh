# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Incluso da ogni smoke bash (`source`), subito dopo `BASE_URL=`.
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

curl() {
  command curl -H "X-Forwarded-Proto: https" \
               -H "X-Forwarded-For: ${SMOKE_X_FORWARDED_FOR}" "$@"
}
