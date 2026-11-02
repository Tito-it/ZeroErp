# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il refresh token JWT viaggia in un cookie HttpOnly, mai nel corpo
#        (brief-be-fe-sicurezza-header-token-mfa §2, dal 2026-09-28): lo
#        script della pagina non lo vede, quindi uno script iniettato non lo
#        puo' leggere ne' spedire altrove. L'access token resta nel corpo e il
#        frontend lo tiene solo in memoria.
#        UNA sede per nome, attributi, lettura, scrittura e cancellazione: la
#        usano login e refresh dei tre canali, logout, cambio password e cambio
#        emittente attivo. Due copie degli attributi divergerebbero, e un
#        cookie scritto con un `Path` e cancellato con un altro non si cancella.
#        Qui anche la LETTURA dei claim del refresh presentato, con la firma
#        verificata (`claims_refresh_firmati`): la usano logout e refresh.
# Note: ⭐ `Path=/api/v1/` e non il solo endpoint di refresh: il refresh serve
#       anche a logout (`/auth/logout/`), cambio emittente
#       (`/core/me/emittente-attivo/`) e cambio password, che stanno altrove
#       (decisione 2026-09-28). Resta HttpOnly e `SameSite=Strict`: nessun
#       altro sito lo fa partire.
#       ⛔ CSRF: il refresh si autentica col SOLO cookie (nessun Bearer), quindi
#       pretende anche l'header `X-Requested-With: XMLHttpRequest`
#       (`richiedi_header_anti_csrf`). Un form o un link di un altro sito non
#       puo' mandare un header custom, e senza CORS il browser non lo
#       permette nemmeno a uno script altrui. Logout e cambio emittente non ne
#       hanno bisogno: pretendono gia' il Bearer, che un altro sito non ha.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal

import jwt
from django.conf import settings
from django.http import HttpRequest, HttpResponseBase, JsonResponse
from rest_framework_simplejwt.exceptions import TokenBackendError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.state import token_backend

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.services.service_errors import ServiceError

REFRESH_COOKIE_NAME = "zeroerp_refresh"
REFRESH_COOKIE_PATH = "/api/v1/"
REFRESH_COOKIE_SAMESITE: Literal["Strict"] = "Strict"

# L'header che il frontend manda sul refresh, e che un altro sito non puo'
# mandare. Il valore e' quello che le librerie mettono per convenzione.
logger = logging.getLogger("security")

ANTI_CSRF_HEADER = "X-Requested-With"
ANTI_CSRF_VALORE = "XMLHttpRequest"


# Scopo: Scrive il refresh nel cookie. La durata e' quella del token
#        (`REFRESH_TOKEN_LIFETIME`): il cookie non sopravvive a cio' che porta.
def scrivi_refresh_cookie(response: HttpResponseBase, refresh: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh,
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        path=REFRESH_COOKIE_PATH,
        secure=settings.REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite=REFRESH_COOKIE_SAMESITE,
    )


# Scopo: Cancella il cookie, con lo STESSO path e samesite con cui e' stato
#        scritto: altrimenti il browser lo tratta come un cookie diverso e
#        quello vero resta.
def cancella_refresh_cookie(response: HttpResponseBase) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite=REFRESH_COOKIE_SAMESITE,
    )


# Scopo: Il refresh presentato dal browser, o None se il cookie manca o e'
#        vuoto. Accetta la richiesta DRF o quella Django.
def leggi_refresh_cookie(request: HttpRequest) -> str | None:
    valore = request.COOKIES.get(REFRESH_COOKIE_NAME)
    return valore or None


