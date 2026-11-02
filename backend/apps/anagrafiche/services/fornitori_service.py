# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione fornitori.
#        Creazione (ruolo FO + fornitore + contatto + indirizzi) dalla madre del
#        DB `anagrafiche.fn_crea_fornitore`. CRUD, lista paginata, update.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.anagrafiche.db.fornitori_repository import (
    FORNITORE_UPDATE_ALLOWED,
    FornitoriRepository,
)
from apps.anagrafiche.error_codes import (
    E_ANAG_NOT_FOUND,
    E_ANAG_VALIDAZIONE,
)
from apps.anagrafiche.services._validators import (
    create_with_constraint_mapping,
    extract_optional_fields,
    require_found,
)
from apps.anagrafiche.services.contatti_service import VINCOLI_CONTATTO, contatto_inline_per_madre
from apps.anagrafiche.services.soggetti_service import indirizzi_per_madre
from apps.core.api.payload_validators import optional_uuid
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator


# Contratto della PATCH, validato QUI con 400 `E_ANAG_VALIDAZIONE` (2026-09-26):
# dal passaggio al BB `execute_dynamic_update` il repository rifiuta con
# `RuntimeError` (500) ogni colonna fuori whitelist — fino a quel giorno la
# scartava in silenzio. Parte dalle colonne scrivibili del repository.
_UPDATE_FORNITORE_KEYS: frozenset[str] = FORNITORE_UPDATE_ALLOWED

# Validator stateless del dominio (solo il codice errore): condivisibile.
_V = PayloadValidator(validation_code=E_ANAG_VALIDAZIONE)


class FornitoriService:
    """Service per gestione fornitori completa."""

    def __init__(self) -> None:
        self._repo = FornitoriRepository()

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata fornitori.
    def list_fornitori(self, **params: Any) -> tuple[list, int]:
        return self._repo.list_fornitori(**params)

    # Scopo: Risolve i filtri attivi della lista fornitori in dict
    #        {label_italiano: descrizione_leggibile} per l'header
    #        dell'export DEF-1. Stesso pattern di
    #        `ClientiService.resolve_filtri_export_label` /
    #        `SoggettiService.resolve_filtri_export_label`: sostituisce il
    #        dump JSON opaco ("stato_fornitore_id: 3") con etichette
    #        comprensibili ("Stato: Attivo").
    #
    #        Fallback: se il lookup non trova match (id obsoleto), usa
    #        "id=N" per non perdere informazione.
    def resolve_filtri_export_label(
        self,
        *,
        stato_fornitore_id: int | None = None,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if stato_fornitore_id is not None:
            desc = self._repo.get_stato_fornitore_descrizione(
                stato_fornitore_id,
            )
            out["Stato"] = desc or f"id={stato_fornitore_id}"
        return out

    # Scopo: Dettaglio completo di un fornitore.
    def get_fornitore(self, fornitore_id: int) -> dict[str, Any]:
        return require_found(self._repo.get_fornitore(fornitore_id), "Fornitore non trovato.")

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Scopo: Aggiorna campi editabili di un fornitore (pagamento, fiscale, FE, rating, note).
    def update_fornitore(self, fornitore_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=_UPDATE_FORNITORE_KEYS, message="Payload fornitore non valido.",
        )
        # Verifica che il fornitore esista
        self.get_fornitore(fornitore_id)
        # Un PATCH vuoto e' un 400, non il 404 che dava il rowcount (2026-10-14).
        _V.require_campi_da_aggiornare(payload)
        updated = self._repo.update_fornitore(fornitore_id, payload)
        ErrorManager.require(updated, code=E_ANAG_NOT_FOUND, message="Fornitore non trovato.")
        return {"updated": True}

    # =================================================================
    # Creazione fornitore
    # =================================================================

    # Scopo: Crea un fornitore completo: ruolo FO, fornitore nello stato VE,
    #        contatto del ruolo (opzionale) e indirizzi del ruolo, con la madre
    #        del DB `anagrafiche.fn_crea_fornitore` (un'istruzione: atomica, e i
    #        trigger DEFERRED degli indirizzi obbligatori trovano tutto).
    #        Qui restano i pre-check per l'operatore: il soggetto, i campi del
    #        payload, la classificazione del contatto inline (EMPTY/PARTIAL/
    #        VALID: decide SE c'e' un contatto) e gli indirizzi; poi la
    #        traduzione dei vincoli per nome.
    #        Risultato: dict con id del fornitore e soggetto_ruolo_id.
    # ⭐ Dal 2026-10-18 (2b-2, lotto 4): fino ad allora i quattro passi stavano
    #    qui dentro un `transaction.atomic`.
    def crea_fornitore(self, payload: dict[str, Any]) -> dict[str, Any]:
        soggetto_id = optional_uuid(payload, "soggetto_id")
        ErrorManager.require(soggetto_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="soggetto_id obbligatorio.")
        assert soggetto_id is not None

        fornitore_data = self._extract_fornitore_data(payload)
        contatto = contatto_inline_per_madre(payload.get("contatto"))
        indirizzi = indirizzi_per_madre(payload.get("indirizzi"))

        fornitore_id, soggetto_ruolo_id = create_with_constraint_mapping(
            lambda: self._repo.crea_fornitore(str(soggetto_id), fornitore_data, contatto, indirizzi),
            {
                "uq_fornitori_soggetto_ruolo_id": "Esiste gia' un fornitore per questo soggetto.",
                "uq_fornitori_codice": (
                    "Esiste gia' un fornitore con questo codice.",
                    "codice",
                ),
                **VINCOLI_CONTATTO,
            },
        )
        return {
            "id": fornitore_id,
            "soggetto_ruolo_id": soggetto_ruolo_id,
        }

    # Scopo: Estrae i campi opzionali del fornitore dal payload via extract_optional_fields.
    def _extract_fornitore_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        # codice incluso solo se fornito (altrimenti il DB lo genera se
        # sistema_codici configurato); i bool a None = "non fornito" → default DB.
        return extract_optional_fields(
            payload,
            ints=("valuta_id", "modalita_pagamento_id", "termine_pagamento_id",
                  "giorni_pagamento", "rating"),
            bools=("fine_mese", "split_payment", "ritenuta_acconto", "bollo_esente"),
            strings=("codice", "regime_fiscale", "canale_fe", "pec_email", "note"),
            numeric=("ritenuta_aliquota",),
            dates=("qualifica_scadenza",),
        )
