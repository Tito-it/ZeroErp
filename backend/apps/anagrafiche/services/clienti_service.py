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

from django.db import transaction

from apps.anagrafiche.db.clienti_repository import ClientiRepository
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.error_codes import (
    E_ANAG_NOT_FOUND,
    E_ANAG_VALIDAZIONE,
    E_BA_ADMIN_GLOBALE_VIETATO,
)
from apps.anagrafiche.services._validators import create_with_constraint_mapping, optional_str, require_found
from apps.anagrafiche.services.contatti_service import crea_contatto_inline_se_valido
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
    #        via PermissionResolver.get_emittenti_pk_ids. None = bypass
    #        (superuser/admin globale/0 emittenti). Refactor operatore-
    #        emittenti, follow-up BE-3.5: senza questo filtro un operatore
    #        di EF A vedrebbe i clienti di EF B nella lista.
    def list_clienti(self, **params: Any) -> tuple[list, int]:
        return self._repo.list_clienti(**params)

    # Scopo: Risolve i filtri attivi della lista in dict
    #        {label_italiano: descrizione_leggibile} per l'header
    #        dell'export DEF-1. Sostituisce il dump JSON opaco
    #        ("utility_id: 5") con etichette comprensibili
    #        ("Utility: Servizio Base").
    #
    #        Pattern: il dominio sa quali filtri ha e quale lookup
    #        risolve la descrizione (qui utility/stato). In DEF-8 ogni
    #        lista replica lo stesso pattern domain-specific.
    #
    #        Fallback: se il lookup non trova match (id obsoleto), usa
    #        "id=N" per non perdere informazione.
    def resolve_filtri_export_label(
        self,
        *,
        search: str | None = None,
        utility_id: int | None = None,
        stato_cliente_id: int | None = None,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if search:
            out["Ricerca"] = search
        if utility_id is not None:
            desc = self._repo.get_utility_descrizione(utility_id)
            out["Utility"] = desc or f"id={utility_id}"
        if stato_cliente_id is not None:
            desc = self._repo.get_stato_cliente_descrizione(stato_cliente_id)
            out["Stato"] = desc or f"id={stato_cliente_id}"
        return out

    # Scopo: Lista utility ammesse per creazione manuale.
    def list_utilities_manuali(self) -> list[dict[str, Any]]:
        return self._repo.list_utilities_manuali()

    # Scopo: Dettaglio completo di un cliente.
    def get_cliente(self, cliente_id: int) -> dict[str, Any]:
        return require_found(self._repo.get_cliente(cliente_id), "Cliente non trovato.")

    # Scopo: Aggiorna campi editabili di un cliente (pagamento, PA, garanzia, servizio).
    #        La categoria cliente vive sul BA (pricing v5 STADIO 2), i campi
    #        editabili sul cliente: entrambe le scritture vengono fuse in una
    #        sola statement atomica dalla funzione madre anagrafiche.fn_update_cliente
    #        (fix analisi-fix-transazioni Classe A, finding #1). Prima erano due
    #        UPDATE separati in autocommit: il fallimento del secondo lasciava la
    #        categoria BA committata su uno stato parziale.
    def update_cliente(self, cliente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        # Guard esistenza + scope (RLS): 404 pulito E_ANAG_NOT_FOUND se il
        # cliente non esiste o e' fuori dallo scope emittente dell'operatore.
        self.get_cliente(cliente_id)

        # Estrae la categoria BA dal payload senza mutare il dict del caller
        # (il view/chiamante potrebbe usarlo per audit/logging). Validazione
        # fail-fast: intero positivo (la FK e' comunque validata dal DB).
        ba_categoria = payload.get("ba_categoria_cliente_id") if isinstance(payload, dict) else None
        if ba_categoria is not None:
            ErrorManager.require(
                isinstance(ba_categoria, int)
                and not isinstance(ba_categoria, bool)
                and ba_categoria > 0,
                code=E_ANAG_VALIDAZIONE,
                message="ba_categoria_cliente_id deve essere un intero positivo.",
                context={"ba_categoria_cliente_id": ba_categoria},
            )

        # Campi editabili del cliente = payload meno la categoria BA (che ha un
        # canale dedicato). La whitelist effettiva e' applicata dal repository.
        cliente_fields = (
            {k: v for k, v in payload.items() if k != "ba_categoria_cliente_id"}
            if isinstance(payload, dict)
            else {}
        )

        # Una sola SELECT fn_madre(): categoria BA + campi cliente in atomica.
        result = self._repo.update_cliente_atomico(
            cliente_id,
            ba_categoria_cliente_id=ba_categoria,
            cliente_fields=cliente_fields,
        )
        # L'esistenza e' gia' garantita dal guard get_cliente sopra: se entrambi
        # i flag sono False il cliente c'e' ma il payload non conteneva nessun
        # campo editabile ne' la categoria (niente da aggiornare) -> validazione
        # (400), non "non trovato" (404): il cliente esiste (review 2026-07-08).
        ErrorManager.require(
            result["categoria_aggiornata"] or result["campi_aggiornati"],
            code=E_ANAG_VALIDAZIONE,
            message="Nessun campo da aggiornare.",
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
        # Pricing v5 STADIO 2: categoria_cliente_id obbligatoria quando si crea
        # un nuovo BA (no default implicito). Scelta voluta: la categoria e'
        # dimensione commerciale rilevante per il pricing, non deve essere
        # assegnata implicitamente. Se il BA e' pre-esistente la categoria e'
        # gia' sul BA e il valore qui e' ignorato.
        ba_categoria_cliente_id = optional_int(payload, "ba_categoria_cliente_id")
        if billing_account_id is None:
            ErrorManager.require(
                ba_categoria_cliente_id is not None,
                code=E_ANAG_VALIDAZIONE,
                message="ba_categoria_cliente_id obbligatorio per creare un nuovo BA.",
            )

        # Dati cliente (passati direttamente al repository)
        cliente_data: dict[str, Any] = {}
        for key in ["termine_pagamento_id", "modalita_pagamento_id"]:
            val = optional_int(payload, key)
            if val is not None:
                cliente_data[key] = val
        # ⛔ Sei chiavi tolte il 2026-08-29 (I0/I8 del brief
        #    brief-be-fe-iva-risolutore-e-regime-cliente): non sono piu' colonne
        #    di `anagrafiche.clienti`.
        #    ⭐ E con loro se ne va il default `DEFAULT_IVA_ID`, che era il difetto
        #      nel difetto: `iva_id` era NOT NULL senza default DB, quindi il
        #      service la riempiva SEMPRE — ogni cliente portava un codice IVA che
        #      nessuno aveva scelto, indistinguibile da uno scelto apposta.
        #      L'influenza del soggetto sull'IVA passa da un titolo documentato
        #      (D10), mai da una colonna di default (D7-bis).
        #    Le nuove sedi: `split_payment`/`cliente_pa` su `anagrafiche.soggetti`
        #    (D8), `codice_cig`/`_cup`/`_commessa` su `vendite.contratti` (D9).
        garanzia_tipo = optional_str(payload, "garanzia_tipo")
        if garanzia_tipo is not None:
            cliente_data["garanzia_tipo"] = garanzia_tipo
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
            # Pricing v5 STADIO 2: categoria_cliente_id e' obbligatoria; la
            # validazione e' gia' stata effettuata in crea_cliente (no default
            # implicito). La FK e' validata dal DB.
            assert ba_categoria_cliente_id is not None
            billing_account_id = self._repo.create_billing_account(
                istanza_utility_id=istanza_utility_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                utility_id=utility_id,
                fatturazione_ordini=ba_fatturazione_ordini,
                parent_account_id=ba_parent_account_id,
                categoria_cliente_id=ba_categoria_cliente_id)

        # Step 4: Cliente — passa dati obbligatori + opzionali dal payload
        cliente_id = create_with_constraint_mapping(
            lambda: self._repo.create_cliente(
                istanza_utility_id=istanza_utility_id,
                billing_account_id=billing_account_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                **cliente_data,
            ),
            {
                "uq_clienti_istanza_utility": (
                    "Esiste gia' un cliente per questa istanza.",
                    "istanza_utility_id",
                ),
            },
        )

        # Step 5: Contatto ruolo inline opzionale (EMPTY→skip, PARTIAL→errore, VALID→crea).
        crea_contatto_inline_se_valido(
            self._sogg_repo, soggetto_id, soggetto_ruolo_id, contatto_data)

        # Step 6: Indirizzi ruolo (se forniti dal drawer inline — auto-clone incluso)
        if indirizzi_data:
            from apps.anagrafiche.services.soggetti_service import SoggettiService
            SoggettiService().create_indirizzi_ruolo(
                soggetto_ruolo_id, indirizzi_data, tipo_ruolo_codice="CL")

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

