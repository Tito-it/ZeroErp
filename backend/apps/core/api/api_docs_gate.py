# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Cancello request-time per le rotte di documentazione API
#        (`/api/schema/`, `/api/docs/`): esistono solo se
#        `settings.API_DOCS_ENABLED` e' vero, altrimenti 404.
# Note: il controllo e' a richiesta e non a import, cosi' i test lo
#       provano con `override_settings` senza ricaricare gli URL.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse


# Scopo: Avvolge una view e la fa sparire (404) quando la documentazione API e'
#        spenta. 404 e non 403: una rotta spenta non deve nemmeno confermare di
#        esistere a chi non ha un token.
def solo_se_api_docs_abilitate(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @wraps(view)
    def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not getattr(settings, "API_DOCS_ENABLED", False):
            raise Http404
        return view(request, *args, **kwargs)

    return _wrapped
