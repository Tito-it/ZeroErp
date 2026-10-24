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
    # - flusso_id / pratica_id: identificativi istanza operativa
    # - meta: JSONB del flusso (dati estensibili, specifici dell'istanza)
    # - handler_params: JSONB da template_flussi (configurazione statica del template)
    # - user: utente acting (per audit/p_user delle fn DB); None = CURRENT_USER DB
    def execute(
        self,
        flusso_id: int,
        pratica_id: int,
        meta: dict[str, Any],
        handler_params: dict[str, Any],
        user: str | None = None,
    ) -> dict[str, Any]: ...


# Mapping handler_key → classe Python.
# Popolato a runtime via register_handler() chiamato da AppConfig.ready() del
# dominio chiamante (es. apps/vendite/apps.py), per evitare la dipendenza di
# import pratiche→vendite (l'handler vive in vendite).
# ⛔ RITIRARE un handler: a DB prima i collegamenti in ogni versione del
#    workflow (quelle pubblicate di un emittente si ri-versionano), poi
#    l'handler in `pratiche.handler_flussi`, e SOLO DOPO lo si toglie da qui.
#    Al contrario, un collegamento attivo trova la chiave sparita e il flusso
#    risponde 500 E_HANDLER_NON_REGISTRATO (successo il 2026-10-13 con
#    `vendita.accetta_preventivo`). Presidio: test_handler_registro_coerente_db.
HANDLER_MAP: dict[str, type[BaseFlussoHandler]] = {}


# Scopo: Registra (o sovrascrive) un handler per la chiave indicata.
# Chiamato dai dominii consumatori in AppConfig.ready(). Idempotente.
def register_handler(handler_key: str, handler_class: type[BaseFlussoHandler]) -> None:
    HANDLER_MAP[handler_key] = handler_class


# Scopo: Restituisce la classe handler per la chiave indicata, o None se non registrata.
def get_handler(handler_key: str) -> type[BaseFlussoHandler] | None:
    return HANDLER_MAP.get(handler_key)
