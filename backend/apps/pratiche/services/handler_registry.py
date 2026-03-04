# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Registry degli handler flusso.
#        Mappa handler_key (dal DB, tabella pratiche.handler_flussi)
#        a classi Python. Il DB contiene le chiavi, Django il mapping.
#        No dynamic import: mapping statico, esplicito e sicuro.
# ------------------------------------------------------------

from typing import Any, Protocol


class BaseFlussoHandler(Protocol):
    """Contratto per handler flusso. Ogni handler implementa execute()."""

    # Scopo: Esegue la logica dell'handler per il flusso indicato.
    def execute(self, flusso_id: int, pratica_id: int, meta: dict[str, Any]) -> dict[str, Any]: ...


# Mapping handler_key → classe Python.
# Da popolare man mano che si implementano gli handler specifici.
HANDLER_MAP: dict[str, type[BaseFlussoHandler]] = {
    # Esempio:
    # "APPUNTAMENTO": AppuntamentoHandler,
    # "SOPRALLUOGO": SopralluogoHandler,
}


# Scopo: Restituisce la classe handler per la chiave indicata, o None se non registrata.
def get_handler(handler_key: str) -> type[BaseFlussoHandler] | None:
    return HANDLER_MAP.get(handler_key)
