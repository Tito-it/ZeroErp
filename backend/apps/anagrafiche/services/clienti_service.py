# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione clienti.
#        Orchestrazione creazione cliente (istanza + BA + cliente)
#        in una transazione atomica. Riusabile sia dalla creazione
#        manuale (fuori pratica) sia dal motore pratiche.
#        Ref: docs/it/dev/work-in-progress/sviluppo-gestione-clienti.md
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction

from apps.anagrafiche.db.clienti_repository import ClientiRepository
from apps.anagrafiche.error_codes import E_ANAG_DUPLICATO, E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE
from apps.anagrafiche.services._validators import optional_str
from apps.core.services.service_errors import ServiceError
from apps.core.api.payload_validators import optional_int, optional_uuid
from apps.core.services.error_manager import ErrorManager


class ClientiService:
    """Service per gestione clienti completa.

    Il metodo crea_cliente() e' riusabile:
    - Creazione manuale: istanza_utility_id e billing_account_id sono NULL,
      vengono generati in trasparenza.
    - Da pratiche: istanza_utility_id e/o billing_account_id pre-esistenti,
      vengono validati e riusati.
    """

    def __init__(self) -> None:
        self._repo = ClientiRepository()

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata clienti.
    def list_clienti(self, **params: Any) -> tuple[list, int]:
        return self._repo.list_clienti(**params)

    # Scopo: Lista utility ammesse per creazione manuale.
    def list_utilities_manuali(self) -> list[dict[str, Any]]:
        return self._repo.list_utilities_manuali()

    # Scopo: Dettaglio completo di un cliente.
    def get_cliente(self, cliente_id: int) -> dict[str, Any]:
        cliente = self._repo.get_cliente(cliente_id)
        ErrorManager.require(cliente is not None, code=E_ANAG_NOT_FOUND,
                             message="Cliente non trovato.")
        assert cliente is not None
        return cliente

    # =================================================================
    # Creazione cliente (orchestratore riusabile)
    # =================================================================

    # Scopo: Crea un cliente completo in una transazione atomica.
    #        Obiettivo: generare la catena istanza → BA → cliente.
    #        Perimetro: se istanza_utility_id/billing_account_id forniti,
    #        li valida e riusa; se NULL, li genera in trasparenza.
    #        Risultato: dict con id del cliente creato e delle entita' collegate.
    def crea_cliente(self, payload: dict[str, Any]) -> dict[str, Any]:
        soggetto_id = optional_uuid(payload, "soggetto_id")
        ErrorManager.require(soggetto_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="soggetto_id obbligatorio.")
        assert soggetto_id is not None
        soggetto_id = str(soggetto_id)

        utility_id = optional_int(payload, "utility_id")
        ErrorManager.require(utility_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="utility_id obbligatorio.")
        assert utility_id is not None

        # Parametri opzionali: entita' pre-esistenti (da pratiche)
        istanza_utility_id = optional_int(payload, "istanza_utility_id")
        billing_account_id = optional_int(payload, "billing_account_id")

        # Parametri opzionali
        indirizzo_dettaglio_id = optional_int(payload, "indirizzo_dettaglio_id")
        ba_fatturazione_ordini = optional_str(payload, "ba_fatturazione_ordini")
        ba_parent_account_id = optional_int(payload, "ba_parent_account_id")

        # Dati cliente opzionali (passati direttamente al repository)
        cliente_data: dict[str, Any] = {}
        for key in ["termine_pagamento_id", "modalita_pagamento_id", "iva_id",
                     "nr_giorni_scadenza"]:
            val = optional_int(payload, key)
            if val is not None:
                cliente_data[key] = val
        for key in ["tipo_gg_scadenza_ft", "cliente_pa", "split_payment",
                     "garanzia_tipo"]:
            val = optional_str(payload, key)
            if val is not None:
                cliente_data[key] = val
        for key in ["codice_cig", "codice_cup", "codice_commessa"]:
            val = optional_str(payload, key)
            if val is not None:
                cliente_data[key] = val
        if "servizio_da_fatturare" in payload:
            cliente_data["servizio_da_fatturare"] = bool(payload["servizio_da_fatturare"])
        if "garanzia_importo" in payload and payload["garanzia_importo"] is not None:
            cliente_data["garanzia_importo"] = payload["garanzia_importo"]

        # --- Validazione utility ---
        utility = self._repo.get_utility(utility_id)
        ErrorManager.require(utility is not None, code=E_ANAG_VALIDAZIONE,
                             message="Utility non trovata o non attiva.")
        assert utility is not None

        # Se creazione manuale (no istanza pre-esistente), l'utility non deve richiedere PDP
        if istanza_utility_id is None:
            ErrorManager.require(
                not utility["richiede_pdp"], code=E_ANAG_VALIDAZIONE,
                message="Utility con PDP richiesto: la creazione manuale non e' ammessa. "
                        "Utilizzare il motore pratiche.")

        with transaction.atomic():
            return self._execute_creazione(
                soggetto_id=soggetto_id,
                utility_id=utility_id,
                istanza_utility_id=istanza_utility_id,
                billing_account_id=billing_account_id,
                indirizzo_dettaglio_id=indirizzo_dettaglio_id,
                ba_fatturazione_ordini=ba_fatturazione_ordini,
                ba_parent_account_id=ba_parent_account_id,
                cliente_data=cliente_data,
            )

    # Scopo: Esegue la catena di creazione dentro la transazione atomica.
    #        Step: ruolo CLIENTE → istanza (se manca) → BA (se manca) → cliente.
    def _execute_creazione(
        self, *,
        soggetto_id: str,
        utility_id: int,
        istanza_utility_id: int | None,
        billing_account_id: int | None,
        indirizzo_dettaglio_id: int | None,
        ba_fatturazione_ordini: str | None,
        ba_parent_account_id: int | None,
        cliente_data: dict[str, Any],
    ) -> dict[str, Any]:
        # Step 1: Ruolo CLIENTE (get or create)
        soggetto_ruolo_id = self._repo.get_or_create_ruolo_cliente(soggetto_id)

        # Step 2: Istanza utility
        if istanza_utility_id is not None:
            istanza_utility_id = self._validate_istanza(
                istanza_utility_id, soggetto_id, utility_id)
        else:
            istanza_utility_id = self._repo.create_istanza_fittizia(
                soggetto_id=soggetto_id,
                indirizzo_dettaglio_id=indirizzo_dettaglio_id)

        # Step 3: Billing account
        if billing_account_id is not None:
            billing_account_id = self._validate_billing_account(
                billing_account_id, istanza_utility_id)
        else:
            billing_account_id = self._repo.create_billing_account(
                istanza_utility_id=istanza_utility_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                utility_id=utility_id,
                fatturazione_ordini=ba_fatturazione_ordini,
                parent_account_id=ba_parent_account_id)

        # Step 4: Cliente — passa dati obbligatori + opzionali dal payload
        try:
            cliente_id = self._repo.create_cliente(
                istanza_utility_id=istanza_utility_id,
                billing_account_id=billing_account_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                **cliente_data,
            )
        except IntegrityError as exc:
            err_detail = str(exc)
            if "uq_clienti_istanza_utility" in err_detail:
                raise ServiceError(
                    code=E_ANAG_DUPLICATO,
                    message="Esiste gia' un cliente per questa istanza.",
                    detail=err_detail) from exc
            raise

        return {
            "id": cliente_id,
            "istanza_utility_id": istanza_utility_id,
            "billing_account_id": billing_account_id,
            "soggetto_ruolo_id": soggetto_ruolo_id,
        }

    # =================================================================
    # Step interni — validazione entita' pre-esistenti
    # =================================================================

    # Scopo: Valida istanza pre-esistente: deve esistere, appartenere al soggetto
    #        e alla utility indicata.
    def _validate_istanza(
        self, istanza_utility_id: int, soggetto_id: str, utility_id: int,
    ) -> int:
        istanza = self._repo.get_istanza(istanza_utility_id)
        ErrorManager.require(istanza is not None, code=E_ANAG_NOT_FOUND,
                             message="Istanza utility non trovata.")
        assert istanza is not None
        ErrorManager.require(
            str(istanza["soggetto_id"]) == str(soggetto_id), code=E_ANAG_VALIDAZIONE,
            message="L'istanza non appartiene al soggetto indicato.")
        ErrorManager.require(
            istanza["utility_id"] == utility_id, code=E_ANAG_VALIDAZIONE,
            message="L'istanza non corrisponde alla utility indicata.")
        return istanza_utility_id

    # Scopo: Valida billing account pre-esistente: deve esistere e appartenere
    #        all'istanza indicata.
    def _validate_billing_account(
        self, billing_account_id: int, istanza_utility_id: int,
    ) -> int:
        ba = self._repo.get_billing_account(billing_account_id)
        ErrorManager.require(ba is not None, code=E_ANAG_NOT_FOUND,
                             message="Billing account non trovato.")
        assert ba is not None
        ErrorManager.require(
            ba["istanza_utility_id"] == istanza_utility_id, code=E_ANAG_VALIDAZIONE,
            message="Il billing account non appartiene all'istanza indicata.")
        return billing_account_id

