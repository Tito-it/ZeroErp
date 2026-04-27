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
    E_CONTATTO_INCOMPLETO,
)
from apps.anagrafiche.services._validators import create_with_dedup, optional_str
from apps.anagrafiche.services.contatti_service import (
    classify_contatto_payload,
    missing_required_fields,
)
from apps.core.api.payload_validators import optional_bool, optional_int, optional_iso_date, optional_uuid
from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError


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
            result = create_with_dedup(
                lambda: {"id": self._repo.create_fornitore(
                    soggetto_ruolo_id=soggetto_ruolo_id,
                    **fornitore_data,
                )},
                duplicate_message="Esiste gia' un fornitore per questo soggetto.",
            )

            # Step 3: Contatto ruolo (se fornito).
            # Regola unificata via classify_contatto_payload (Fase 5):
            #   EMPTY   → skip (no contatto)
            #   PARTIAL → errore esplicito (sostituisce vecchio silent skip)
            #   VALID   → crea
            contatto_status = classify_contatto_payload(contatto_data)
            if contatto_status == "PARTIAL":
                raise ServiceError(
                    code=E_CONTATTO_INCOMPLETO,
                    message="Contatto incompleto: completa o svuota tutti i campi.",
                    context={"missing": missing_required_fields(contatto_data)},
                )
            if contatto_status == "VALID":
                assert contatto_data is not None
                self._sogg_repo.crea_contatto(
                    soggetto_id,
                    nominativo=contatto_data["nominativo"],
                    email=optional_str(contatto_data, "email"),
                    telefono=optional_str(contatto_data, "telefono"),
                    cellulare=optional_str(contatto_data, "cellulare"),
                    pec=optional_str(contatto_data, "pec"),
                    tipo_contatto_id=optional_int(contatto_data, "tipo_contatto_id"),
                    note=optional_str(contatto_data, "note"),
                    soggetto_ruolo_id=soggetto_ruolo_id,
                )

            # Step 4: Indirizzi ruolo (se forniti — obbligatori per trigger DEFERRED)
            #         Il frontend manda tipo_indirizzo_codice + stradario/libero.
            #         Risolviamo codice→id e stradario→indirizzo_dettaglio_id.
            self._create_indirizzi_ruolo(soggetto_ruolo_id, indirizzi_data)

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
        # codice: incluso solo se fornito (altrimenti il DB lo genera se sistema_codici configurato)
        for key in ["codice", "regime_fiscale", "canale_fe", "pec_email", "note"]:
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

    # Scopo: Crea indirizzi a livello ruolo dal payload frontend.
    #        Risolve tipo_indirizzo_codice → tipo_indirizzo_id.
    #        Per indirizzi normalizzati, risolve stradario → indirizzo_dettaglio_id
    #        tramite SoggettiService (riuso logica esistente, zero duplicazione).
    #        Auto-clone: se un solo indirizzo e la matrice ha piu tipi obbligatori,
    #        clona l'indirizzo per i tipi mancanti (stesso pattern di SoggettoDrawer).
    #        Skip duplicati: se il soggetto_ruolo ha gia' indirizzi con lo stesso
    #        tipo_indirizzo_id, li salta (es. secondo cliente su ruolo CL esistente).
    def _create_indirizzi_ruolo(
        self, soggetto_ruolo_id: int, indirizzi_data: list[dict[str, Any]],
        tipo_ruolo_codice: str = "FO",
    ) -> None:
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        from apps.core.db.lookup_repository import LookupRepository
        sogg_svc = SoggettiService()

        if not indirizzi_data:
            return

        # Tipi indirizzo gia' presenti sul ruolo (skip duplicati)
        existing_tipo_ids = self._sogg_repo.get_existing_tipo_indirizzo_ids(soggetto_ruolo_id)

        # Auto-clone: clona il primo indirizzo per i tipi obbligatori mancanti
        matrice = LookupRepository().list_matrice_indirizzi_ruolo(tipo_ruolo_codice)
        tipi_presenti = {ind.get("tipo_indirizzo_codice") for ind in indirizzi_data if isinstance(ind, dict)}
        primo = indirizzi_data[0]
        for m in matrice:
            if m["obbligatorio"] and m["codice"] not in tipi_presenti:
                indirizzi_data.append({**primo, "tipo_indirizzo_codice": m["codice"]})

        # Risolvi e crea ogni indirizzo
        resolved_det_id: int | None = None
        for ind in indirizzi_data:
            if not isinstance(ind, dict):
                continue

            # Risolvi tipo: codice → id
            tipo_indirizzo_id = optional_int(ind, "tipo_indirizzo_id")
            if tipo_indirizzo_id is None:
                tipo_codice = optional_str(ind, "tipo_indirizzo_codice")
                if tipo_codice:
                    tipo_indirizzo_id = self._sogg_repo.resolve_tipo_indirizzo_id(tipo_codice)
            if tipo_indirizzo_id is None:
                ErrorManager.require(False, code=E_ANAG_VALIDAZIONE,
                                     message="Tipo indirizzo non risolto per indirizzo inline.")

            # Risolvi indirizzo: libero o normalizzato (stradario → dettaglio)
            indirizzo_libero = optional_str(ind, "indirizzo_libero")
            indirizzo_dettaglio_id = None
            if not indirizzo_libero:
                det_from_payload = optional_int(ind, "indirizzo_dettaglio_id")
                if det_from_payload:
                    indirizzo_dettaglio_id = det_from_payload
                elif resolved_det_id:
                    # Clone: riusa dettaglio gia risolto (stesso stradario+civico)
                    indirizzo_dettaglio_id = resolved_det_id
                else:
                    indirizzo_dettaglio_id = sogg_svc._resolve_indirizzo_dettaglio(ind)
                # Cache il primo dettaglio risolto per i cloni successivi
                if resolved_det_id is None and indirizzo_dettaglio_id:
                    resolved_det_id = indirizzo_dettaglio_id

            # Skip se il tipo indirizzo esiste gia' sul ruolo
            # (es. secondo cliente creato sullo stesso soggetto_ruolo CL)
            if tipo_indirizzo_id in existing_tipo_ids:
                continue

            self._sogg_repo.crea_indirizzo_ruolo(
                soggetto_ruolo_id,
                tipo_indirizzo_id=tipo_indirizzo_id,
                indirizzo_dettaglio_id=indirizzo_dettaglio_id,
                indirizzo_libero=indirizzo_libero,
                stato_id=optional_int(ind, "stato_id"),
                comune_id=optional_int(ind, "comune_id"),
                codice_postale_id=optional_int(ind, "codice_postale_id"),
            )
            # Aggiorna set per evitare duplicati nell'auto-clone
            existing_tipo_ids.add(tipo_indirizzo_id)
