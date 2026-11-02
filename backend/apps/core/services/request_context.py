# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gestione contesto richiesta.
# ------------------------------------------------------------


from __future__ import annotations

from contextvars import ContextVar

# Contesto richiesta API (request_id/idempotency_key) accessibile nei layer core.

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_idempotency_key_var: ContextVar[str | None] = ContextVar("idempotency_key", default=None)


# Scopo: Aggiorna `request_context` con i valori richiesti dal flusso corrente.
def set_request_context(*, request_id: str | None, idempotency_key: str | None) -> None:
    _request_id_var.set(request_id)
    _idempotency_key_var.set(idempotency_key)


# Scopo: Gestisce `clear_request_context` nel flusso applicativo del modulo.
def clear_request_context() -> None:
    set_request_context(request_id=None, idempotency_key=None)


# Scopo: Recupera `request_id` dal contesto applicativo o dal database.
def get_request_id() -> str | None:
    return _request_id_var.get()


# Scopo: Recupera `idempotency_key` dal contesto applicativo o dal database.
def get_idempotency_key() -> str | None:
    return _idempotency_key_var.get()


# --------------- HTTP request helpers ---------------

import ipaddress
import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest

from apps.core.services.auth_constants import JWT_CLAIM_SID
from apps.core.services.service_errors import ServiceError


# Scopo: Estrae l'IP del client dalla request, fidandosi solo dei proxy dichiarati.
# ⭐ E' l'UNICA sede della regola «quale hop e' fidato» (audit, log richieste,
# throttle, freno del login): `settings.TRUSTED_PROXY_COUNT` = N.
#   - N = 0 → `REMOTE_ADDR`; `X-Forwarded-For` ignorato (lo scrive il client);
#   - N > 0 → l'N-esimo valore di `X-Forwarded-For` DA DESTRA: ogni proxy
#     (Nginx: `$proxy_add_x_forwarded_for`) accoda l'indirizzo da cui riceve,
#     quindi solo gli ultimi N valori sono stati scritti da un proxy fidato.
#     ⛔ Mai il primo: e' quello che il client dichiara, e lo cambia a piacere.
# Ritorna una stringa valida per `inet`, oppure None se l'IP non si ricava
# (header assente o con meno di N valori — la richiesta non e' passata dalla
# catena dichiarata —, valore malformato). None non si sostituisce con un
# ripiego: chi ne fa una chiave di sicurezza deve rifiutare, non indovinare.
def get_client_ip(request: HttpRequest) -> str | None:
    proxy_fidati = settings.TRUSTED_PROXY_COUNT
    if proxy_fidati == 0:
        return _normalizza_ip(request.META.get("REMOTE_ADDR"))
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if not xff:
        return None
    valori = xff.split(",")
    if len(valori) < proxy_fidati:
        return None
    return _normalizza_ip(valori[-proxy_fidati])


# Scopo: La `HttpRequest` di Django sotto la `Request` di DRF (o la richiesta
#        stessa, se e' gia' di Django): per i BB che leggono `META` e `path`
#        e per chi li chiama. ⭐ Regola del 2 (2026-10-02): era scritto a mano
#        in dieci view.
def richiesta_django(request: Any) -> HttpRequest:
    return getattr(request, "_request", request)


# Scopo: Il `sid` (la sessione) del JWT della richiesta corrente; None se la
#        richiesta non porta un token (una `HttpRequest` di Django, un test).
#        ⭐ Regola del 2 (2026-10-03): era `_get_current_sid` di
#        `sessioni_view`; il secondo consumatore e' il freno della password
#        dentro una sessione, che chiude QUELLA sessione.
def sid_corrente(request: Any) -> str | None:
    auth = getattr(request, "auth", None)
    return str(auth.get(JWT_CLAIM_SID, "")) if auth else None


# Scopo: La provenienza di una richiesta di autenticazione, o il rifiuto:
#        la provenienza e' la chiave del freno sulla credenziale, e senza il
#        freno non si applica (fail-closed). Causa tipica del rifiuto: la
#        richiesta non e' passata dalla catena di proxy dichiarata
#        (DJANGO_TRUSTED_PROXY_COUNT). Accetta la `Request` di DRF o la
#        `HttpRequest` di Django.
#        ⭐ Regola del 2: login, secondo passo e self-service del secondo
#        fattore. Fino al 2026-10-02 il BB dava il solo errore e la lettura
#        era copiata nei tre chiamanti: ora e' una.
def provenienza_obbligatoria(request: Any) -> str:
    django_request = richiesta_django(request)
    provenienza = get_client_ip(django_request)
    if provenienza is None:
        raise _errore_provenienza_assente(django_request)
    return provenienza


# Scopo: Il rifiuto senza provenienza; il log di sicurezza lo scrive qui.
def _errore_provenienza_assente(request: HttpRequest) -> ServiceError:
    logging.getLogger("security").error(
        "security.provenienza_assente path=%s remote_addr=%s xff=%s",
        request.path,
        request.META.get("REMOTE_ADDR"),
        request.META.get("HTTP_X_FORWARDED_FOR"),
    )
    return ServiceError(
        code="E_AUTH_CHIAMATA_NON_VALIDA",
        message="Chiamata non valida: provenienza assente.",
        detail="IP del chiamante non ricavabile dalla catena di proxy dichiarata.",
    )


# Scopo: Valida un indirizzo IP (v4/v6) e lo riporta in forma canonica; None se non lo e'.
def _normalizza_ip(valore: str | None) -> str | None:
    if not valore:
        return None
    try:
        return str(ipaddress.ip_address(valore.strip()))
    except ValueError:
        return None


# Scopo: Estrae lo User-Agent dalla request, troncato a 500 caratteri.
def get_user_agent(request: HttpRequest) -> str | None:
    ua = request.META.get("HTTP_USER_AGENT")
    return ua[:500] if ua else None
