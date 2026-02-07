# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Throttling DRF per endpoint search/lista.
# ------------------------------------------------------------
from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle

# Throttling DRF: limita endpoint search/lista sensibili.


class SearchBurstRateThrottle(SimpleRateThrottle):
    scope = "search_burst"

    def get_cache_key(self, request, view):
        if not getattr(view, "is_search_endpoint", False):
            return None
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
