# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Incluso (`source`) da `_smoke_auth.sh`: lo usano gli smoke che provano
#        il refresh token JWT (login con `smoke_login -D <file header>`).
#        Dal 2026-09-28 il refresh viaggia nel cookie HttpOnly
#        `zeroerp_refresh`, mai nel corpo (brief-be-fe-sicurezza-header-token-mfa
#        §2): si legge dal `Set-Cookie` della risposta e si ripresenta come fa
#        il browser, col cookie e l'header anti-CSRF che il refresh pretende.
# Uso:
#   curl ... -D "$HDRFILE" .../admin/token/        # login: salva gli header
#   REFRESH=$(refresh_dal_set_cookie "$HDRFILE")
#   curl_refresh "$REFRESH" -s -X POST .../admin/token/refresh/
# Note: nome del cookie e header sono quelli di `apps/core/api/refresh_cookie.py`;
#       li confronta `test_auth_views.test_nome_cookie_e_header_uguali_nei_tre_linguaggi`.
# ------------------------------------------------------------

SMOKE_REFRESH_COOKIE="zeroerp_refresh"

# Scopo: il valore del cookie del refresh negli header salvati con `curl -D`
#        (l'ultimo, se la risposta ne scrive piu' d'uno); vuoto se assente.
refresh_dal_set_cookie() {
  tr -d '\r' < "$1" \
    | sed -nE "s/^[Ss]et-[Cc]ookie: ${SMOKE_REFRESH_COOKIE}=([^;]*).*/\1/p" \
    | tail -1
}

# Scopo: curl che presenta il refresh dato come il browser: cookie + header
#        anti-CSRF. Gli argomenti dopo il primo passano a curl cosi' come sono.
curl_refresh() {
  local refresh="$1"
  shift
  curl -H "Cookie: ${SMOKE_REFRESH_COOKIE}=${refresh}" \
       -H "X-Requested-With: XMLHttpRequest" "$@"
}
