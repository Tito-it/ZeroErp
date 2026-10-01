# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

from django.conf import settings
from django.http import HttpRequest


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
