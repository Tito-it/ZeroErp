# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Throttling DRF per endpoint search/lista, login e reset password.
# ------------------------------------------------------------
from __future__ import annotations

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from apps.core.services.request_context import get_client_ip

# Throttling DRF: limita endpoint sensibili.

# Chiave comune delle richieste di cui l'IP non si ricava: condividono UN
# contatore (fail-closed), invece di sfuggire al limite.
_IDENT_IP_SCONOSCIUTO = "ip-sconosciuto"


class _ClientIpIdentMixin:
    """L'IP del throttle viene dal BB `get_client_ip`, non da DRF.

    ⛔ `SimpleRateThrottle.get_ident` di DRF legge `X-Forwarded-For` per conto
    suo (con `NUM_PROXIES` non impostato usa l'header INTERO, scritto dal
    client): chi cambia l'header a ogni richiesta avrebbe un contatore nuovo
    ogni volta. La regola dell'hop fidato sta in un solo posto.
    """

    # Scopo: Identifica il chiamante con l'IP fidato del BB `get_client_ip`.
    def get_ident(self, request):
        return get_client_ip(request) or _IDENT_IP_SCONOSCIUTO


class _CustomRateAnonThrottle(_ClientIpIdentMixin, AnonRateThrottle):
    """Base con parsing rate custom (supporta minuti "Nm" e ore "Nh")."""

    # Scopo: Parsing custom per rate con minuti/ore (es. "5/5m", "3/1h").
    # DRF supporta solo second/minute/hour/day. Qui convertiamo "Nm"/"Nh" in secondi.
    def parse_rate(self, rate):
        if rate is None:
            return (None, None)
        num_requests, duration = rate.split("/")
        num_requests = int(num_requests)
        if duration.endswith("m"):
            period = int(duration[:-1]) * 60
        elif duration.endswith("h"):
            period = int(duration[:-1]) * 3600
        else:
            return super().parse_rate(rate)
        return (num_requests, period)


class LoginRateThrottle(_CustomRateAnonThrottle):
    """Limita tentativi login per IP: 5 ogni 5 minuti."""
    scope = "login"
    rate = "5/5m"


class SecondoFattoreRateThrottle(_CustomRateAnonThrottle):
    """Limita il SECONDO PASSO del login per IP: 5 ogni 5 minuti.

    ⭐ Contatore proprio, non quello del login (fino al 2026-10-02 era lo
    stesso): col secondo fattore ogni accesso costa due richieste, e un
    contatore condiviso dimezzava i login possibili da un IP — dietro un
    ufficio con un solo indirizzo, due o tre persone insieme ricevevano 429
    (collaudo di Tid: lo smoke col secondo login fermato al secondo passo).
    Chi prova codici a raffica resta frenato tre volte: da questo limite, dal
    freno della credenziale a DB (ogni codice sbagliato e' un tentativo fallito,
    D-T2) e dalla sfida, che scade in 5 minuti. Lo stesso ritmo del login per
    scelta, non per copia: i due limiti possono divergere.
    """
    scope = "login_secondo_fattore"
    rate = "5/5m"


class PasswordResetRateThrottle(_CustomRateAnonThrottle):
    """Limita richieste reset password per IP: 3 ogni 15 minuti."""
    scope = "password_reset"
    rate = "3/15m"


class SearchBurstRateThrottle(_ClientIpIdentMixin, SimpleRateThrottle):
    scope = "search_burst"

    # Scopo: Recupera `cache_key` dal contesto applicativo o dal database.
    def get_cache_key(self, request, view):
        if not getattr(view, "is_search_endpoint", False):
            return None
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
