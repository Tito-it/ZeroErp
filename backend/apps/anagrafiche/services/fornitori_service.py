# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione fornitori.
#        Orchestrazione creazione fornitore (ruolo FO + insert)
#        in una transazione atomica. CRUD, lista paginata, update.
#        Pattern semplificato rispetto a clienti (nessuna cascata
#        istanza/BA — il fornitore e' un ruolo diretto).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.anagrafiche.db.fornitori_repository import FornitoriRepository
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE
from apps.anagrafiche.services._validators import create_with_dedup, optional_str
from apps.core.api.payload_validators import optional_bool, optional_int, optional_iso_date, optional_uuid
from apps.core.services.error_manager import ErrorManager


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

    # Scopo: Dettaglio completo di un fornitore.
    def get_fornitore(self, fornitore_id: int) -> dict[str, Any]:
        fornitore = self._repo.get_fornitore(fornitore_id)
        ErrorManager.require(fornitore is not None, code=E_ANAG_NOT_FOUND,
                             message="Fornitore non trovato.")
        assert fornitore is not None
        return fornitore

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
    #        Obiettivo: ottenere ruolo FO per il soggetto e inserire il record fornitore.
    #        Perimetro: validazione soggetto_id, get_or_create ruolo, insert con campi opzionali.
    #        Risultato: dict con id del fornitore e soggetto_ruolo_id.
    def crea_fornitore(self, payload: dict[str, Any]) -> dict[str, Any]:
        soggetto_id = optional_uuid(payload, "soggetto_id")
        ErrorManager.require(soggetto_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="soggetto_id obbligatorio.")
        assert soggetto_id is not None
        soggetto_id = str(soggetto_id)

        # Campi opzionali del fornitore
        fornitore_data = self._extract_fornitore_data(payload)

        with transaction.atomic():
            # Step 1: Ruolo FORNITORE (get or create)
            soggetto_ruolo_id = self._repo.get_or_create_ruolo_fornitore(soggetto_id)

            # Step 2: Insert fornitore (create_with_dedup gestisce IntegrityError)
            result = create_with_dedup(
                lambda: {"id": self._repo.create_fornitore(
                    soggetto_ruolo_id=soggetto_ruolo_id,
                    **fornitore_data,
                )},
                duplicate_message="Esiste gia' un fornitore per questo soggetto.",
            )

        return {
            "id": result["id"],
            "soggetto_ruolo_id": soggetto_ruolo_id,
        }

    # Scopo: Estrae i campi opzionali del fornitore dal payload.
    #        Usa helper condivisi: optional_int, optional_bool, optional_str, optional_iso_date.
    def _extract_fornitore_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}

        # FK int
        for key in ["valuta_id", "modalita_pagamento_id", "termine_pagamento_id",
                     "giorni_pagamento", "rating"]:
            val = optional_int(payload, key)
            if val is not None:
                data[key] = val

        # Boolean — optional_bool ha default=False, qui None nel payload significa
        # "non fornito" e non va incluso nel dict (il DB usa i propri default).
        for key in ["fine_mese", "split_payment", "ritenuta_acconto", "bollo_esente"]:
            if key in payload and payload[key] is not None:
                data[key] = optional_bool(payload, key)

        # Stringhe — usa optional_str da _validators (strip + None se vuoto)
        for key in ["regime_fiscale", "canale_fe", "pec_email", "note"]:
            val = optional_str(payload, key)
            if val is not None:
                data[key] = val

        # Numeric (ritenuta_aliquota puo' essere float/decimal)
        if "ritenuta_aliquota" in payload and payload["ritenuta_aliquota"] is not None:
            data["ritenuta_aliquota"] = payload["ritenuta_aliquota"]

        # Date
        val = optional_iso_date(payload, "qualifica_scadenza")
        if val is not None:
            data["qualifica_scadenza"] = val

        return data
