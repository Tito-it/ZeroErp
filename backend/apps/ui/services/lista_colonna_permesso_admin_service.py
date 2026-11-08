# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per `ui.lista_colonna_permesso` (Blocco F Fase 1).
#        Espone UPSERT su (colonna_id, profilo_accesso_id) con livello
#        TUTTO/LETTURA/BLOCCATO + DELETE puntuale + lista per lista_id.
#
#        Non c'e' UPDATE separato dal CREATE: la chiave UNIQUE
#        (colonna_id, profilo_accesso_id) garantisce 1 sola riga per
#        coppia, quindi POST e' UPSERT idempotente.
#
#        I CHECK lato DB sono soft (FK + UNIQUE). La validazione del
#        livello_accesso e' enum (config.livello_accesso).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import IntegrityError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)
from apps.ui.db.ui_admin_repository import UiAdminRepository

E_PERMESSO_VALIDATION = "E_UI_PERMESSO_VALIDAZIONE"
E_PERMESSO_NOT_FOUND = "E_UI_PERMESSO_NON_TROVATO"
E_LISTA_NOT_FOUND = "E_UI_LISTA_NON_TROVATA"

# DRIFT RISK: allineato all'enum DB `config.livello_accesso`
# (3 valori fissi nel modello permessi v2). La duplicazione qui filtra
# presto con errore parlante; il DB e' la guard finale.
_LIVELLI_AMMESSI: frozenset[str] = frozenset({"TUTTO", "LETTURA", "BLOCCATO"})

_UPSERT_KEYS: frozenset[str] = frozenset(
    {"colonna_id", "profilo_accesso_id", "livello_accesso"}
)

_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    # Anche se il flusso e' UPSERT, lasciamo il mapping per resilienza
    # in caso di race / direct-INSERT da test.
    "uq_ui_lista_colonna_permesso_col_profilo": (
        E_PERMESSO_VALIDATION,
        "Esiste gia' un permesso colonna per questa coppia (colonna, profilo).",
    ),
}

_FK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "fk_lista_colonna_permesso_lista_colonna": (
        E_PERMESSO_VALIDATION,
        "colonna_id non valido (FK su ui.lista_colonna).",
    ),
    "fk_lista_colonna_permesso_profili_accesso": (
        E_PERMESSO_VALIDATION,
        "profilo_accesso_id non valido (FK su config.profili_accesso).",
    ),
}


class ListaColonnaPermessoAdminService:
    """Facade scrittura permessi colonna (Blocco F admin)."""

    def __init__(self, repo: UiAdminRepository | None = None) -> None:
        self._repo = repo or UiAdminRepository()
        self._v = PayloadValidator(validation_code=E_PERMESSO_VALIDATION)

    # =================================================================
    # Read
    # =================================================================

    # Scopo: Lista permessi colonna per una lista_id, con join arricchiti
    #        per il display fields (codice colonna, profilo). 404 se la
    #        lista non esiste o non e' attiva.
    # ⭐ Forma `{results, count}` — vedi la nota su `list_colonne_admin`:
    #    conteggio da query SUA, mai `len(results)`.
    def list_permessi(self, lista_id: int) -> dict[str, Any]:
        ErrorManager.require(
            self._repo.get_definizione(lista_id) is not None,
            code=E_LISTA_NOT_FOUND,
            message="Lista non trovata.",
            detail=f"lista_id={lista_id}",
        )
        return {
            "results": self._repo.list_permessi_by_lista(lista_id),
            "count": self._repo.count_permessi_by_lista(lista_id),
        }

    # =================================================================
    # Upsert / Delete
    # =================================================================

    # Scopo: UPSERT permesso. Valida payload, esegue ON CONFLICT DO UPDATE
    #        e ritorna l'id risultante (nuovo o aggiornato).
    def upsert_permesso(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.validate_allowed_keys(
            payload,
            allowed=_UPSERT_KEYS,
            message="Payload permesso colonna non valido.",
        )
        colonna_id = self._v.require_positive_int(payload, "colonna_id")
        profilo_id = self._v.require_positive_int(payload, "profilo_accesso_id")
        livello = self._v.require_string(payload, "livello_accesso")
        ErrorManager.require(
            livello in _LIVELLI_AMMESSI,
            code=E_PERMESSO_VALIDATION,
            message="Livello accesso non valido.",
            detail=f"livello='{livello}', ammessi={sorted(_LIVELLI_AMMESSI)!r}",
        )

        try:
            permesso_id = self._repo.upsert_permesso(
                colonna_id=colonna_id,
                profilo_accesso_id=profilo_id,
                livello_accesso=livello,
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_PERMESSO_VALIDATION,
                fallback_message="Violazione vincolo DB su permesso colonna.",
                context={
                    "colonna_id": colonna_id,
                    "profilo_accesso_id": profilo_id,
                },
            )
        return {
            "id": permesso_id,
            "colonna_id": colonna_id,
            "profilo_accesso_id": profilo_id,
            "livello_accesso": livello,
        }

    # Scopo: Cancella permesso per id. Idempotente verso il caller in
    #        senso forte: 404 esplicito se non esisteva, perche' un FE
    #        che chiama DELETE su id immaginario merita feedback netto.
    def delete_permesso(self, permesso_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(permesso_id, field="permesso_id")
        deleted = self._repo.delete_permesso(permesso_id)
        ErrorManager.require(
            deleted,
            code=E_PERMESSO_NOT_FOUND,
            message="Permesso colonna non trovato.",
            detail=f"permesso_id={permesso_id}",
        )
        return {"deleted": True, "id": permesso_id}

