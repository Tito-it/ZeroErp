# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin read-only per `ui.lista_definizione`. Espone:
#          - list_definizioni()        — lista per Select header
#                                         "Lista corrente"
#          - list_colonne_lista(id)    — catalogo colonne (Fase 1, helper
#                                         per la composizione preset; non
#                                         filtra per permessi: e' admin)
#
#        I CRUD su lista_definizione/lista_colonna sono Fase 2 (gestione
#        SUPER_ADMIN tramite tab tecnici): per la Fase 1 restano gestiti
#        via seed CSV.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.ui.db.ui_admin_repository import UiAdminRepository

E_LISTA_NOT_FOUND = "E_UI_LISTA_NON_TROVATA"


class ListaDefinizioneAdminService:
    """Facade lettura definizione lista + catalogo colonne (admin)."""

    def __init__(self, repo: UiAdminRepository | None = None) -> None:
        self._repo = repo or UiAdminRepository()

    # Scopo: Lista delle definizioni di lista attive. Pre-popola il
    #        Select "Lista corrente" della pagina admin.
    def list_definizioni(self) -> list[dict[str, Any]]:
        return self._repo.list_definizioni()

    # Scopo: Catalogo colonne grezzo di una lista (no filtro permessi:
    #        amministrazione tecnica). 404 se la lista non esiste o non
    #        e' attiva.
    def list_colonne_lista(self, lista_id: int) -> list[dict[str, Any]]:
        ErrorManager.require(
            self._repo.get_definizione(lista_id) is not None,
            code=E_LISTA_NOT_FOUND,
            message="Lista non trovata.",
            detail=f"lista_id={lista_id}",
        )
        return self._repo.list_colonne_by_lista(lista_id)
