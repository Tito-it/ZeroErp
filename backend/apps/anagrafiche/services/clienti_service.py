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
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.error_codes import (
    E_ANAG_DUPLICATO,
    E_ANAG_NOT_FOUND,
    E_ANAG_VALIDAZIONE,
    E_BA_ADMIN_GLOBALE_VIETATO,
)
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
        self._sogg_repo = SoggettiRepository()

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata clienti.
    #        Param `emittente_ids` (lista bigint[] di soggetto_ruolo_id
    #        emittente, oppure None) e' lo scope risolto dal chiamante
    #        via PermissionResolver.get_emittenti_ids. None = bypass
    #        (superuser/admin globale/0 emittenti). Refactor operatore-
    #        emittenti, follow-up BE-3.5: senza questo filtro un operatore
    #        di EF A vedrebbe i clienti di EF B nella lista.
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

    # Scopo: Aggiorna campi editabili di un cliente (pagamento, PA, garanzia, servizio).
    def update_cliente(self, cliente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        # Verifica che il cliente esista.
        cliente = self.get_cliente(cliente_id)

        # Pricing v5 STADIO 2: la categoria vive sul BA, non sul cliente.
        # Se presente nel payload, la estrae e la scrive separatamente sul BA
        # prima di passare i restanti campi al repo cliente. FK validata dal DB.
        #
        # Importante (B2 review 2026-04-15): estraiamo senza mutare il dict
        # del caller; il view/chiamante potrebbe usarlo per audit/logging.
        ba_categoria = payload.get("ba_categoria_cliente_id") if isinstance(payload, dict) else None
        ba_categoria_changed = False
        if ba_categoria is not None:
            ErrorManager.require(
                isinstance(ba_categoria, int)
                and not isinstance(ba_categoria, bool)
                and ba_categoria > 0,
                code=E_ANAG_VALIDAZIONE,
                message="ba_categoria_cliente_id deve essere un intero positivo.",
                context={"ba_categoria_cliente_id": ba_categoria},
            )
            ba_id = cliente["billing_account_id"]
            self._repo.update_ba_categoria(ba_id, ba_categoria)
            ba_categoria_changed = True

        # Costruisce payload filtrato per il repo cliente (no mutation sul caller).
        cliente_payload = (
            {k: v for k, v in payload.items() if k != "ba_categoria_cliente_id"}
            if isinstance(payload, dict)
            else payload
        )
        updated = self._repo.update_cliente(cliente_id, cliente_payload) if cliente_payload else False
        ErrorManager.require(
            updated or ba_categoria_changed,
            code=E_ANAG_NOT_FOUND,
            message="Cliente non trovato o nessun campo modificato.",
        )
        return {"updated": True}

    # =================================================================
    # Creazione cliente (orchestratore riusabile)
    # =================================================================

    # Scopo: Guard applicativo refactor operatore-emittenti (Q6).
    #        Blocca la creazione BA per admin globale quando esistono
    #        emittenti fiscali nel sistema. Difesa "early reject" per
    #        dare un errore pulito (E_BA_ADMIN_GLOBALE_VIETATO, 403)
    #        invece di un fallimento generico del trigger DB.
    #        Defense-in-depth: il trigger
    #        anagrafiche.trgfn_billing_account_guard_admin_globale
    #        e' la difesa finale lato DB.
    #        Skip se auth_user_id e' None (contesto di sistema, es.
    #        test fixture o bootstrap non-API).
    def _guard_can_create_ba(self, auth_user_id: int | None) -> None:
        if auth_user_id is None:
            return
        if not self._repo.check_user_can_create_ba(auth_user_id):
            raise ServiceError(
                code=E_BA_ADMIN_GLOBALE_VIETATO,
                message=(
                    "Un amministratore globale non puo' creare billing "
                    "account quando esistono emittenti fiscali. Operare "
                    "come operatore di un emittente specifico."
                ),
            )

    # Scopo: Crea un cliente completo in una transazione atomica.
    #        Obiettivo: generare la catena istanza → BA → cliente.
    #        Perimetro: se istanza_utility_id/billing_account_id forniti,
    #        li valida e riusa; se NULL, li genera in trasparenza.
    #        Risultato: dict con id del cliente creato e delle entita' collegate.
    #        Param auth_user_id: ID Django dell'utente chiamante (None per
    #        contesti di sistema). Usato per il guard refactor operatore-
    #        emittenti che blocca admin globale + emittenti presenti.
    def crea_cliente(
        self, payload: dict[str, Any], *, auth_user_id: int | None = None
    ) -> dict[str, Any]:
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

        # Guard refactor operatore-emittenti (Q6): admin globale non puo'
        # creare BA se ci sono emittenti. Solo se non c'e' un BA pre-esistente
        # (perche' in quel caso si riusa, non si crea).
        if billing_account_id is None:
            self._guard_can_create_ba(auth_user_id)

        # Parametri opzionali
        indirizzo_dettaglio_id = optional_int(payload, "indirizzo_dettaglio_id")
        ba_fatturazione_ordini = optional_str(payload, "ba_fatturazione_ordini")
        ba_parent_account_id = optional_int(payload, "ba_parent_account_id")
        # Pricing v5 STADIO 2: categoria_cliente_id opzionale; se assente il
        # repository defaulta a 'STANDARD'. La FK e' validata dal DB.
        ba_categoria_cliente_id = optional_int(payload, "ba_categoria_cliente_id")

        # Dati cliente (passati direttamente al repository)
        cliente_data: dict[str, Any] = {}
        for key in ["termine_pagamento_id", "modalita_pagamento_id", "iva_id",
                     "nr_giorni_scadenza"]:
            val = optional_int(payload, key)
            if val is not None:
                cliente_data[key] = val
        # iva_id e' NOT NULL senza default DB: se non fornito, risolvi dal DB
        if "iva_id" not in cliente_data:
            cliente_data["iva_id"] = self._repo.get_default_iva_id()
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

        # Contatto e indirizzi inline (opzionali, per creazione da drawer)
        contatto_data = payload.get("contatto")
        indirizzi_data = payload.get("indirizzi", [])

        with transaction.atomic():
            return self._execute_creazione(
                soggetto_id=soggetto_id,
                utility_id=utility_id,
                istanza_utility_id=istanza_utility_id,
                billing_account_id=billing_account_id,
                indirizzo_dettaglio_id=indirizzo_dettaglio_id,
                ba_fatturazione_ordini=ba_fatturazione_ordini,
                ba_parent_account_id=ba_parent_account_id,
                ba_categoria_cliente_id=ba_categoria_cliente_id,
                cliente_data=cliente_data,
                contatto_data=contatto_data,
                indirizzi_data=indirizzi_data,
            )

    # Scopo: Esegue la catena di creazione dentro la transazione atomica.
    #        Step: ruolo CLIENTE → istanza → BA → cliente → contatto → indirizzi ruolo.
    def _execute_creazione(
        self, *,
        soggetto_id: str,
        utility_id: int,
        istanza_utility_id: int | None,
        billing_account_id: int | None,
        indirizzo_dettaglio_id: int | None,
        ba_fatturazione_ordini: str | None,
        ba_parent_account_id: int | None,
        ba_categoria_cliente_id: int | None = None,
        cliente_data: dict[str, Any],
        contatto_data: dict[str, Any] | None = None,
        indirizzi_data: list[dict[str, Any]] | None = None,
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
            # Pricing v5 STADIO 2: categoria_cliente_id e' NOT NULL in DB. Se il
            # chiamante non la passa, risolviamo esplicitamente STANDARD e
            # falliamo con messaggio parlante se il seed manca (B1 review
            # 2026-04-15: evita IntegrityError opaco da subquery NULL).
            effective_categoria_id = ba_categoria_cliente_id
            if effective_categoria_id is None:
                effective_categoria_id = self._repo.get_categoria_cliente_id_by_codice(
                    "STANDARD"
                )
                ErrorManager.require(
                    effective_categoria_id is not None,
                    code=E_ANAG_VALIDAZIONE,
                    message="Categoria cliente 'STANDARD' non configurata.",
                    detail=(
                        "Seed anagrafiche.categorie_clienti mancante: il "
                        "backfill F1-DB-03 deve essere applicato oppure la "
                        "categoria di default deve essere fornita esplicitamente."
                    ),
                )
            billing_account_id = self._repo.create_billing_account(
                istanza_utility_id=istanza_utility_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                utility_id=utility_id,
                fatturazione_ordini=ba_fatturazione_ordini,
                parent_account_id=ba_parent_account_id,
                categoria_cliente_id=effective_categoria_id)

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

        # Step 5: Contatto ruolo (se fornito dal drawer inline)
        if contatto_data and contatto_data.get("nominativo"):
            self._sogg_repo.crea_contatto(
                soggetto_id,
                nominativo=contatto_data.get("nominativo", ""),
                email=optional_str(contatto_data, "email"),
                telefono=optional_str(contatto_data, "telefono"),
                cellulare=optional_str(contatto_data, "cellulare"),
                pec=optional_str(contatto_data, "pec"),
                tipo_contatto_id=optional_int(contatto_data, "tipo_contatto_id"),
                note=optional_str(contatto_data, "note"),
                soggetto_ruolo_id=soggetto_ruolo_id,
            )

        # Step 6: Indirizzi ruolo (se forniti dal drawer inline — auto-clone incluso)
        if indirizzi_data:
            from apps.anagrafiche.services.fornitori_service import FornitoriService
            FornitoriService()._create_indirizzi_ruolo(
                soggetto_ruolo_id, list(indirizzi_data), tipo_ruolo_codice="CL")

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

