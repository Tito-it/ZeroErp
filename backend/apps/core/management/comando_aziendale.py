# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La classe base dei management command del progetto. Attiva il fuso
#        dell'azienda (BB `core/services/fuso_aziendale`) prima di `handle`, come
#        `FusoAziendaleMiddleware` fa per una richiesta: un comando lanciato da
#        un timer systemd o da un worker ragiona nel fuso dell'azienda, non in
#        quello del processo ('UTC') ne' dell'host.
#
#        ⛔ Ogni comando in `apps/*/management/commands/` eredita da qui.
#        Presidio: `apps/core/tests/test_comandi_fuso_aziendale.py`.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.services.fuso_aziendale import attiva_fuso_aziendale


class ComandoAziendale(BaseCommand):
    """`BaseCommand` che gira nel fuso dell'azienda."""

    # Scopo: Attiva il fuso dell'azienda attorno all'esecuzione del comando, e
    #        lo disattiva alla fine (anche su errore). `execute` e' il punto
    #        che `call_command` e `manage.py` attraversano entrambi.
    def execute(self, *args: Any, **options: Any) -> str | None:
        attiva_fuso_aziendale()
        try:
            return super().execute(*args, **options)
        finally:
            timezone.deactivate()