# Scopo: Rifiuta con 403 `E_PERMISSION_DENIED` una richiesta autenticata dal
#        solo cookie che non porta l'header anti-CSRF (vedi le note in testa).
def richiedi_header_anti_csrf(request: HttpRequest) -> None:
    ricevuto = request.headers.get(ANTI_CSRF_HEADER)
    if ricevuto != ANTI_CSRF_VALORE:
        # Il valore ricevuto (non e' un segreto) distingue i due casi che la
        # risposta confonde: header ASSENTE (client vecchio, o un altro sito)
        # e header CAMBIATO lungo la strada (browser o proxy che lo
        # riscrivono). Troncato: lo scrive il client.
        logger.warning(
            "security.refresh_senza_header_anti_csrf ricevuto=%r user_agent=%r",
            ricevuto[:80] if ricevuto else ricevuto,
            (request.headers.get("User-Agent") or "")[:120],
        )
        raise ServiceError(
            code="E_PERMISSION_DENIED",
            message="Richiesta non ammessa.",
            detail=f"Rinnovo della sessione senza l'header {ANTI_CSRF_HEADER}: {ANTI_CSRF_VALORE}.",
        )


# Scopo: Sposta il refresh dal corpo (dove lo mettono SimpleJWT e i
#        serializer) al cookie. Ritorna il refresh spostato, o None se il corpo
#        non ne aveva uno. Il corpo si modifica sul posto.
def sposta_refresh_nel_cookie(response: HttpResponseBase, dati: dict | None) -> str | None:
    if not dati:
        return None
    refresh = dati.pop("refresh", None)
    if refresh:
        scrivi_refresh_cookie(response, str(refresh))
    return refresh


# Scopo: i claim del refresh presentato, con la FIRMA verificata e la
#        scadenza no. `None` se il token non e' nostro, e' malformato o non e'
#        un refresh.
#        Estratto il 2026-09-28 (regola del 2, ok Tid) da `logout_view`: la
#        seconda occorrenza era il guard cross-namespace del refresh, che
#        leggeva la veste da un token decodificato alla cieca — un token
#        illeggibile diventava «veste assente», cioe' 403 invece di 401 (E-8
#        dell'analisi difetti doc API core).
# ⛔ La firma si verifica: dai claim si decide QUALE sessione chiude il logout
#    e QUALE veste ha il refresh; da un token non verificato li sceglierebbe
#    chiunque.
# ⚠️ La scadenza no: il logout con un refresh scaduto deve chiudere lo stesso
#    la sessione (il successore, emesso da una rotazione, puo' essere vivo), e
#    nel refresh la scadenza la giudica SimpleJWT subito dopo, con la
#    blacklist.
# ⚠️ Non `RefreshToken(...)`: rifiuta il token gia' in blacklist, che per il
#    logout e' proprio il caso da chiudere (il refresh ruotato da una
#    richiesta in volo).
def claims_refresh_firmati(refresh: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            refresh,
            # SimpleJWT annota `Token`, ma lui stesso la chiama col token
            # grezzo (str) in `TokenBackend.decode`.
            token_backend.get_verifying_key(refresh),  # type: ignore[arg-type]
            algorithms=[token_backend.algorithm],
            audience=token_backend.audience,
            issuer=token_backend.issuer,
            options={
                "verify_aud": token_backend.audience is not None,
                "verify_exp": False,
            },
        )
    except (jwt.PyJWTError, TokenBackendError):
        return None
    if payload.get(api_settings.TOKEN_TYPE_CLAIM) != "refresh":
        return None
    return payload


# Scopo: `handle_post_json` per un POST che apre o riscrive la sessione
#        (cambio password, cambio emittente attivo). Il gestore restituisce
#        `(dati, refresh)`: i dati vanno nel corpo, il refresh nel cookie —
#        SOLO se la risposta e' un 200. Un errore sollevato dopo l'emissione
#        (il gestore, il commit) non lascia al browser il refresh di una
#        sessione che il corpo dichiara fallita.
#        Estratto il 2026-09-28 (regola del 2, ok Tid): era scritto uguale
#        nelle due view, con un dizionario di appoggio chiuso nel gestore.
def handle_post_json_con_refresh(
    request: Any,
    handler: Callable[[dict[str, Any]], tuple[dict[str, Any], str]],
) -> JsonResponse:
    emesso: dict[str, str] = {}

    def _gestore(payload: dict[str, Any]) -> dict[str, Any]:
        dati, refresh = handler(payload)
        emesso["refresh"] = refresh
        return dati

    response = handle_post_json(request, handler=_gestore)
    if "refresh" in emesso and response.status_code == 200:
        scrivi_refresh_cookie(response, emesso["refresh"])
    return response
