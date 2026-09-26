# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service facade per vendite.offerte_commerciali + eccezioni +
#        utility 1:1 (CRUD iniziale, step DB 1-4 atterrati 2026-05-24).
#
#        L'offerta commerciale e' il documento pre-contrattuale: vive nel
#        ciclo BOZZA -> EMESSA -> (ACCETTATA | RIFIUTATA | SUPERATA) +
#        terminale di ritiro BOZZA -> ANNULLATA. La state machine e' enforced
#        dal trigger DB trgfn_offerte_commerciali_guard_transizione; il
#        service applica solo pre-validazioni applicative (stato corrente,
#        payload obbligatorio motivazione su RIFIUTATA/ANNULLATA) e lascia
#        al DB le invarianti complesse (listino_versione_id NULL in
#        emissione, listino non ATTIVO, transizione non ammessa, ecc.).
#
#        Stato 2026-05-25: tutti gli step DB 1-9 atterrati. Il service
#        espone l'intero ciclo dell'offerta commerciale: create -> emetti ->
#        registra_esito -> push_a_contratto + revisione e annullamento.
#        Niente metodo "fuori scope" residuo.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.core.services.error_manager import ErrorManager
from apps.core.services.capability_blob import capabilities_o_vuoto
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import (
    PayloadValidator,
    translate_db_errors,
)
from apps.vendite.db.listini_repository import ListiniRepository
from apps.vendite.db.offerte_repository import _ORDER_COLS_OFFERTE, OfferteRepository
from apps.vendite.services._indirizzi_documento_helpers import (
    IndirizziDocumentoConfig,
    auto_assegna_indirizzo_default,
    delete_indirizzo_documento,
    list_indirizzi_documento,
    upsert_indirizzo_documento,
)
from apps.vendite.services._approvazioni_prezzo_constants import (
    SORGENTE_OFFERTA,
    STATO_APPROVAZIONE_PENDING,
)
from apps.vendite.services._componenti_service_helpers import (
    dati_patch_componente,
    normalize_componenti_overrides,
    resolve_emittente_sr_id_for_testata,
)
from apps.vendite.services._pricing_gate_helpers import (
    guard_uom_id_positive,
    resolve_or_check_override_prezzo,
    validate_componenti_overrides_authorization,
)
from apps.vendite.types import OffertaPushResult

logger = logging.getLogger(__name__)


# Codici errore applicativi (registrati in apps.core.services.error_policies).
# Riusiamo E_VENDITE_* per coerenza con preventivi/contratti; i codici DB
# specifici (E_OFFERTA_TRANSIZIONE_NON_AMMESSA, ecc.) emergono dal trigger
# guard e vengono mappati dal middleware API (P0001 -> 422 con codice
# applicativo passato dal RAISE EXCEPTION del DB).
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"


# Pattern per estrarre il codice errore applicativo dal MESSAGE dei trigger
# DB. Convenzione progetto: `RAISE EXCEPTION USING MESSAGE='E_OFFERTA_XXX'`.
# Il primo token con underscore in maiuscolo che inizia per E_ e' il codice.


# Codici stato documento (chiavi naturali `codice_interno` in
# config.stati_doc_offerte). Usate per:
#  - lookup id stato target via `get_stato_id_by_codice`
#  - assertion di stato corrente nelle transizioni
#  - test (fixtures + asserzioni)
class StatoOfferta:
    BOZZA = "BOZZA"
    EMESSA = "EMESSA"
    ACCETTATA = "ACCETTATA"
    RIFIUTATA = "RIFIUTATA"
    ANNULLATA = "ANNULLATA"
    SUPERATA = "SUPERATA"


# Set di stati editabili (testata, eccezioni, utility). Estraibile in futuro
# se le regole differenziassero per oggetto (oggi e' "solo BOZZA").
_STATI_EDITABILI: frozenset[str] = frozenset({StatoOfferta.BOZZA})


# Set "azionabili da EMESSA": registra_accettazione, registra_rifiuto,
# crea_revisione partono tutti da stato EMESSA. Estratto come costante per
# evitare 3 allocazioni `frozenset({EMESSA})` ad ogni chiamata di guard.
_STATI_DA_EMESSA: frozenset[str] = frozenset({StatoOfferta.EMESSA})


# Set "pushabili a contratto": solo ACCETTATA (Step 8 brief DB).
_STATI_PUSHABILI: frozenset[str] = frozenset({StatoOfferta.ACCETTATA})


# Set di esiti cliente da EMESSA (used by registra_esito routing).
_ESITI_AMMESSI_DA_EMESSA: frozenset[str] = frozenset(
    {StatoOfferta.ACCETTATA, StatoOfferta.RIFIUTATA}
)


# Whitelist order_by ammessi dal service (gate prima del repository), DERIVATA
# dalla whitelist del repository (`_ORDER_COLS_OFFERTE`), unica fonte di verita'
# — stesso schema di `_ORDER_BY_CONTRATTI`.
#
# Era una copia scritta a mano, e il 2026-07-31 aveva gia' divergito: teneva
# `stato_codice_interno` e `data_update` dopo che il repository li aveva persi.
# Un gate piu' largo del repository non protegge, sposta il difetto di un piano:
# la chiave passa la validazione e poi il repository ripiega in silenzio.
# `revisione_numero` ASSENTE: non ordinabile (decisione §7.3).
_ORDER_BY_OFFERTE: frozenset[str] = frozenset(_ORDER_COLS_OFFERTE)


# Stati in cui l'offerta non si modifica e non offre azioni all'operatore.
#
# ⛔ NON piu' «senza transizioni uscenti», e la differenza e' del 2026-08-28:
#    `SUPERATA` una transizione uscente ORA CE L'HA — `SUPERATA -> EMESSA`, che
#    il database percorre da se' quando l'ultima revisione viva viene annullata
#    e il padre deve tornare a essere l'offerta del lineage. E' seedata
#    `manuale: false`, quindi non compare fra le azioni disponibili e nessun
#    pulsante la propone: per chi guarda lo stato resta chiuso, ma dire «non ha
#    uscite» era vero fino a ieri e adesso non lo e' piu'.
#
# ⚠️ COSTANTE NON USATA: nessuno la legge, in tutto il backend. Resta perche'
#    cancellarla e' una decisione di chi possiede le offerte, non di chi passava
#    di qui — ma una costante morta che dichiara anche una cosa falsa e' il
#    peggio dei due casi, e la dichiarazione e' stata corretta.
_STATI_TERMINALI: frozenset[str] = frozenset(
    {"ACCETTATA", "RIFIUTATA", "ANNULLATA", "SUPERATA"}
)


# UNIQUE constraints catalogati per mappare violazioni IntegrityError.
# Formato richiesto da `map_integrity_error`: tuple[error_code, message].
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_offerte_commerciali_codice": (
        E_VENDITE_DUPLICATO,
        "Codice offerta gia' esistente.",
        "codice",
    ),
    "uq_offerte_commerciali_uid": (
        E_VENDITE_DUPLICATO,
        "UID offerta gia' esistente.",
    ),
    "uq_offerte_commerciali_utilities_offerta_id": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' un record utility per questa offerta (1:1).",
    ),
    "uq_offerte_eccezioni_one_eccezione_per_articolo": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' un'eccezione OVERRIDE/ESCLUSIONE per questo articolo "
        "nell'offerta.",
    ),
    "uq_offerte_eccezioni_one_aggiunta_per_articolo": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' un'eccezione AGGIUNTA per questo articolo nell'offerta.",
    ),
}


# FK constraints catalogati (best-effort: i nomi corrispondono a quelli
# emessi da Postgres su violazione FK).
_FK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "fk_offerte_commerciali_billing_account": (
        E_VENDITE_FK, "Billing account non trovato.",
    ),
    "fk_offerte_commerciali_emittente_fiscale": (
        E_VENDITE_FK, "Emittente fiscale non trovato.",
    ),
    "fk_offerte_commerciali_listino": (
        E_VENDITE_FK, "Listino non trovato.",
    ),
    "fk_offerte_commerciali_listino_versione": (
        E_VENDITE_FK, "Versione listino non trovata.",
    ),
    "fk_offerte_commerciali_istanza_utility": (
        E_VENDITE_FK, "Istanza utility non trovata.",
    ),
    "fk_offerte_commerciali_utility": (
        E_VENDITE_FK, "Utility non trovata.",
    ),
    "fk_offerte_eccezioni_articolo": (
        E_VENDITE_FK, "Articolo non trovato.",
    ),
    "fk_offerte_eccezioni_offerta": (
        E_VENDITE_FK, "Offerta non trovata.",
    ),
}


# Whitelist payload create offerta (testata).
# Step 5 brief DB atterrato 2026-05-25: il codice OFC-* e' generato dal trigger
# `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT). Il campo `codice` NON
# va piu' nel payload: se inviato si rifiuta come unknown_key (defense-in-depth
# applicativo; il trigger DB e' la garanzia ultima).
_CREATE_KEYS_OFFERTA: frozenset[str] = frozenset({
    "emittente_fiscale_id",
    "billing_account_id",
    "istanza_utility_id",
    "utility_id",
    "listino_id",
    "listino_versione_id",
    # Snapshot valuta fissato al CREATE, opzionale: se non passato, il
    # trigger DB `_a*_set_valuta_default_ins` risolve via
    # `vendite.fn_get_valuta_id` (catena BA → emittente → gestore, brief
    # work-done 2026-05-29). Il FE form-defaults può pre-popolarlo via BB
    # `resolve_valuta_default` per UX.
    "valuta_id",
    "valore_variazione_globale",
    "tipo_variazione_globale",
    "validita_dal",
    "validita_al",
    "meta",
    # Sub-oggetto opzionale per la creazione contestuale del record
    # utility 1:1 (mirror ContrattoDrawer pattern, piano §C2). Se presente,
    # il service crea l'offerta + utility nella stessa transazione,
    # evitando il flusso "create offerta poi PATCH utility" che lascerebbe
    # un'offerta orfana di utility su fallimento intermedio.
    "utility",
})


