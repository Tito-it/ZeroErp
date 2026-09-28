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
# Note: ⭐ `curl` diventa una funzione, quindi vale per OGNI chiamata dello
#       script, anche dentro `$(...)` e negli helper, senza toccarle una per
#       una. ⛔ Una chiamata `command curl` la aggirerebbe.
#       Presidio: `apps/core/tests/api/test_https_header.py` (ogni smoke che usa
#       `BASE_URL` include questo file).
# ------------------------------------------------------------

curl() { command curl -H "X-Forwarded-Proto: https" "$@"; }
