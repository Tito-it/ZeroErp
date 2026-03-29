# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Throttling DRF per endpoint search/lista, login e reset password.
# ------------------------------------------------------------
from __future__ import annotations

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

# Throttling DRF: limita endpoint sensibili.


class _CustomRateAnonThrottle(AnonRateThrottle):
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


class PasswordResetRateThrottle(_CustomRateAnonThrottle):
    """Limita richieste reset password per IP: 3 ogni 15 minuti."""
    scope = "password_reset"
    rate = "3/15m"


class SearchBurstRateThrottle(SimpleRateThrottle):
    scope = "search_burst"

    # Scopo: Recupera `cache_key` dal contesto applicativo o dal database.
    def get_cache_key(self, request, view):
        if not getattr(view, "is_search_endpoint", False):
            return None
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
