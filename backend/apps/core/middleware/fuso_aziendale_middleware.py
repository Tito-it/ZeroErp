# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Attiva il fuso dell'azienda (BB `core/services/fuso_aziendale`) per
#        ogni richiesta, e lo disattiva alla fine. Cosi' cio' che Django
#        converte da se' — template, filtro `|date`, `DateTimeField` di DRF —
#        parla nel fuso dell'azienda e non in `settings.TIME_ZONE` ('UTC').
#
#        ⚠️ Non e' la condizione perche' i BB rispondano giusto: `oggi_aziendale`
#        e `in_ora_locale` dichiarano il fuso da se'. Il middleware copre il resto.
#        ⛔ Nessun ripiego: se il fuso non si legge (parametro assente, DB giu')
#        la richiesta fallisce, come il resto del backend senza DB.
#        ⭐ Tranne i PERCORSI TECNICI (BB `core/services/percorsi_tecnici`):
#        fuori dal dominio, non leggono il fuso. Fino al 2026-11-01 anche
#        `/health` lo leggeva, e la sonda di vita del processo rispondeva 500
#        col DB irraggiungibile: lo smoke del container in CI era rosso dal
#        24-10.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from apps.core.services.fuso_aziendale import attiva_fuso_aziendale
from apps.core.services.percorsi_tecnici import e_percorso_tecnico


class FusoAziendaleMiddleware:
    """Attiva il fuso dell'azienda per la durata della richiesta."""

    # Scopo: Costruttore standard dei middleware Django.
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    # Scopo: Attiva il fuso, serve la richiesta, disattiva comunque: il thread
    #        di un worker serve richieste successive e non deve portarsi dietro
    #        lo stato.
    def __call__(self, request: HttpRequest) -> HttpResponse:
        if e_percorso_tecnico(request.path):
            return self.get_response(request)
        attiva_fuso_aziendale()
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
