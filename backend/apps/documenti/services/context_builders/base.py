# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Interfaccia DocumentContextBuilder. Le implementazioni
#        concrete vivono nei domini sorgente (es.
#        apps.vendite.services.preventivo_document_context_builder).
#        Il render service riceve `context_code + sorgente_id`, risolve
#        il builder via registry e invoca build_context() per ottenere
#        il dizionario passato al template engine (WeasyPrint v1).
# ------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DocumentContextBuilder(ABC):
    """
    Builder di contesto per la generazione di un documento da una sorgente.

    Contratto:
    - `CODE` (class var): chiave whitelisted, deve combaciare 1:1 con
      `documenti.template_documenti.context_builder_code`. Il render
      service usa questa chiave per il dispatch.
    - `build_context(sorgente_id, *, auth_user_id, locale)` ritorna un dict
      JSON-serializable usato dal template engine. Il builder NON conosce
      il template HTML: si limita a fornire i dati. La logica di template
      vive lato `render_service`.
    - le implementazioni leggono dati dai propri repository di dominio,
      non da quelli `documenti`.
    """

    CODE: str = ""

    @abstractmethod
    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        """
        Ritorna il dizionario di contesto per la sorgente identificata da
        `sorgente_id`. Solleva ServiceError(E_DOCUMENTI_NOT_FOUND) se la
        sorgente non esiste o e' fuori scope per l'utente.
        """
