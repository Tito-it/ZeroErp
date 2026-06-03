# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione fornitori.
#        Orchestrazione creazione fornitore (ruolo FO + contatto + indirizzo + insert)
#        in una transazione atomica. CRUD, lista paginata, update.
#        In creazione, contatto e indirizzo vengono inseriti nella stessa transazione
#        per soddisfare i trigger DEFERRED (indirizzi obbligatori per ruolo FO).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.anagrafiche.db.fornitori_repository import FornitoriRepository
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.error_codes import (
    E_ANAG_NOT_FOUND,
    E_ANAG_VALIDAZIONE,
)
from apps.anagrafiche.services._validators import (
    create_with_constraint_mapping,
    extract_optional_fields,
    require_found,
)
from apps.anagrafiche.services.contatti_service import crea_contatto_inline_se_valido
from apps.core.api.payload_validators import optional_uuid
from apps.core.services.error_manager import ErrorManager


class FornitoriService:
    """Service per gestione fornitori completa."""

    def __init__(self) -> None:
        self._repo = FornitoriRepository()
        self._sogg_repo = SoggettiRepository()

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
        search: str | None = None,
        stato_fornitore_id: int | None = None,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if search:
            out["Ricerca"] = search
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
        # Verifica che il fornitore esista
        self.get_fornitore(fornitore_id)
        updated = self._repo.update_fornitore(fornitore_id, payload)
        ErrorManager.require(updated, code=E_ANAG_NOT_FOUND,
                             message="Fornitore non trovato o nessun campo modificato.")
        return {"updated": True}

    # =================================================================
    # Creazione fornitore
    # =================================================================

    # Scopo: Crea un fornitore completo in una transazione atomica.
    #        Obiettivo: ruolo FO + fornitore + contatto (opzionale) + indirizzo ruolo (opzionale).
    #        Perimetro: validazione soggetto_id, get_or_create ruolo, insert fornitore,
    #        insert contatto e indirizzo nella stessa transazione per soddisfare
    #        trigger DEFERRED (indirizzi obbligatori per ruolo FO).
    #        Risultato: dict con id del fornitore e soggetto_ruolo_id.
    def crea_fornitore(self, payload: dict[str, Any]) -> dict[str, Any]:
        soggetto_id = optional_uuid(payload, "soggetto_id")
        ErrorManager.require(soggetto_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="soggetto_id obbligatorio.")
        assert soggetto_id is not None
        soggetto_id = str(soggetto_id)

        # Campi opzionali del fornitore
        fornitore_data = self._extract_fornitore_data(payload)

        # Contatto e indirizzi inline (opzionali, per creazione da drawer)
        contatto_data = payload.get("contatto")
        indirizzi_data = payload.get("indirizzi", [])

        with transaction.atomic():
            # Step 1: Ruolo FORNITORE (get or create)
            soggetto_ruolo_id = self._repo.get_or_create_ruolo_fornitore(soggetto_id)

            # Step 2: Insert fornitore
            result = create_with_constraint_mapping(
                lambda: {"id": self._repo.create_fornitore(
                    soggetto_ruolo_id=soggetto_ruolo_id,
                    **fornitore_data,
                )},
                {
                    "uq_fornitori_soggetto_ruolo_id": "Esiste gia' un fornitore per questo soggetto.",
                    "uq_fornitori_codice": "Esiste gia' un fornitore con questo codice.",
                },
            )

            # Step 3: Contatto ruolo inline opzionale (EMPTY→skip, PARTIAL→errore, VALID→crea).
            crea_contatto_inline_se_valido(
                self._sogg_repo, soggetto_id, soggetto_ruolo_id, contatto_data)

            # Step 4: Indirizzi ruolo (se forniti — obbligatori per trigger DEFERRED).
            #         Operazione di dominio soggetto_ruolo: delega a SoggettiService.
            from apps.anagrafiche.services.soggetti_service import SoggettiService
            SoggettiService().create_indirizzi_ruolo(soggetto_ruolo_id, indirizzi_data, tipo_ruolo_codice="FO")

        return {
            "id": result["id"],
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

    # Indirizzi a livello ruolo: spostato in SoggettiService.create_indirizzi_ruolo
    # (operazione di dominio soggetto_ruolo). crea_fornitore vi delega.