# Whitelist payload update offerta (testata). Sub-set di create (immutabili:
# codice/uid/stato_doc_offerta_id/revisione_numero/revisione_padre_id e
# tutti i campi audit/timestamp di transizione).
_UPDATE_KEYS_OFFERTA: frozenset[str] = frozenset({
    "emittente_fiscale_id",
    "billing_account_id",
    "istanza_utility_id",
    "utility_id",
    "listino_id",
    "listino_versione_id",
    "valore_variazione_globale",
    "tipo_variazione_globale",
    "validita_dal",
    "validita_al",
    "meta",
    # Sub-oggetto opzionale per upsert del record utility 1:1 nella stessa
    # transazione (simmetria col create, mirror ContrattoDrawer pattern).
    # Se valorizzato, l'update testata + l'upsert utility sono atomici.
    "utility",
})


# Whitelist payload eccezione (create).
# `componenti_overrides` non e' campo di `offerte_commerciali_eccezioni`:
# viene estratto pre-INSERT e passato a `fn_offerta_eccezione_componenti_init`
# (auto-init post-create_eccezione su articolo composito).
# Tipi eccezione che ammettono un prezzo manuale e quindi passano dal gate
# L1/L2/L3 (mirror di `contratti_service._TIPI_ECCEZIONE_CON_GATE`).
# ESCLUSIONE ha prezzo NULL → nessun gate.
_TIPI_ECCEZIONE_CON_GATE: frozenset[str] = frozenset({"OVERRIDE", "AGGIUNTA"})


_CREATE_KEYS_ECCEZIONE: frozenset[str] = frozenset({
    "articolo_id",
    "tipo_eccezione",
    "tipo_erogazione",
    "fonte_quantita_attesa",
    "periodicita",
    "generazione_canone",
    "competenza_canone",
    "prezzo_unitario",
    "quantita",
    "qta_operativa",
    "uom_operativa_id",
    "factor_to_base",
    "ordine",
    "attivo",
    "meta",
    "componenti_overrides",
    # Flag opt-in workflow L3 (richiesta approvazione su violazione L2). Non e'
    # colonna DB: estratto pre-INSERT dal service (mirror contratti).
    "richiesta_approvazione",
})


# Whitelist payload eccezione (update): articolo_id e tipo_eccezione immutabili.
# `componenti_overrides` non re-spedito in update (la BoM e' contratto
# immutabile post-init); la modifica prezzi componente passa via endpoint
# CRUD dedicato `PATCH .../componenti/<cid>/`.
_UPDATE_KEYS_ECCEZIONE: frozenset[str] = frozenset(
    _CREATE_KEYS_ECCEZIONE - {
        "articolo_id", "tipo_eccezione", "componenti_overrides",
    }
)


# Whitelist payload utility (create).
_CREATE_KEYS_UTILITY: frozenset[str] = frozenset({
    "istanza_utility_id",
    "utility_id",
    "istanza_dati_precontrattuali_id",
    "tipo_utenza_id",
    "classe_utenza_id",
    "param_1_num",
    "param_2_txt",
    "meta",
})


# Whitelist payload utility (update): istanza_utility_id/utility_id immutabili.
_UPDATE_KEYS_UTILITY: frozenset[str] = frozenset(
    _CREATE_KEYS_UTILITY - {"istanza_utility_id", "utility_id"}
)


