# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condiviso per le `_resolve_contesto_<sorgente>` delle view
#        documentali "per sorgente" (offerta, preventivo, contratto, ...).
#        Centralizza le 3 guard ricorrenti — entity esiste, emittente
#        fiscale risolto, sorgente_tipo attivo — che prima erano duplicate
#        in ogni `<sorgente>_documenti_views.py`. La differenza per dominio
#        e' solo nel repo che fetcha l'entity e nei messaggi i18n-aware:
#        l'helper accetta entity gia' fetchata + i messaggi gia' formulati.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.config.db.sorgenti_repository import SorgentiRepository
from apps.core.services.error_manager import ErrorManager

# Codici errore allineati alla convenzione delle view documentali.
_E_VALIDATION = "E_DOCUMENTI_VALIDATION"
_E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


# Scopo: Risolve il contesto comune per le view documentali "per sorgente":
#        valida che l'entity esista, che abbia un emittente fiscale, e
#        risolve il sorgente_tipo_id dal codice. Ritorna `(entity_dict,
#        sorgente_tipo_id)`. Fail-fast con messaggi parlanti su tutti i
#        rami: 404 (entity not found), validazione (emittente mancante o
#        sorgente non attiva).
#
#        Caller pattern:
#            def _resolve_contesto_<x>(x_id):
#                entity = XRepository().get_for_documento_generation(x_id)
#                return resolve_contesto_documentale(
#                    entity=entity, entity_id=x_id,
#                    not_found_message="<X> non trovat<o/a>.",
#                    emittente_message="Emittente fiscale non risolto per <l'x/il x>.",
#                    sorgente_codice="<CODICE>",
#                )
def resolve_contesto_documentale(
    *,
    entity: dict[str, Any] | None,
    entity_id: int,
    not_found_message: str,
    emittente_message: str,
    sorgente_codice: str,
) -> tuple[dict[str, Any], int]:
    ErrorManager.require(
        entity is not None,
        code=_E_NOT_FOUND,
        message=not_found_message,
        detail=f"entity_id={entity_id}",
    )
    assert entity is not None
    ErrorManager.require(
        entity.get("emittente_fiscale_id") is not None,
        code=_E_VALIDATION,
        message=emittente_message,
        detail=f"entity_id={entity_id}",
    )
    sorgente = SorgentiRepository().get_sorgente_attiva(sorgente_codice)
    ErrorManager.require(
        sorgente is not None,
        code=_E_VALIDATION,
        message=f"Sorgente '{sorgente_codice}' non configurata o non attiva.",
    )
    assert sorgente is not None
    return entity, int(sorgente["id"])