class OfferteService:
    """Service CRUD offerte commerciali — ciclo completo (D6, BE 2026-05-25)."""

    def __init__(self) -> None:
        self._repo = OfferteRepository()
        self._v = PayloadValidator(
            validation_code=E_VENDITE_VALIDATION,
            log_to_db=True,
            function_name="offerte_service",
        )

    # =================================================================
    # Guard DB errors uniforme
    # =================================================================

    # Scopo: Normalizza errori DB (IntegrityError + DatabaseError P0001 dei
    #        trigger guard, codici E_OFFERTA_* parlanti) in ServiceError.
    #        Delega al BB condiviso `translate_db_errors` (core
    #        payload_helpers, estratto 2026-07-13 — regola del 2 alla 5a
    #        copia); resta la firma context-based per i call site del service.
    @contextmanager
    def _db_errors(
        self,
        context: dict[str, Any],
        *,
        fallback_message: str = "Violazione vincolo DB su offerta.",
    ) -> Iterator[None]:
        with translate_db_errors(
            context=context,
            fallback_code=E_VENDITE_VALIDATION,
            fallback_message=fallback_message,
            unique_constraints=_UNIQUE_CONSTRAINTS,
            fk_constraints=_FK_CONSTRAINTS,
        ):
            yield

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata offerte. Niente default temporali impliciti: la UI
    #        applica i propri (es. validita_dal_min = inizio anno-1).
    def list_offerte(
        self,
        *,
        search: str | None = None,
        billing_account_id: int | None = None,
        stato_codice_interno: str | None = None,
        utility_id: int | None = None,
        listino_id: int | None = None,
        validita_dal_min: str | None = None,
        validita_dal_max: str | None = None,
        solo_ultima_revisione: bool = True,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "data_insert",
        order_dir: str = "desc",
        auth_user_id: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_OFFERTE, order_dir=order_dir)
        # ⭐ La soglia del termine (vuoto o sotto 3 caratteri → non filtra) la
        #    applica il BB `add_ricerca_full_condition` nel repository, uguale
        #    per tutte le liste. Fino al 2026-09-23 qui era un 400: il frontend
        #    manda il termine a ogni tasto, e i primi due erano un errore.
        filters: dict[str, Any] = {
            "billing_account_id": billing_account_id,
            "stato_codice_interno": stato_codice_interno,
            "utility_id": utility_id,
            "listino_id": listino_id,
            "validita_dal_min": validita_dal_min,
            "validita_dal_max": validita_dal_max,
            "search": search,
            "solo_ultima_revisione": solo_ultima_revisione,
            # Scope emittente: `None` = nessuna restrizione (superuser a
            # livello API); entra nei filtri cosi' righe e conteggio hanno lo
            # stesso perimetro.
            "auth_user_id": auth_user_id,
        }
        rows = self._repo.list_offerte(
            **filters,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        total = self._repo.count_offerte(**filters)
        return rows, total

    # Scopo: Etichette leggibili dei filtri attivi, incluse come metadato nel
    #        file di export (DEF-1 §6: un file filtrato deve dichiararsi
    #        sottoinsieme). Gemello di ContrattiService.resolve_filtri_export_label.
    def resolve_filtri_export_label(
        self,
        *,
        search: str | None = None,
        stato_codice_interno: str | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        listino_id: int | None = None,
        validita_dal_min: str | None = None,
        validita_dal_max: str | None = None,
        solo_ultima_revisione: bool = True,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if search:
            out["Ricerca"] = search
        if stato_codice_interno:
            out["Stato"] = stato_codice_interno
        if billing_account_id is not None:
            out["Cliente BA (id)"] = billing_account_id
        if utility_id is not None:
            out["Utility (id)"] = utility_id
        if listino_id is not None:
            out["Listino (id)"] = listino_id
        if validita_dal_min:
            out["Dal"] = str(validita_dal_min)
        if validita_dal_max:
            out["Al"] = str(validita_dal_max)
        # solo_ultima_revisione=False = storico revisioni incluso.
        if not solo_ultima_revisione:
            out["Storico revisioni"] = "incluso"
        return out

    # Scopo: Carica la testata offerta o solleva E_VENDITE_NOT_FOUND (BB core
    #        `testata_o_not_found`: qui solo codice e messaggio del dominio).
    #        `getter` ammette il lettore leggero `get_stato_codice`, dove al
    #        chiamante basta sapere che l'offerta esiste.
    def _get_offerta_or_raise(
        self, offerta_id: int, *, op: str,
        getter: Callable[[int], Any] | None = None,
    ) -> Any:
        return testata_o_not_found(
            getter or self._repo.get_offerta, offerta_id,
            code=E_VENDITE_NOT_FOUND, message="Offerta non trovata.",
            id_name="offerta_id", function_name=f"offerte_service.{op}",
        )

    # Scopo: Dettaglio offerta + eccezioni + utility 1:1 + blob capability
    #        (refactor data-driven 2026-05-26). Lo stato della macchina e
    #        le azioni ammesse arrivano da `script.fn_available_actions_offerta`,
    #        cosi' il drawer Vue NON ricalcola nulla lato client (pattern
    #        coerente con contratti/preventivi/promo). Il blob viaggia
    #        intatto SOTTO `capabilities`, non fuso nella testata (api.md
    #        §«Il blob sta SOTTO `capabilities`», 2026-09-23): il merge
    #        nasconde le collisioni invece di evitarle.
    #
    #        Graceful fallback (2026-05-26 post bug fn DB `??` JSONB):
    #        se la fn capability solleva DatabaseError, logghiamo warning e
    #        ritorniamo il dettaglio con `capabilities` VUOTO (la chiave c'e'
    #        sempre: la forma non dipende dall'esito). Il FE cade in readonly
    #        conservativo (canEditTestata=false), ma l'operatore vede
    #        comunque l'offerta — niente errore E_DATABASE criptico al
    #        client per un problema diagnostico del DB. Pattern coerente
    #        col principio "una rottura del capability layer non deve
    #        impedire la lettura dell'entita'".
    def get_offerta(self, offerta_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        row = self._get_offerta_or_raise(offerta_id, op="get_offerta")
        row["eccezioni"] = self._repo.list_eccezioni(offerta_id)
        row["utility"] = self._repo.get_utility(offerta_id)
        row["capabilities"] = capabilities_o_vuoto(
            lambda: self._repo.get_available_actions(offerta_id),
            funzione="fn_available_actions_offerta", entita_id=offerta_id, logger=logger,
        )
        return row

    # =================================================================
    # Create / Update / Delete testata
    # =================================================================

    # Scopo: Crea offerta in stato BOZZA. Il codice `OFC-*` e' generato
    #        dal trigger DB `trgfn_offerte_commerciali_gen_codice` (Step 5,
    #        atterrato 2026-05-25): non va nel payload (rifiutato dalla
    #        whitelist). Lo stato BOZZA si risolve via lookup `codice_interno`.
    def crea_offerta(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS_OFFERTA)
        # Validazioni applicative minime (il DB rifinisce gli invarianti via
        # CHECK chk_offerte_*).
        for required in (
            "emittente_fiscale_id",
            "billing_account_id",
            "istanza_utility_id",
            "utility_id",
            "listino_id",
            "validita_dal",
        ):
            ErrorManager.require(
                required in payload and payload[required] not in (None, ""),
                code=E_VENDITE_VALIDATION,
                message=f"Campo '{required}' obbligatorio in creazione.",
                context={"field": required},
            )
        # Estrae il sub-oggetto utility (opzionale, mirror ContrattoDrawer)
        # PRIMA di passare il payload al repo: la testata non ha la colonna
        # `utility` (vive in offerte_commerciali_utilities) e l'INSERT
        # fallirebbe come colonna inesistente. Atomicita' garantita dalla
        # transaction.atomic() che incapsula entrambe le scritture.
        utility_payload = payload.get("utility")
        if utility_payload is not None:
            ErrorManager.require(
                isinstance(utility_payload, dict),
                code=E_VENDITE_VALIDATION,
                message="Campo 'utility' deve essere oggetto.",
                context={"got": type(utility_payload).__name__},
            )
        stato_bozza_id = self._repo.get_stato_id_by_codice(StatoOfferta.BOZZA)
        ErrorManager.require(
            stato_bozza_id is not None,
            code=E_VENDITE_VALIDATION,
            message="Stato BOZZA non configurato in config.stati_doc_offerte.",
        )
        assert stato_bozza_id is not None
        data: dict[str, Any] = self._con_meta_normalizzato(
            {k: v for k, v in payload.items() if k != "utility"},
        )
        data["stato_doc_offerta_id"] = stato_bozza_id
        # `codice` NON in payload (vedi nota _CREATE_KEYS_OFFERTA): il trigger
        # BEFORE INSERT genera OFC-NNNNNNN via `script.fn_generate_codice`.
        # `revisione_numero` ha default DB = 1.
        with self._db_errors({"billing_account_id": payload.get("billing_account_id")}):
            with transaction.atomic():
                offerta_id = self._repo.create_offerta(data)
                # Utility 1:1 inline: derivata da BA + campi business opzionali.
                # Eredita istanza_utility_id/utility_id dal payload testata se
                # non specificati nel sub-oggetto (coerenza FK garantita dal
                # BA scelto). Saltata se utility_payload e' None.
                if utility_payload is not None:
                    self._add_utility_inline(
                        offerta_id, payload, utility_payload,
                    )
        # UX v2: auto-assegnazione best-effort dell'indirizzo default
        # (indirizzo di ruolo CON del cliente, fallback FATT). Mai bloccante.
        auto_assegna_indirizzo_default(_INDIRIZZI_CFG, int(offerta_id))
        return self.get_offerta(offerta_id)

    # Scopo: Crea il record utility 1:1 contestualmente alla testata. Riusa
    #        la stessa whitelist + guard della crea_utility "esposta", ma
    #        senza il check di stato (siamo dentro la create, l'offerta e'
    #        appena nata in BOZZA per costruzione).
    def _add_utility_inline(
        self,
        offerta_id: int,
        offerta_payload: dict[str, Any],
        utility_payload: dict[str, Any],
    ) -> None:
        # Eredita istanza_utility_id/utility_id dalla testata se non passati
        # esplicitamente nel sub-oggetto (BA -> utility coerente).
        merged = dict(utility_payload)
        merged.setdefault("istanza_utility_id", offerta_payload.get("istanza_utility_id"))
        merged.setdefault("utility_id", offerta_payload.get("utility_id"))
        self._v.validate_allowed_keys(merged, allowed=_CREATE_KEYS_UTILITY)
        merged = self._con_meta_normalizzato(merged)
        for required in ("istanza_utility_id", "utility_id"):
            ErrorManager.require(
                merged.get(required) is not None,
                code=E_VENDITE_VALIDATION,
                message=f"Campo utility.'{required}' obbligatorio.",
                context={"field": required},
            )
        self._repo.create_utility(offerta_id, merged)

    # Scopo: Aggiorna la testata di un'offerta. Editabilita' solo in stato
    #        BOZZA — defense-in-depth applicativa; il trigger DB blocca
    #        comunque cambi su stati terminali. Payload vuoto -> 400 (no-op
    #        silenzioso evitato).
    #
    #        Sub-oggetto opzionale `utility`: se presente, fa upsert del
    #        record utility 1:1 nella stessa transaction.atomic(). Simmetria
    #        col create (refactor atomico 2026-05-26). Eredita
    #        `istanza_utility_id`/`utility_id` dalla testata se non passati
    #        esplicitamente nel sub-oggetto (coerenza FK garantita dal BA).
    def aggiorna_offerta(
        self, offerta_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS_OFFERTA)
        self._guard_payload_non_vuoto(payload, op="aggiorna_offerta")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        # Split testata vs utility prima del repo. La testata non ha la
        # colonna `utility` (vive in offerte_commerciali_utilities).
        utility_payload = payload.get("utility")
        if utility_payload is not None:
            ErrorManager.require(
                isinstance(utility_payload, dict),
                code=E_VENDITE_VALIDATION,
                message="Campo 'utility' deve essere oggetto.",
                context={"got": type(utility_payload).__name__},
            )
        testata_payload = self._con_meta_normalizzato(
            {k: v for k, v in payload.items() if k != "utility"},
        )
        # Guard: payload "vuoto" dopo aver estratto utility non e' un no-op
        # (l'upsert utility e' un side-effect valido).
        if not testata_payload and utility_payload is None:
            self._guard_payload_non_vuoto({}, op="aggiorna_offerta")

        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                if testata_payload:
                    self._repo.update_offerta(offerta_id, testata_payload)
                if utility_payload is not None:
                    self._upsert_utility_inline(offerta_id, utility_payload)
        return self.get_offerta(offerta_id)

    # Scopo: Upsert del record utility 1:1 contestualmente al PATCH testata.
    #        Distingue create (nessuna utility ancora) da update (utility
    #        esistente) tramite lookup; entrambi i rami applicano la stessa
    #        whitelist (`_CREATE_KEYS_UTILITY` per create, `_UPDATE_KEYS_UTILITY`
    #        per update — istanza_utility_id/utility_id immutabili dopo
    #        la creazione del record).
    def _upsert_utility_inline(
        self, offerta_id: int, utility_payload: dict[str, Any]
    ) -> None:
        existing = self._repo.get_utility(offerta_id)
        if existing is None:
            # Create: applica la stessa logica di crea_offerta inline.
            offerta = self._repo.get_offerta(offerta_id)
            assert offerta is not None
            self._add_utility_inline(offerta_id, offerta, utility_payload)
            return
        # Update: gli id (`istanza_utility_id`/`utility_id`) sono immutabili e
        # il sotto-oggetto del form li riporta: si tolgono. ⛔ Ma una chiave
        # SCONOSCIUTA si rifiuta (400), come nel ramo create: fino al
        # 2026-09-26 l'intersezione con la whitelist la scartava in silenzio —
        # un salvataggio «riuscito» senza aver scritto il campo.
        self._v.validate_allowed_keys(utility_payload, allowed=_CREATE_KEYS_UTILITY)
        update_payload = self._con_meta_normalizzato({
            k: v for k, v in utility_payload.items() if k in _UPDATE_KEYS_UTILITY
        })
        if not update_payload:
            return
        self._repo.update_utility(int(existing["id"]), update_payload)

    # Scopo: Elimina un'offerta in stato BOZZA (hard delete). L'annullamento
    #        "di processo" passa invece da `annulla` (BOZZA -> ANNULLATA).
    #        Il `delete` qui resta come pulizia tecnica di bozze "vuote".
    def elimina_offerta(self, offerta_id: int) -> None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                deleted = self._repo.delete_offerta(offerta_id)
                ErrorManager.require(
                    deleted,
                    code=E_VENDITE_NOT_FOUND,
                    message="Offerta non trovata.",
                    context={"offerta_id": offerta_id},
                )

    # =================================================================
    # Transizioni di stato manuali
    # =================================================================

    # Scopo: BOZZA -> EMESSA. Pre-step: "freeze at emission" della versione
    #        listino (lookup ATTIVA alla data odierna + UPDATE offerta) se
    #        non e' gia' fissata; il trigger DB
    #        `trgfn_offerte_commerciali_guard_transizione` richiede infatti
    #        `listino_versione_id NOT NULL` per autorizzare la transizione
    #        (E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO) e l'utente nel
    #        form CREATE seleziona solo il listino, non la versione.
    #        Tutto nella stessa transazione del caller (la view che chiama
    #        `emetti` apre un atomic esterno che include anche la
    #        generazione documento + allegati).
    def emetti(self, offerta_id: int) -> dict[str, Any]:
        # `transaction.atomic()` (nested = savepoint se c'e' gia' un atomic
        # esterno della view, tx vera altrimenti) garantisce che il pre-fill
        # di `listino_versione_id` e il cambio stato siano atomici anche se
        # `emetti` viene invocato standalone (es. command, sync job, test
        # integration). Senza wrap, lo standalone potrebbe lasciare
        # l'offerta con la versione fissata e lo stato ancora BOZZA in
        # caso di errore del trigger del cambio stato.
        with transaction.atomic():
            self._fissa_versione_listino_se_necessario(offerta_id)
            return self._cambia_stato_manuale(
                offerta_id,
                target_codice=StatoOfferta.EMESSA,
                expected_from=_STATI_EDITABILI,
            )

    # Scopo: Se l'offerta ha un listino selezionato ma nessuna versione
    #        fissata, cerca la versione ATTIVA (o CHIUSA come fallback)
    #        del listino oggi e la persiste su `listino_versione_id`.
    #        Errore parlante se il listino esiste ma non ha versioni
    #        operative valide oggi. Idempotente: no-op se gia' fissata o
    #        offerta senza listino (caso quest'ultimo lasciato al trigger
    #        DB per coerenza con la sua signaling).
    def _fissa_versione_listino_se_necessario(self, offerta_id: int) -> None:
        offerta = self._repo.get_offerta(offerta_id)
        if offerta is None:
            return  # 404 verra' segnalato da `_cambia_stato_manuale`.
        if offerta.get("listino_versione_id") is not None:
            return
        listino_id = offerta.get("listino_id")
        if listino_id is None:
            return  # nessun listino: gestito dai check di stato del DB.
        today = timezone.localdate()
        versione_id = ListiniRepository().get_versione_attiva_alla_data(
            int(listino_id), today,
        )
        ErrorManager.require(
            versione_id is not None,
            code=E_VENDITE_VALIDATION,
            message=(
                "Il listino di riferimento non ha una versione attiva "
                "alla data odierna. Impossibile emettere l'offerta: "
                "pubblicare prima una versione del listino."
            ),
            context={
                "offerta_id": offerta_id,
                "listino_id": listino_id,
                "data": today.isoformat(),
            },
        )
        assert versione_id is not None
        self._repo.update_offerta(
            offerta_id, {"listino_versione_id": versione_id},
        )

    # Scopo: EMESSA -> ACCETTATA (esito cliente positivo). Il trigger DB
    #        valorizza `data_accettazione`.
    def registra_accettazione(self, offerta_id: int) -> dict[str, Any]:
        return self._cambia_stato_manuale(
            offerta_id,
            target_codice=StatoOfferta.ACCETTATA,
            expected_from=_STATI_DA_EMESSA,
        )

    # Scopo: EMESSA -> RIFIUTATA (esito cliente negativo). Motivazione
    #        obbligatoria. Il trigger DB valorizza `data_rifiuto` +
    #        `motivazione_rifiuto`.
    def registra_rifiuto(
        self, offerta_id: int, *, motivazione: str
    ) -> dict[str, Any]:
        self._v.guard_non_empty_string(motivazione, field="motivazione")
        return self._cambia_stato_manuale(
            offerta_id,
            target_codice=StatoOfferta.RIFIUTATA,
            expected_from=_STATI_DA_EMESSA,
            motivazione=motivazione.strip(),
        )

    # Scopo: Esito cliente unificato (ACCETTATA o RIFIUTATA, da EMESSA). La
    #        view si limita a passare il payload, il routing per esito vive
    #        qui — coerente con i due metodi specifici sopra (mantenuti per
    #        chi vuole l'API esplicita).
    def registra_esito(
        self, offerta_id: int, *, esito: str, motivazione: str | None = None
    ) -> dict[str, Any]:
        ErrorManager.require(
            esito in _ESITI_AMMESSI_DA_EMESSA,
            code=E_VENDITE_VALIDATION,
            message="Esito non valido.",
            detail=f"Atteso uno tra {sorted(_ESITI_AMMESSI_DA_EMESSA)}, ricevuto {esito!r}.",
            context={"offerta_id": offerta_id, "esito": esito},
        )
        if esito == StatoOfferta.ACCETTATA:
            return self.registra_accettazione(offerta_id)
        return self.registra_rifiuto(offerta_id, motivazione=motivazione or "")

    # Scopo: Crea rev.N+1 di un'offerta in stato EMESSA invocando la fn DB
    #        `vendite.fn_crea_revisione_offerta`. La fn copia testata +
    #        eccezioni attive + utility 1:1; il trigger DB
    #        `trg_offerte_commerciali_z90_revisione_ins` marca automaticamente
    #        la rev.N corrente come SUPERATA. Ritorna la nuova rev.N+1
    #        (BOZZA) come dettaglio completo.
    #
    #        Guard di stato (EMESSA obbligatorio) gia' nel DB con codice
    #        `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`; replichiamo lato
    #        applicativo per fail-fast con messaggio strutturato.
    def crea_revisione(
        self, offerta_id: int, *, user: str | None = None
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._assert_stato_corrente(offerta_id, expected=_STATI_DA_EMESSA)
        with self._db_errors(
            {"offerta_id": offerta_id},
            fallback_message="Errore creazione revisione offerta.",
        ):
            with transaction.atomic():
                new_id = self._repo.crea_revisione(offerta_id, user)
        return self.get_offerta(new_id)

    # Scopo: Push offerta ACCETTATA → contratto DRAFT (Step 8 brief DB,
    #        atterrato 2026-05-25). Pattern A idempotenza: la fn DB
    #        `fn_push_offerta_a_contratto` ha guard UNIQUE su
    #        `contratti.offerta_id` — doppia invocazione fallisce con
    #        `E_OFFERTA_CONTRATTO_GIA_GENERATO`. Pratica opzionale.
    #
    #        Ritorna `OffertaPushResult` con id+numero del nuovo contratto
    #        DRAFT e il `sorgente_uid` (= `offerta.uid`) per tracciabilita'.
    #
    #        Successione su overlap (brief successione 2026-05-31): se per la
    #        quintupla esiste gia' un contratto attivo sovrapposto, la fn DB
    #        solleva `E_CONTRATTO_OVERLAP_ESISTENTE` quando `chiudi_esistente`
    #        e' False (il FE intercetta il codice, mostra il contratto in
    #        conflitto via `get_contratto_sovrapposto` e ri-chiama con
    #        `chiudi_esistente=True`, che chiude il vecchio per successione).
    def push_a_contratto(
        self,
        offerta_id: int,
        *,
        pratica_id: int | None = None,
        chiudi_esistente: bool = False,
    ) -> OffertaPushResult:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        if pratica_id is not None:
            self._v.guard_positive_int(pratica_id, field="pratica_id")
        self._assert_stato_corrente(offerta_id, expected=_STATI_PUSHABILI)
        with self._db_errors(
            {
                "offerta_id": offerta_id,
                "pratica_id": pratica_id,
                "chiudi_esistente": chiudi_esistente,
            },
            fallback_message="Errore push offerta a contratto.",
        ):
            with transaction.atomic():
                contratto_id = self._repo.push_a_contratto(
                    offerta_id, pratica_id, chiudi_esistente,
                )
        # UX v2: la cascata DB copia gli indirizzi dell'offerta sul contratto;
        # fallback best-effort dall'anagrafica di ruolo se la sorgente non
        # aveva slot compatibili. Import locale per evitare cicli fra service.
        from apps.vendite.services.contratti_service import (
            auto_assegna_indirizzo_default_contratto,
        )
        auto_assegna_indirizzo_default_contratto(int(contratto_id))
        contratto = self._repo.get_contratto_minimal(contratto_id)
        ErrorManager.require(
            contratto is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto generato non leggibile post-push.",
            context={"contratto_id": contratto_id, "offerta_id": offerta_id},
        )
        assert contratto is not None
        return OffertaPushResult(
            contratto_id=int(contratto["id"]),
            contratto_codice=str(contratto["numero"]),
            sorgente_uid=str(contratto["uid"]),
        )

    # Scopo: Ritorna il contratto attivo la cui validita' si sovrappone a
    #        quella che il push genererebbe per questa offerta, o None.
    #        Lettura libera (read-only): alimenta il dialog FE di successione
    #        quando il push ha restituito `E_CONTRATTO_OVERLAP_ESISTENTE`.
    #        Delega a `fn_contratto_sovrapposto` (dominio contratti) via repo.
    def get_contratto_sovrapposto(
        self, offerta_id: int
    ) -> dict[str, Any] | None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._get_offerta_or_raise(offerta_id, op="get_contratto_sovrapposto", getter=self._repo.get_stato_codice)
        return self._repo.get_contratto_sovrapposto(offerta_id)

    # Scopo: Ritorna la catena di revisioni che condivide il root (rev.1)
    #        con l'offerta passata. Lettura libera in ogni stato.
    def list_revisioni(self, offerta_id: int) -> list[dict[str, Any]]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        # 404 esplicito se l'offerta non esiste.
        self._get_offerta_or_raise(offerta_id, op="list_revisioni", getter=self._repo.get_stato_codice)
        return self._repo.list_revisioni(offerta_id)

    # Scopo: BOZZA -> ANNULLATA (ritiro interno prima dell'emissione).
    #        Motivazione obbligatoria. Pattern simmetrico al contratto
    #        "annulla DRAFT". Il trigger DB valorizza `data_annullamento` +
    #        `motivazione_rifiuto`.
    def annulla(self, offerta_id: int, *, motivazione: str) -> dict[str, Any]:
        self._v.guard_non_empty_string(motivazione, field="motivazione")
        return self._cambia_stato_manuale(
            offerta_id,
            target_codice=StatoOfferta.ANNULLATA,
            expected_from=_STATI_EDITABILI,
            motivazione=motivazione.strip(),
        )

    # =================================================================
    # CRUD eccezioni (solo in BOZZA)
    # =================================================================

    # Scopo: Lista eccezioni di un'offerta (qualsiasi stato — la lettura
    #        non e' bloccata; il guard BOZZA si applica solo in scrittura).
    def list_eccezioni(self, offerta_id: int) -> list[dict[str, Any]]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        # Verifica esistenza offerta per 404 esplicito.
        self._get_offerta_or_raise(offerta_id, op="list_eccezioni", getter=self._repo.get_stato_codice)
        return self._repo.list_eccezioni(offerta_id)

    # Scopo: Crea un'eccezione. Solo in stato BOZZA.
    def crea_eccezione(
        self,
        offerta_id: int,
        payload: dict[str, Any],
        *,
        auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS_ECCEZIONE)
        payload = self._con_meta_normalizzato(payload)
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        for required in ("articolo_id", "tipo_eccezione", "fonte_quantita_attesa"):
            ErrorManager.require(
                required in payload and payload[required] not in (None, ""),
                code=E_VENDITE_VALIDATION,
                message=f"Campo '{required}' obbligatorio.",
                context={"field": required},
            )

        # Gate L1 override prezzo componenti (BB condiviso, 2026-06-01): se il
        # payload porta `componenti_overrides` l'operatore deve avere l'azione
        # `prezzo_override_manuale`. Prima del pop (il payload li contiene ancora).
        validate_componenti_overrides_authorization(
            payload, auth_user_id, function_name="offerte_service.crea_eccezione",
        )
        # Flag opt-in workflow L3. Estratto qui per non finire nel payload INSERT.
        richiesta_approvazione = bool(payload.pop("richiesta_approvazione", False))

        # Estrae overrides BoM prima di passare il payload al repo (la colonna
        # non esiste su `offerte_commerciali_eccezioni`); normalizza valori.
        overrides_raw = payload.pop("componenti_overrides", None)
        componenti_overrides = normalize_componenti_overrides(
            overrides_raw,
            function_name="offerte_service.crea_eccezione",
            error_code=E_VENDITE_VALIDATION,
        )

        articolo_id = payload.get("articolo_id")
        # Pre-check articolo composito (cache locale per non chiamare 2 volte
        # il repo nel ramo INSERT + init componenti). Usato sia per il guard
        # `prezzo_unitario = None` sotto, sia per l'auto-init componenti.
        is_composito = bool(
            articolo_id
            and self._repo.is_articolo_composito(str(articolo_id)),
        )

        # Coerenza prezzo_unitario / tipo_eccezione (pre-DB, specchio CHECK
        # `chk_offerte_eccezioni_prezzo_per_tipo_eccezione`):
        # - ESCLUSIONE -> prezzo NULL (l'articolo non e' disponibile)
        # - OVERRIDE / AGGIUNTA -> prezzo NOT NULL (e' il prezzo finale)
        # Eccezione: articolo composito (modello unificato BoM). Il FE puo'
        # omettere `prezzo_unitario` per padri compositi perche' il prezzo
        # padre = SUM(figli × coeff_qta) calcolato dal trigger DB
        # `_z90_ricalcola_padre` post-init componenti BoM nello stesso
        # `transaction.atomic`. Settiamo `Decimal(0)` come placeholder per
        # superare il CHECK; il trigger lo sovrascrive sincrono dopo INSERT
        # padre + INSERT figli. Pattern simmetrico ai contratti (cfr.
        # `contratti_service` ~ linea 2114 "Padre composito").
        tipo_eccezione = payload.get("tipo_eccezione")
        prezzo_raw = payload.get("prezzo_unitario")
        if tipo_eccezione == "ESCLUSIONE":
            ErrorManager.require(
                prezzo_raw is None,
                code=E_VENDITE_VALIDATION,
                message=(
                    "ESCLUSIONE: prezzo_unitario deve essere NULL "
                    "(l'articolo non e' disponibile per questa offerta)."
                ),
                context={"tipo_eccezione": tipo_eccezione},
            )
        elif prezzo_raw is None and tipo_eccezione in ("OVERRIDE", "AGGIUNTA"):
            ErrorManager.require(
                is_composito,
                code=E_VENDITE_VALIDATION,
                message=(
                    f"{tipo_eccezione}: prezzo_unitario obbligatorio "
                    "per articoli non compositi."
                ),
                context={"tipo_eccezione": tipo_eccezione},
            )
            # Placeholder: il trigger DB lo sovrascrive a SUM(componenti).
            payload = {**payload, "prezzo_unitario": Decimal("0")}

        # Gate prezzo L1+L2+L3 su OVERRIDE/AGGIUNTA NON compositi: il prezzo
        # composito e' derivato (SUM figli) → nessun confronto col resolver.
        # `testata_gate` riusato dal ramo composito sotto (1 round-trip in meno).
        pratica_id_l3: int | None = None
        testata_gate: dict[str, Any] | None = None
        # Fix analisi-fix-transazioni #8 (Classe B): il gate L3 (crea la pratica
        # di approvazione) vive DENTRO transaction.atomic() insieme alla create
        # eccezione. Prima era invocato PRIMA dell'atomic → pratica orfana se la
        # create eccezione rollava. Il gate fa permission-check L1/L2 in Python
        # (azioni di processo): resta orchestrazione BE, non funzione madre DB.
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                if tipo_eccezione in _TIPI_ECCEZIONE_CON_GATE and not is_composito:
                    pratica_id_l3, testata_gate = self._apply_pricing_gate_eccezione(
                        offerta_id=offerta_id,
                        articolo_id=articolo_id,
                        uom_id=payload.get("uom_operativa_id"),
                        payload=payload,
                        auth_user_id=auth_user_id,
                        richiesta_approvazione=richiesta_approvazione,
                        riga_id_for_link=None,  # eccezione_id non noto qui
                    )
                eccezione_id = self._repo.create_eccezione(offerta_id, payload)
                # Link riga<->pratica L3: post-create, eccezione_id ora noto.
                if pratica_id_l3 is not None:
                    from apps.vendite.services.approvazioni_prezzo_service import (
                        link_riga_a_pratica,
                    )
                    link_riga_a_pratica(
                        pratica_id=pratica_id_l3,
                        riga_id=eccezione_id,
                        sorgente=SORGENTE_OFFERTA,
                    )
                # Auto-init componenti BoM su articolo composito (mirror del
                # flow contratti: la fn DB e' idempotente, no-op se gia'
                # presenti o articolo non composito).
                # ESCLUSIONE escluso: un articolo escluso non ha prezzo
                # (CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione impone
                # prezzo_unitario NULL) ne' senso di negoziare i suoi componenti.
                # Inizializzarli farebbe scattare trgfn_componenti_ricalcola_padre
                # che scriverebbe SUM(figli) sul padre ESCLUSIONE -> violazione.
                if is_composito and tipo_eccezione != "ESCLUSIONE":
                    testata = testata_gate or self._repo.get_offerta(offerta_id) or {}
                    emittente_sr_id = self._resolve_emittente_sr_id_for_offerta(
                        offerta_id=offerta_id,
                        testata=testata,
                        auth_user_id=auth_user_id,
                        function_name="offerte_service.crea_eccezione",
                    )
                    self._repo.init_componenti_eccezione(
                        eccezione_id=eccezione_id,
                        emittente_soggetto_ruolo_id=emittente_sr_id,
                        data_riferimento=testata.get("validita_dal"),
                        componenti_overrides=componenti_overrides,
                    )
        row = self._repo.get_eccezione(eccezione_id)
        assert row is not None
        return row

    # Scopo: Aggiorna un'eccezione. Solo se offerta in BOZZA. Payload vuoto
    #        -> 400 (no-op silenzioso evitato). Se il PATCH tocca
    #        `prezzo_unitario` su una eccezione OVERRIDE/AGGIUNTA non composita,
    #        applica il gate L1/L2/L3 (mirror di `contratti_service.update_riga`).
    def aggiorna_eccezione(
        self, offerta_id: int, eccezione_id: int, payload: dict[str, Any],
        *, auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS_ECCEZIONE)
        payload = self._con_meta_normalizzato(payload)
        # Flag opt-in workflow L3 (estratto prima del guard non-vuoto: non e' un
        # campo di update di per se').
        richiesta_approvazione = bool(payload.pop("richiesta_approvazione", False))
        self._guard_payload_non_vuoto(payload, op="aggiorna_eccezione")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        existing = self._repo.get_eccezione(eccezione_id)
        ErrorManager.require(
            existing is not None and existing.get("offerta_id") == offerta_id,
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione non trovata o non appartenente all'offerta.",
            context={"offerta_id": offerta_id, "eccezione_id": eccezione_id},
        )
        assert existing is not None
        # Gate prezzo L1+L2+L3 quando il PATCH tocca `prezzo_unitario` su
        # OVERRIDE/AGGIUNTA non composito. Il prezzo composito e' derivato →
        # nessun gate (i componenti hanno il proprio workflow). `articolo_id` e
        # `tipo_eccezione` sono immutabili → letti dalla riga esistente.
        tipo_existing = existing.get("tipo_eccezione")
        # Fix analisi-fix-transazioni #9 (Classe B): il gate L3 (crea + linka
        # inline la pratica di approvazione) vive DENTRO transaction.atomic()
        # insieme all'UPDATE eccezione. Prima era invocato PRIMA dell'atomic →
        # pratica orfana se l'UPDATE rollava. Il gate fa permission-check L1/L2
        # in Python (azioni di processo): resta orchestrazione BE, non fn madre DB.
        with self._db_errors({"eccezione_id": eccezione_id}):
            with transaction.atomic():
                if (
                    tipo_existing in _TIPI_ECCEZIONE_CON_GATE
                    and not bool(existing.get("is_composito"))
                    and "prezzo_unitario" in payload
                ):
                    self._apply_pricing_gate_eccezione(
                        offerta_id=offerta_id,
                        articolo_id=existing.get("articolo_id"),
                        uom_id=payload.get("uom_operativa_id") or existing.get("uom_operativa_id"),
                        payload=payload,
                        auth_user_id=auth_user_id,
                        richiesta_approvazione=richiesta_approvazione,
                        riga_id_for_link=eccezione_id,  # noto: link inline
                        # Preserva il meta persistito (audit/altre chiavi): senza,
                        # l'UPDATE prezzo lo sovrascriverebbe col solo audit nuovo.
                        fallback_meta=existing.get("meta"),
                    )
                self._repo.update_eccezione(eccezione_id, payload)
        row = self._repo.get_eccezione(eccezione_id)
        assert row is not None
        return row

    # Scopo: Helper unificato gate L1+L2+L3 su eccezione offerta. Mirror di
    #        `contratti_service._apply_pricing_gate_riga`. Muta `payload`
    #        (prezzo_unitario normalizzato, merge meta audit, e — se workflow L3
    #        attivo — stato_approvazione_prezzo=PENDING + pratica id). Orchestra
    #        la pratica L3 quando il prezzo viola L2 e `richiesta_approvazione`
    #        e' true. Ritorna `(pratica_id_l3 | None, testata_gate)` (testata
    #        riusata dal caller per il ramo composito → no double-fetch).
    def _apply_pricing_gate_eccezione(
        self,
        *,
        offerta_id: int,
        articolo_id: Any,
        uom_id: Any,
        payload: dict[str, Any],
        auth_user_id: int | None,
        richiesta_approvazione: bool,
        riga_id_for_link: int | None,
        fallback_meta: dict[str, Any] | None = None,
    ) -> tuple[int | None, dict[str, Any]]:
        testata_gate = self._repo.get_offerta(offerta_id)
        assert testata_gate is not None
        prezzo_finale, prezzo_meta = resolve_or_check_override_prezzo_riga_offerta(
            testata=testata_gate,
            articolo_id=articolo_id,
            uom_id=uom_id,
            payload_prezzo=payload.get("prezzo_unitario"),
            auth_user_id=auth_user_id,
            function_name="offerte_service._apply_pricing_gate_eccezione",
            richiesta_approvazione=richiesta_approvazione,
        )
        if prezzo_finale is not None:
            payload["prezzo_unitario"] = prezzo_finale
        if prezzo_meta:
            # Merge audit pricing sul meta corrente. Priorita': payload.meta >
            # `fallback_meta` (meta della riga esistente, case update) > {}.
            # Senza fallback, un UPDATE che tocca il prezzo (payload senza meta)
            # sovrascriverebbe il meta persistito perdendo le chiavi precedenti.
            base_meta = payload.get("meta") or fallback_meta or {}
            # Coerce JSONB→dict difensivo (mirror contratti): il meta puo'
            # arrivare come stringa JSON da certi path repo.
            if isinstance(base_meta, str):
                try:
                    parsed = json.loads(base_meta)
                    base_meta = parsed if isinstance(parsed, dict) else {}
                except (json.JSONDecodeError, ValueError):
                    base_meta = {}
            merged_meta = dict(base_meta)
            merged_meta.update(prezzo_meta)
            payload["meta"] = merged_meta
        pratica_id_l3: int | None = None
        if prezzo_meta and prezzo_meta.get("richiesta_approvazione_pending"):
            pratica_id_l3 = _orchestrate_l3_request_offerta(
                offerta_id=offerta_id,
                articolo_id=articolo_id,
                prezzo_finale=prezzo_finale,
                prezzo_meta=prezzo_meta,
                auth_user_id=auth_user_id,
                riga_id_for_link=riga_id_for_link,
            )
            payload["stato_approvazione_prezzo"] = STATO_APPROVAZIONE_PENDING
            payload["pratica_approvazione_prezzo_id"] = pratica_id_l3
        return pratica_id_l3, testata_gate

    # =================================================================
    # Componenti BoM su eccezione (mirror contratti, simmetria 2026-05-26)
    # =================================================================

    # Scopo: Preview componenti BoM PRIMA del save eccezione (ComponentiDialog
    # FE). Read-only, nessun side-effect. Risolve emittente da testata >
    # operatore. Mirror di `ContrattiService.preview_componenti_riga`.
    def preview_componenti_eccezione(
        self,
        offerta_id: int,
        *,
        articolo_id: str,
        uom_operativa_id: int | None,
        quantita: Any,
        auth_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        testata = self._get_offerta_or_raise(offerta_id, op="preview_componenti_eccezione")
        emittente_sr_id = self._resolve_emittente_sr_id_for_offerta(
            offerta_id=offerta_id,
            testata=testata,
            auth_user_id=auth_user_id,
            function_name="offerte_service.preview_componenti_eccezione",
        )
        # `utility_id` NOT NULL su DDL: guard parlante prima del cast per
        # evitare TypeError criptici in caso di dato malformato (test/dev).
        utility_id_raw = testata.get("utility_id")
        ErrorManager.require(
            utility_id_raw is not None,
            code=E_VENDITE_VALIDATION,
            message="Offerta senza utility_id: impossibile risolvere il pricing.",
            context={"offerta_id": offerta_id},
        )
        return self._repo.preview_componenti_eccezione(
            articolo_id=str(articolo_id),
            uom_id=uom_operativa_id,
            quantita_padre=quantita,
            data_riferimento=testata.get("validita_dal"),
            ba_id=testata.get("billing_account_id"),
            utility_id=int(utility_id_raw),
            emittente_soggetto_ruolo_id=emittente_sr_id,
        )

    # Scopo: Helper unificato risoluzione emittente_sr_id per le operazioni
    # componenti BoM dell'offerta. Precedenza: testata > operatore. Solleva
    # E_VENDITE_VALIDATION se nessuna fonte (admin globale + testata senza
    # emittente_fiscale_id). Centralizza il pattern riusato da
    # `crea_eccezione` e `preview_componenti_eccezione`.
    def _resolve_emittente_sr_id_for_offerta(
        self,
        *,
        offerta_id: int,
        testata: dict[str, Any],
        auth_user_id: int | None,
        function_name: str,
    ) -> int:
        emittente_sr_id = resolve_emittente_sr_id_for_testata(
            testata, auth_user_id,
            repo_get_sr_id_by_fiscale_id=self._repo.get_emittente_sr_id_by_fiscale_id,
        )
        ErrorManager.require(
            emittente_sr_id is not None,
            code=E_VENDITE_VALIDATION,
            message=(
                "Operazione componenti BoM richiede emittente fiscale "
                "risolvibile (testata o utente)."
            ),
            context={"offerta_id": offerta_id},
            function_name=function_name,
        )
        assert emittente_sr_id is not None
        return emittente_sr_id

    # Scopo: Lista componenti BoM persistiti su eccezione composita. Guard
    # esistenza eccezione + match URL anti-tampering (eccezione_id deve
    # appartenere all'offerta_id richiesto).
    def list_componenti_eccezione(
        self,
        offerta_id: int, eccezione_id: int,
        *, solo_attivi: bool = True,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        eccezione = self._repo.get_eccezione(eccezione_id)
        ErrorManager.require(
            eccezione is not None
            and int(eccezione.get("offerta_id") or 0) == offerta_id,
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione offerta non trovata.",
            context={"offerta_id": offerta_id, "eccezione_id": eccezione_id},
        )
        return self._repo.list_componenti_riga(eccezione_id, solo_attivi=solo_attivi)

    # Scopo: Modifica componente BoM eccezione esistente. Whitelist colonne via
    # repo mixin. Guard stato offerta editabile + esistenza componente +
    # match URL.
    def update_componente_eccezione(
        self,
        offerta_id: int, eccezione_id: int, componente_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        self._v.guard_positive_int(componente_id, field="componente_id")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        self._load_componente_for_modification(
            offerta_id=offerta_id, eccezione_id=eccezione_id,
            componente_id=componente_id,
        )
        # ⛔ Contratto dell'OPERATORE (BB unico per i cinque documenti), non
        #    la whitelist del repository: fino al 2026-09-26 qui si validava
        #    contro `COMPONENTE_UPDATE_ALLOWED`, che contiene
        #    `stato_approvazione_prezzo` — un operatore poteva approvarsi da
        #    solo un prezzo L3 PENDING. `origine_prezzo` la deriva il server.
        payload = dati_patch_componente(
            payload,
            function_name="offerte_service.update_componente_eccezione",
        )
        with self._db_errors(
            {"componente_id": componente_id, "eccezione_id": eccezione_id},
            fallback_message=(
                "Violazione vincolo DB su componente eccezione offerta."
            ),
        ):
            updated = self._repo.update_componente(componente_id, **payload)
        ErrorManager.require(
            updated,
            code=E_VENDITE_VALIDATION,
            message="Nessun campo aggiornato sul componente.",
            detail="Payload vuoto o senza campi nella whitelist.",
        )
        return {"status": "ok", "componente_id": componente_id}

    # Scopo: Soft delete componente BoM eccezione (`attivo=FALSE`). Il trigger
    # DB di ricalcolo padre esclude i componenti inattivi dalla SUM.
    def delete_componente_eccezione(
        self,
        offerta_id: int, eccezione_id: int, componente_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        self._v.guard_positive_int(componente_id, field="componente_id")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        self._load_componente_for_modification(
            offerta_id=offerta_id, eccezione_id=eccezione_id,
            componente_id=componente_id,
        )
        with self._db_errors(
            {"componente_id": componente_id, "eccezione_id": eccezione_id},
            fallback_message="Impossibile eliminare il componente (dipendenze).",
        ):
            deleted = self._repo.delete_componente(componente_id)
        return {
            "status": "ok",
            "componente_id": componente_id,
            "deleted": deleted,
        }

    # Scopo: Lookup componente + verifica appartenenza eccezione/offerta.
    # Centralizza guard URL anti-tampering riusato da update/delete componente.
    def _load_componente_for_modification(
        self,
        *,
        offerta_id: int,
        eccezione_id: int,
        componente_id: int,
    ) -> dict[str, Any]:
        eccezione = self._repo.get_eccezione(eccezione_id)
        ErrorManager.require(
            eccezione is not None
            and int(eccezione.get("offerta_id") or 0) == offerta_id,
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione offerta non trovata.",
            context={"offerta_id": offerta_id, "eccezione_id": eccezione_id},
        )
        componente = self._repo.get_componente(componente_id)
        ErrorManager.require(
            componente is not None
            and int(componente.get("eccezione_offerta_id") or 0) == eccezione_id,
            code=E_VENDITE_NOT_FOUND,
            message="Componente non trovato sull'eccezione.",
            context={
                "eccezione_id": eccezione_id,
                "componente_id": componente_id,
            },
        )
        assert componente is not None
        return componente

    # Scopo: Cancella un'eccezione. Solo se offerta in BOZZA.
    def elimina_eccezione(self, offerta_id: int, eccezione_id: int) -> None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        existing = self._repo.get_eccezione(eccezione_id)
        ErrorManager.require(
            existing is not None and existing.get("offerta_id") == offerta_id,
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione non trovata o non appartenente all'offerta.",
            context={"offerta_id": offerta_id, "eccezione_id": eccezione_id},
        )
        with self._db_errors({"eccezione_id": eccezione_id}):
            with transaction.atomic():
                self._repo.delete_eccezione(eccezione_id)

    # =================================================================
    # Utility 1:1 (solo in BOZZA per write)
    # =================================================================

    # Scopo: Legge il record utility 1:1 di un'offerta (read libero).
    def get_utility(self, offerta_id: int) -> dict[str, Any] | None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._get_offerta_or_raise(offerta_id, op="get_utility", getter=self._repo.get_stato_codice)
        return self._repo.get_utility(offerta_id)

    # Scopo: Crea il record utility 1:1. UNIQUE su offerta_id: doppio create
    #        rilevato e mappato a E_VENDITE_DUPLICATO. Solo in BOZZA.
    def crea_utility(
        self, offerta_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS_UTILITY)
        payload = self._con_meta_normalizzato(payload)
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        for required in ("istanza_utility_id", "utility_id"):
            ErrorManager.require(
                required in payload and payload[required] is not None,
                code=E_VENDITE_VALIDATION,
                message=f"Campo '{required}' obbligatorio.",
                context={"field": required},
            )
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                self._repo.create_utility(offerta_id, payload)
        row = self._repo.get_utility(offerta_id)
        assert row is not None
        return row

    # Scopo: Aggiorna il record utility (campi business). Solo in BOZZA.
    #        Payload vuoto -> 400 (no-op silenzioso evitato).
    def aggiorna_utility(
        self, offerta_id: int, utility_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(utility_id, field="utility_id")
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS_UTILITY)
        payload = self._con_meta_normalizzato(payload)
        self._guard_payload_non_vuoto(payload, op="aggiorna_utility")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        existing = self._repo.get_utility(offerta_id)
        ErrorManager.require(
            existing is not None and existing.get("id") == utility_id,
            code=E_VENDITE_NOT_FOUND,
            message="Record utility non trovato per questa offerta.",
            context={"offerta_id": offerta_id, "utility_id": utility_id},
        )
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                self._repo.update_utility(utility_id, payload)
        row = self._repo.get_utility(offerta_id)
        assert row is not None
        return row

    # =================================================================
    # Helper interni
    # =================================================================

    # Scopo: Fail-fast su payload vuoto in update. Senza questo guard, il
    #        repository ritorna False senza errori, ma il service restituisce
    #        comunque `get_offerta(...)` — l'operatore vedrebbe un "successo"
    #        ingannevole sul tasto Salva quando in realta' non e' stato
    #        scritto nulla.
    # Scopo: Normalizza `meta` (se presente) con il BB `optional_meta`:
    #        oggetto JSON (dict, o stringa che ne contiene uno) -> dict,
    #        `null` -> `{}`, qualunque altra cosa -> 400 E_VENDITE_VALIDATION.
    #        Ritorna una COPIA del payload (il chiamante non vede la mutazione).
    # ⭐ 2026-09-26, migrazione delle scritture sul BB core. Fino a quel giorno
    #    il `meta` del client arrivava al repository COSI' COM'ERA e
    #    `to_write_param` lo passava a `json.dumps`: una stringa diventava uno
    #    SCALARE stringa jsonb, un numero un numero — su una colonna che il
    #    modello vuole oggetto (`NOT NULL DEFAULT '{}'` su tutte e tre le
    #    tabelle), e che il gate prezzo rilegge come dict. E `null` arrivava
    #    come NULL contro il NOT NULL (errore DB generico). Ora la regola e'
    #    quella di contratti/promo: un oggetto o un 400 parlante, `null` =
    #    reset a `{}`.
    def _con_meta_normalizzato(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "meta" not in payload:
            return payload
        return {**payload, "meta": self._v.optional_meta(payload)}

    def _guard_payload_non_vuoto(
        self, payload: dict[str, Any], *, op: str
    ) -> None:
        ErrorManager.require(
            bool(payload),
            code=E_VENDITE_VALIDATION,
            message="Nessun campo da aggiornare.",
            detail=f"Operazione {op}: il payload e' vuoto.",
            context={"op": op},
        )

    # Scopo: Verifica che l'offerta esista e sia in uno degli stati attesi.
    #        Solleva 404 se offerta inesistente, 422 se stato fuori scope.
    def _assert_stato_corrente(
        self, offerta_id: int, *, expected: set[str] | frozenset[str]
    ) -> str:
        stato = self._get_offerta_or_raise(offerta_id, op="_assert_stato_corrente", getter=self._repo.get_stato_codice)
        ErrorManager.require(
            stato in expected,
            code=E_VENDITE_VALIDATION,
            message=(
                "Operazione non consentita: stato corrente "
                f"'{stato}', atteso uno tra {sorted(expected)}."
            ),
            context={
                "offerta_id": offerta_id,
                "stato_corrente": stato,
                "stati_attesi": sorted(expected),
            },
        )
        return stato

    # Scopo: Esegue una transizione di stato manuale. Il guard pre-condizione
    #        (`expected_from`) e' difesa applicativa; il trigger DB rifinisce
    #        ulteriormente (es. BOZZA->EMESSA fallisce se listino_versione_id
    #        NULL o versione non ATTIVA).
    def _cambia_stato_manuale(
        self,
        offerta_id: int,
        *,
        target_codice: str,
        expected_from: set[str] | frozenset[str],
        motivazione: str | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._assert_stato_corrente(offerta_id, expected=expected_from)
        target_stato_id = self._repo.get_stato_id_by_codice(target_codice)
        ErrorManager.require(
            target_stato_id is not None,
            code=E_VENDITE_VALIDATION,
            message=f"Stato '{target_codice}' non configurato.",
            context={"target_codice": target_codice},
        )
        assert target_stato_id is not None
        with self._db_errors(
            {"offerta_id": offerta_id, "target_codice": target_codice},
            fallback_message="Cambio stato offerta non consentito.",
        ):
            with transaction.atomic():
                self._repo.update_stato(
                    offerta_id,
                    target_stato_id,
                    motivazione_rifiuto=motivazione,
                )
        return self.get_offerta(offerta_id)


# ══════════════════════════════════════════════════════════
# Pricing riga offerta + gate L1/L2/L3 (module-level)
# ══════════════════════════════════════════════════════════
# Speculari a `contratti_service.contratti_suggerisci_prezzo_riga` +
# `resolve_or_check_override_prezzo_riga_contratto` (refactor 2026-06-01: gate
# prezzi sulle offerte, simmetria col contratto). Esposte module-level perche'
# `resolver_fn` del BB `_pricing_gate_helpers.resolve_or_check_override_prezzo`
# attende la signature `(documento_id, *, articolo_id, uom_id, auth_user_id)`.


# Scopo: Risolve il contesto di pricing per un'offerta: testata + emittente +
#        BA/utility/data + listino_versione preferita. Mirror di
#        `contratti_service._load_contratto_context_for_pricing` (offerta usa
#        `validita_dal` come data di riferimento e `codice` come numero doc).
def _load_offerta_context_for_pricing(
    offerta_id: int,
    auth_user_id: int | None,
    *,
    function_name: str,
    repo: OfferteRepository | None = None,
) -> dict[str, Any]:
    if repo is None:
        repo = OfferteRepository()
    testata = testata_o_not_found(
        repo.get_offerta, offerta_id,
        code=E_VENDITE_NOT_FOUND, message="Offerta non trovata.",
        id_name="offerta_id", function_name=function_name,
    )

    ba_id_raw = testata.get("billing_account_id")
    ErrorManager.require(
        ba_id_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Offerta senza billing_account: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    utility_id_raw = testata.get("utility_id")
    ErrorManager.require(
        utility_id_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Offerta senza utility: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    validita_dal_raw = testata.get("validita_dal")
    ErrorManager.require(
        validita_dal_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Offerta senza validita_dal: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    assert validita_dal_raw is not None
    data_riferimento = (
        validita_dal_raw if isinstance(validita_dal_raw, date)
        else date.fromisoformat(str(validita_dal_raw))
    )

    emittente_sr_id = resolve_emittente_sr_id_for_testata(
        testata, auth_user_id,
        repo_get_sr_id_by_fiscale_id=repo.get_emittente_sr_id_by_fiscale_id,
    )
    ErrorManager.require(
        emittente_sr_id is not None,
        code=E_VENDITE_VALIDATION,
        message="Impossibile risolvere l'emittente fiscale per il pricing.",
        function_name=function_name,
    )
    assert emittente_sr_id is not None

    # Fast path CONTRATTO_LISTINO via `listino_versione_id_preferito` (come
    # contratti). In BOZZA la versione e' fissata solo all'emissione → se NULL,
    # lookup dinamico della versione operativa alla data (ATTIVA/CHIUSA).
    listino_versione_id_preferito = testata.get("listino_versione_id")
    if listino_versione_id_preferito is None:
        listino_id_raw = testata.get("listino_id")
        if listino_id_raw is not None:
            listino_versione_id_preferito = ListiniRepository().get_versione_attiva_alla_data(
                int(listino_id_raw), data_riferimento,
            )

    return {
        "testata": testata,
        "ba_id": int(ba_id_raw),
        "utility_id": int(utility_id_raw),
        "emittente_sr_id": emittente_sr_id,
        "data_riferimento": data_riferimento,
        "listino_versione_id_preferito": listino_versione_id_preferito,
    }


# Scopo: Suggerisce il prezzo unitario per una riga (eccezione) offerta.
#        `resolver_fn` per il BB gate. Mirror di
#        `contratti_suggerisci_prezzo_riga`.
def offerta_suggerisci_prezzo_riga(
    offerta_id: int,
    *,
    articolo_id: str,
    uom_id: int,
    auth_user_id: int | None,
) -> dict[str, Any]:
    from apps.vendite.services.pricing_service import PricingService

    function_name = "offerte_service.offerta_suggerisci_prezzo_riga"
    ErrorManager.require(
        articolo_id is not None and str(articolo_id).strip() != "",
        code=E_VENDITE_VALIDATION,
        message="articolo_id obbligatorio.",
        function_name=function_name,
    )
    guard_uom_id_positive(
        uom_id, error_code=E_VENDITE_VALIDATION, function_name=function_name,
    )

    ctx = _load_offerta_context_for_pricing(
        offerta_id, auth_user_id, function_name=function_name,
    )

    result = PricingService().resolve_prezzo(
        articolo_id=str(articolo_id),
        uom_id=int(uom_id),
        data_riferimento=ctx["data_riferimento"],
        ba_id=ctx["ba_id"],
        utility_id=ctx["utility_id"],
        emittente_soggetto_ruolo_id=ctx["emittente_sr_id"],
        listino_versione_id_preferito=ctx["listino_versione_id_preferito"],
    )

    # Normalizzazione Decimal/date → string per stabilita' JSON (coerente
    # con contratti/preventivi).
    def _normalize(v: Any) -> Any:
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, date):
            return v.isoformat()
        return v

    return {k: _normalize(v) for k, v in result.items()}


# Scopo: Thin wrapper sul BB `resolve_or_check_override_prezzo` per le eccezioni
#        offerta. Mirror di `resolve_or_check_override_prezzo_riga_contratto`.
#        Normalizza la testata aliasando `data`←`validita_dal` (il BB usa
#        `testata["data"]` nel guard skip-context). Skip gate se l'offerta
#        e' senza listino (per coerenza col contratto, anche se sull'offerta
#        `listino_id` e' obbligatorio).
def resolve_or_check_override_prezzo_riga_offerta(
    *,
    testata: dict[str, Any],
    articolo_id: Any,
    uom_id: Any,
    payload_prezzo: Any,
    auth_user_id: int | None,
    function_name: str,
    richiesta_approvazione: bool = False,
) -> tuple[Any, dict[str, Any] | None]:
    if testata.get("listino_id") is None:
        return payload_prezzo, None

    testata_normalized = (
        testata if testata.get("data") is not None
        else {**testata, "data": testata.get("validita_dal")}
    )
    return resolve_or_check_override_prezzo(
        testata=testata_normalized,
        articolo_id=articolo_id,
        uom_id=uom_id,
        payload_prezzo=payload_prezzo,
        auth_user_id=auth_user_id,
        function_name=function_name,
        resolver_fn=offerta_suggerisci_prezzo_riga,
        error_code_validazione=E_VENDITE_VALIDATION,
        richiesta_approvazione=richiesta_approvazione,
    )


# Scopo: orchestratore L3 per le eccezioni offerta. Mirror di
#        `contratti_service._orchestrate_l3_request_contratto`. Crea la pratica
#        APPROVAZIONE_PREZZO via `crea_richiesta_approvazione_offerta`,
#        opzionalmente collega riga_id (update: noto subito; create: link
#        post-INSERT). Ritorna pratica_id.
def _orchestrate_l3_request_offerta(
    *,
    offerta_id: int,
    articolo_id: Any,
    prezzo_finale: Any,
    prezzo_meta: dict[str, Any],
    auth_user_id: int | None,
    riga_id_for_link: int | None = None,
) -> int:
    from apps.vendite.services.approvazioni_prezzo_service import (
        crea_richiesta_approvazione_offerta,
        link_riga_a_pratica,
    )
    pratica_id = crea_richiesta_approvazione_offerta(
        offerta_id=offerta_id,
        riga_id=riga_id_for_link,
        articolo_id=str(articolo_id) if articolo_id is not None else "",
        prezzo_resolver=Decimal(prezzo_meta["prezzo_base_resolver"])
        if prezzo_meta.get("prezzo_base_resolver") else None,
        prezzo_manuale=Decimal(str(prezzo_finale)),
        violazione=prezzo_meta["violazione_l2"],
        auth_user_id=auth_user_id,
    )
    if riga_id_for_link is not None:
        link_riga_a_pratica(
            pratica_id=pratica_id,
            riga_id=riga_id_for_link,
            sorgente=SORGENTE_OFFERTA,
        )
    return pratica_id


# ══════════════════════════════════════════════════════════
#  Indirizzi documento (BB condiviso _indirizzi_documento_helpers)
# ══════════════════════════════════════════════════════════

_INDIRIZZI_CFG = IndirizziDocumentoConfig(
    # lambda (non la classe): risolve il nome a call-time, cosi' i @patch
    # dei test unit raggiungono anche il ramo auto-assegnazione.
    repo_factory=lambda: OfferteRepository(),
    stati_modificabili=_STATI_EDITABILI,
    not_found_code=E_VENDITE_NOT_FOUND,
    stato_error_code=E_VENDITE_VALIDATION,
    error_code=E_VENDITE_VALIDATION,
    fn_prefix="vendite.offerte_service",
)


# Scopo: Pannello indirizzi dell'offerta (ambito OFFERTE). Guard, ownership e
#        traduzione errori DB nel BB condiviso.
def list_indirizzi(offerta_id: int) -> dict[str, Any]:
    return list_indirizzi_documento(_INDIRIZZI_CFG, offerta_id)


# Scopo: Upsert slot indirizzo (uno-per-tipo, solo BOZZA).
def upsert_indirizzo(offerta_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return upsert_indirizzo_documento(_INDIRIZZI_CFG, offerta_id, payload)


# Scopo: Rimozione slot indirizzo (solo BOZZA).
def delete_indirizzo(offerta_id: int, indirizzo_id: int) -> dict[str, Any]:
    return delete_indirizzo_documento(_INDIRIZZI_CFG, offerta_id, indirizzo_id)
