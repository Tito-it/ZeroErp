# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per preventivi vendita (CRUD, stato, righe, integrazione).
# ------------------------------------------------------------

# Orchestrazione preventivi vendita: validazione, guard su stato,
# delega a repository per accesso DB, gestione transizioni e integrazione
# con commesse e pratiche.

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import IntegrityError, transaction

from apps.config.sorgenti import SORGENTE_COMMESSA, SORGENTE_PREVENTIVO
from apps.core.db._helpers import richiedi_codice_a_vocabolario
from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.services.documento_modello import (
    e_stato_di_accettazione,
    e_stato_di_annullo,
    e_stato_di_emissione,
    e_stato_iniziale,
    rifiuta_stato_di_emissione,
    stato_di_emissione,
)
from apps.core.services.error_manager import ErrorManager
from apps.vendite.services._cliente_coppia_documento import rifiuta_colonne_ferme, risolvi_cliente_coppia
from apps.vendite.services._righe_bozza_guard import Verbo, richiedi_righe_in_bozza
from apps.vendite.services._date_consegna_righe import aggiorna_date_consegna_righe
from apps.vendite.services._annullo_con_legami import (
    legami_del_documento,
    legami_confermati as dichiarazione_legami,
)
from apps.vendite.services._iva_contesto_documento import make_risolvi_iva_riga
from apps.core.services.permissions_resolver import PermissionResolver
from apps.vendite.services._pricing_gate_helpers import (
    guard_uom_id_positive,
    resolve_or_check_override_prezzo,
    validate_componenti_overrides_authorization,
)
from apps.core.services.payload_helpers import (
    PayloadValidator,
    make_db_errors_translator,
    vincolo_violato,
)
from apps.core.services.testata_guard import (
    pagina_dopo_testata,
    riga_del_padre_o_not_found,
    testata_o_not_found,
)
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.services._componenti_service_helpers import (
    dati_patch_componente,
    normalize_componenti_attivazioni,
    normalize_componenti_overrides,
    resolve_emittente_sr_id_for_testata,
)
from apps.vendite.services._indirizzi_documento_helpers import (
    IndirizziDocumentoConfig,
    delete_indirizzo_documento,
    list_indirizzi_documento,
    upsert_indirizzo_documento,
)
from apps.core.services.partitioned_note_service import contatori_documento
from apps.vendite.db.note_repositories import NOTE_REPO_PREVENTIVO
from apps.vendite.db.preventivi_repository import TESTATA_PREVENTIVI, PreventiviRepository
from apps.vendite.types import PreventivoDetailRow
from apps.vendite.services._approvazioni_prezzo_constants import (
    STATO_APPROVAZIONE_APPROVED,
    STATO_APPROVAZIONE_PENDING,
    STATO_APPROVAZIONE_REJECTED,
)
from apps.core.api.payload_validators import envelope_da_offset


# ── Costanti di validazione ──

# ⛔ `_STATI_FATTURABILI` e `_STATI_GENERA_PRATICA` ({"ACCETTATO"}) ritirati il
#    2026-10-31 (brief-modello-documento-vendita §17.6 BE-T2): lo stato di
#    accettazione lo dice il vocabolario (colonna `accettazione`).
#    E `_STATI_MODIFICABILI` ({"DRAFT"}) nello stesso giro: la bozza e' lo
#    stato iniziale del vocabolario (`e_stato_iniziale`).
_FN = "vendite.preventivi_service"
# Il codice di validazione del dominio: una costante, non 35 letterali (2026-10-19).
E_PREV_VALIDAZIONE = "E_PREV_VALIDAZIONE"
# La data di consegna RICHIESTA dal cliente sulla riga (brief-db-modifiche-certe-
# ciclo-vendita-e-articolo, Blocco A). Sul preventivo c'e' solo la richiesta:
# la conferma nasce sull'ordine, e `fn_push_preventivo_a_ordine` porta avanti
# questa. Nullable: ometterla resta legittimo; in PATCH `null` esplicito azzera.
# Solo la FORMA si controlla qui (una data malformata e' un 400 col campo
# acceso, non un 500 dal DB): nessun CHECK di dominio, per scelta (brief §2.3).
_CHIAVE_DATA_CONSEGNA = "data_consegna_richiesta_cliente"
# Il traduttore degli errori DB del cambio di stato, lo stesso BB di ordine,
# bolla e contratto: il codice E_* del trigger o del verbo arriva al FE col
# contesto dell'operazione (`confirm_and_retry` dell'annullo compreso), e un
# errore DB senza codice e' il 400 del dominio, non un 500 generico.
_db_errors = make_db_errors_translator(
    fn_prefix=_FN,
    fallback_code=E_PREV_VALIDAZIONE,
    fallback_message="Violazione vincolo DB su preventivo.",
)

# Scopo: il contratto dell'operatore sull'UPDATE di testata e di riga, come
#        `_UPDATE_KEYS_*` di ddt/ordini/resi. Fino al 2026-09-26 erano due tuple
#        INLINE nel ciclo, e chi cercava «la whitelist dei preventivi» per nome
#        non la trovava. ⭐ Il presidio
#        `test_whitelist_service_dentro_repository` le confronta con le
#        colonne che il repository sa scrivere.
# ⚠️ `utility_id` ed `emittente_fiscale_id` NON ci sono: si scelgono alla
#    creazione (lock del DB «ferma sempre»), e le rifiuta sul campo
#    `rifiuta_colonne_ferme`. `iva_id` nemmeno (`I6`,
#    2026-08-31: l'aliquota la decide il risolutore). `quantita` e' derivata
#    dal trigger: la sorgente e' `qta_operativa`.
UPDATE_KEYS_PREVENTIVO: frozenset[str] = frozenset({
    "billing_account_id", "istanza_utility_id",
    "valuta_id", "termine_pagamento_id",
    "validita_dal", "validita_al", "competenza_mese",
    "fatturazione_immediata", "meta",
})
UPDATE_KEYS_RIGA: frozenset[str] = frozenset({
    "descrizione", "qta_operativa", "uom_operativa_id",
    "factor_to_base", "prezzo_unitario", "sconto_percentuale",
    "ordine", "meta",
})
# Il contratto della CREAZIONE (testata e riga): le chiavi che `crea_preventivo`
# e `gestisci_riga` leggono, ne' una di piu' ne' una di meno — e una chiave fuori
# elenco e' un 400 (dal 2026-10-20; prima veniva scartata in silenzio), come in
# ordini e DDT.
# ⭐ Dichiarati il 2026-09-26: fino a quel giorno le chiavi si leggevano una per
#    una e non stavano in nessun elenco, e lo schema OpenAPI scritto a mano
#    pubblicava ancora `iva_id` (chiuso da `I6`, 2026-08-31) e `quantita` (la
#    calcola il trigger da `qta_operativa`), che il service ignorava in silenzio.
#    Lo schema ora si legge da qui (`vendite/api/_schema_da_contratto.py`).
CREATE_KEYS_PREVENTIVO: frozenset[str] = frozenset({
    "utility_id", "billing_account_id", "istanza_utility_id",
    "emittente_fiscale_id", "valuta_id", "termine_pagamento_id",
    "validita_dal", "validita_al", "competenza_mese",
    "fatturazione_immediata", "meta",
})
CREATE_KEYS_RIGA: frozenset[str] = frozenset({
    "articolo_id", "descrizione", "qta_operativa", "uom_operativa_id",
    "factor_to_base", "prezzo_unitario", "sconto_percentuale", "ordine", "meta",
    "data_consegna_richiesta_cliente", "richiesta_approvazione",
    "componenti_overrides", "componenti_attivazioni",
})
# In MODIFICA riga, oltre a `UPDATE_KEYS_RIGA` (le colonne che il repository
# scrive in blocco), `aggiorna_riga` legge a parte queste due: la data con il
# suo validatore, la richiesta di approvazione per il gate L3.
UPDATE_RIGA_LETTE_A_PARTE: frozenset[str] = frozenset({
    "data_consegna_richiesta_cliente", "richiesta_approvazione",
})
# Validator stateless del dominio (solo il codice): testata e righe.
_V = PayloadValidator(validation_code=E_PREV_VALIDAZIONE)


# Scopo: Carica la testata preventivo o solleva E_PREV_NOT_FOUND (BB core
#        `testata_o_not_found`, stesso nome del helper di ordini e DDT).
def _get_testata_or_raise(
    repo: PreventiviRepository, preventivo_id: int, *, op: str,
) -> PreventivoDetailRow:
    return testata_o_not_found(
        repo.get_preventivo, preventivo_id,
        code="E_PREV_NOT_FOUND", message="Preventivo non trovato.",
        id_name="preventivo_id", function_name=f"{_FN}.{op}",
    )


# Scopo: La data di consegna richiesta dal payload di riga: `None` se assente,
#        vuota o `null`; `date` se ISO valida; 400 col campo se malformata.
def _data_consegna_da_payload(payload: dict[str, Any], *, function_name: str) -> date | None:
    normalizzato = {_CHIAVE_DATA_CONSEGNA: empty_to_none(payload.get(_CHIAVE_DATA_CONSEGNA))}
    return _V.optional_date(
        normalizzato, _CHIAVE_DATA_CONSEGNA, function_name=function_name,
    )


# ══════════════════════════════════════════════════════════
#  LETTURE
# ══════════════════════════════════════════════════════════


# Scopo: Lista preventivi paginata con filtri e scope emittente.
# Scopo: Letture grezze (righe + totale) della lista preventivi. Estratta da
#        `list_preventivi` (regola del 2) per condividere la query tra la lista
#        paginata (envelope) e l'export (DEF-1, che fetcha fino a
#        EXPORT_MAX_ROWS+1 senza paginazione). order_by/order_dir guidano
#        l'ordinamento configurabile (whitelist SQL-safe nel repository).
def list_preventivi_rows(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    search: str | None = None,
    solo_ultima_revisione: bool = True,
    auth_user_id: int | None = None,
    limit: int,
    offset: int,
    order_by: str = "data",
    order_dir: str = "desc",
    max_limit: int = MAX_LIMIT,
) -> tuple[list[Any], int]:
    # ⛔ Il filtro di stato esiste nel vocabolario, o e' un 400 sul campo: un
    #    valore sbagliato finiva nel WHERE e la lista rispondeva vuota con un
    #    200 (2026-10-20). Codici dismessi ammessi: i documenti vecchi li portano.
    richiedi_codice_a_vocabolario(
        "config.stati_doc_preventivi", "codice_interno", stato_codice,
        codice_errore="E_PREV_VALIDAZIONE", parametro="stato",  # il query param della lista
    )
    repo = PreventiviRepository()
    return repo.list_preventivi(
        stato_codice=stato_codice,
        billing_account_id=billing_account_id,
        utility_id=utility_id,
        data_da=data_da,
        data_al=data_al,
        search=search,
        solo_ultima_revisione=solo_ultima_revisione,
        auth_user_id=auth_user_id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
        max_limit=max_limit,
    )


def list_preventivi(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    search: str | None = None,
    solo_ultima_revisione: bool = True,
    auth_user_id: int | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order_by: str = "data",
    order_dir: str = "desc",
) -> dict[str, Any]:
    # ⭐ `limit`/`offset` come ogni lista (2026-10-21, un dialetto solo): fino a
    #    quel giorno `page`/`page_size`, l'ultimo wrapper che li parlava.
    ErrorManager.require(
        1 <= limit <= MAX_LIMIT and offset >= 0,
        code=E_PREV_VALIDAZIONE,
        message="Parametri paginazione non validi.",
        function_name=f"{_FN}.list_preventivi",
    )
    results, total_count = list_preventivi_rows(
        stato_codice=stato_codice,
        billing_account_id=billing_account_id,
        utility_id=utility_id,
        data_da=data_da,
        data_al=data_al,
        search=search,
        solo_ultima_revisione=solo_ultima_revisione,
        auth_user_id=auth_user_id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
    )
    return envelope_da_offset(results, total_count, limit=limit, offset=offset)


# Scopo: Etichette leggibili dei filtri attivi, incluse come metadato nel file
#        di export (DEF-1 §6: un file filtrato deve dichiararsi sottoinsieme).
#        Gemello di ContrattiService.resolve_filtri_export_label.
def resolve_filtri_export_label(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    solo_ultima_revisione: bool = True,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if stato_codice:
        out["Stato"] = stato_codice
    if billing_account_id is not None:
        out["Cliente BA (id)"] = billing_account_id
    if utility_id is not None:
        out["Utility (id)"] = utility_id
    if data_da is not None:
        out["Dal"] = str(data_da)
    if data_al is not None:
        out["Al"] = str(data_al)
    # solo_ultima_revisione=False = storico revisioni incluso (informazione utile nel file)
    if not solo_ultima_revisione:
        out["Storico revisioni"] = "incluso"
    return out


# Scopo: Dettaglio preventivo testata + summary + indirizzi + capabilities.
#        Le righe NON sono incluse: il FE le legge separatamente via
#        `GET /preventivi/<id>/righe/` (Fase 3.F6 refactor frontend vendite,
#        decisione C2). I totali_* sono nella testata via trigger DB; aggiungiamo
#        `righe_count` come summary leggero (badge UX). Le capability
#        (available_actions, can_edit_*, can_push_commessa, can_create_revisione,
#        non_editable_fields) sono calcolate da script.fn_available_actions_preventivo
#        e viaggiano SOTTO `capabilities` (api.md §«Il blob sta SOTTO
#        `capabilities`», 2026-09-23).
def get_preventivo(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = _get_testata_or_raise(repo, preventivo_id, op="get_preventivo")
    indirizzi = repo.list_indirizzi(preventivo_id)
    # ⭐ Il blob si consegna COM'E' (api.md §Capability: «il backend trasporta,
    #    non deduce»). I prezzi non autorizzati — righe o componenti BoM attivi
    #    PENDING o REJECTED — spengono «Emetti» e «Accetta» col loro motivo
    #    dentro `available_actions[].reasons`, dallo stesso building block con
    #    cui il guard di transizione solleva (script.fn_check_prezzi_autorizzati);
    #    «Annulla» e la modifica in BOZZA restano accesi (D-2, D-3). Fino al
    #    2026-09-24 qui c'era una riscrittura Python del blob che scriveva
    #    un'altra regola: ritirata, brief-db-preventivi-congelamento-pricing §6.1.
    capabilities = repo.get_capabilities(preventivo_id)
    # Summary leggero: una COUNT sulle righe attive (no scan dell'elenco
    # completo). Le righe vere passano dall'endpoint /righe/ autonomo.
    righe_count = repo.count_righe(preventivo_id)
    return {
        **testata,
        "capabilities": capabilities,
        "indirizzi": indirizzi,
        "righe_count": righe_count,
        "contatori": contatori_documento(NOTE_REPO_PREVENTIVO, preventivo_id),
    }


# Scopo: Lista righe di un preventivo. Legge prima la testata: un preventivo
#        fuori perimetro (o inesistente) e' un 404, non un pannello vuoto.
def list_righe(preventivo_id: int) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    _get_testata_or_raise(repo, preventivo_id, op="list_righe")
    return repo.list_righe(preventivo_id)


# Scopo: Una PAGINA delle righe del preventivo, per la lista configurabile
#        (`GET …/righe/lista/`): ricerca, ordinamento e pagina dal BB del
#        repository, dopo la testata (BB core `pagina_dopo_testata`).
#        Ritorna `(righe, totale)`.
def list_righe_pagina(preventivo_id: int, **opzioni: Any) -> tuple[list[dict[str, Any]], int]:
    repo = PreventiviRepository()
    return pagina_dopo_testata(
        lambda: _get_testata_or_raise(repo, preventivo_id, op="list_righe_pagina"),
        repo.list_righe_pagina, preventivo_id, **opzioni,
    )


# Scopo: Righe MERCE smistabili a ordine (natura destinazione_tipo='ORDINE_VENDITA' non
#        ancora allocate). Alimenta il dialog di smistamento riga-per-riga
#        preventivo→ordine: il FE preseleziona tutte e invia il sottoinsieme
#        scelto a POST /genera-ordine/ {righe_ids}. Le righe sono esattamente
#        quelle che lo smistamento copierebbe (stesso predicato del residuo).
def list_righe_smistabili_ordine(preventivo_id: int) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    _get_testata_or_raise(repo, preventivo_id, op="list_righe_smistabili_ordine")
    return repo.list_righe_smistabili_ordine(preventivo_id)


# Scopo: Riepilogo IVA aggregato del preventivo (una riga per aliquota +
#        eventuali natura/esigibilita/split). Calcolo fiscalmente corretto
#        gia' applicato in DB via fn_ricalcola_riepilogo_iva_preventivo:
#        il service legge la vista denormalizzata, nessun ricalcolo Python.
#        Usato dal FE per il pannello "Riepilogo IVA" del drawer preventivo
#        e (futuro) come builder per fatture emesse dal preventivo.
#        Legge prima la testata: fuori perimetro e' un 404.
def list_riepilogo_iva(preventivo_id: int) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    _get_testata_or_raise(repo, preventivo_id, op="list_riepilogo_iva")
    return repo.list_riepilogo_iva(preventivo_id)


# Scopo: Restituisce il contesto pricing applicato al preventivo (contratto
#        attivo o listino categoria fallback). Lettura puramente informativa
#        usata dall'header del drawer preventivo per audit visivo del path
#        di risoluzione prezzi. Lo stesso resolver `fn_resolve_prezzo_listino_v2`
#        applica la stessa logica al momento del calcolo prezzi riga.
def get_contesto_pricing(preventivo_id: int) -> dict[str, Any] | None:
    repo = PreventiviRepository()
    # ⛔ Prima la testata: un preventivo inesistente o fuori perimetro e' il
    #    404 del dominio, non `200 {}` (2026-10-20, l'ordine di lettura dei
    #    satelliti di api.md §«Scope emittente»).
    _get_testata_or_raise(repo, preventivo_id, op="get_contesto_pricing")
    return repo.resolve_contesto_pricing(preventivo_id)


# ── Indirizzi documento (BB condiviso _indirizzi_documento_helpers) ──

_INDIRIZZI_CFG = IndirizziDocumentoConfig(
    # lambda (non la classe): risolve il nome a call-time, cosi' i @patch
    # dei test unit raggiungono il repository.
    repo_factory=lambda: PreventiviRepository(),
    not_found_code="E_PREV_NOT_FOUND",
    error_code=E_PREV_VALIDAZIONE,
    fn_prefix=_FN,
)


# Scopo: Pannello indirizzi del preventivo (ambito PREVENTIVI). Guard di
#        esistenza e traduzione errori DB nel BB condiviso.
def list_indirizzi(preventivo_id: int) -> dict[str, Any]:
    return list_indirizzi_documento(_INDIRIZZI_CFG, preventivo_id)


# Scopo: Upsert slot indirizzo (uno-per-tipo, solo BOZZA: post-emissione lo
#        snapshot e' congelato; la revisione lo copia 1:1).
def upsert_indirizzo(preventivo_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return upsert_indirizzo_documento(_INDIRIZZI_CFG, preventivo_id, payload)


# Scopo: Rimozione slot indirizzo (solo BOZZA).
def delete_indirizzo(preventivo_id: int, indirizzo_id: int) -> dict[str, Any]:
    return delete_indirizzo_documento(_INDIRIZZI_CFG, preventivo_id, indirizzo_id)


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Testata
# ══════════════════════════════════════════════════════════


_MSG_BA_FUORI_COPPIA = (
    "Il billing account non e' quello dell'istanza e della utility del preventivo."
)


# Scopo: il cliente del preventivo, letto dal lato che il payload porta: il BB
#        `risolvi_cliente_coppia` (regola del 2 con offerta e contratto), coi
#        codici del preventivo. La coppia senza BA resta
#        `E_PREV_UTILITY_ISTANZA_INCOERENTE` sul campo `utility_id`.
def _risolvi_cliente_preventivo(
    *,
    billing_account_id: int | None,
    istanza_utility_id: int | None,
    utility_id: int,
    function_name: str,
) -> tuple[int, int]:
    return risolvi_cliente_coppia(
        billing_account_id=billing_account_id,
        istanza_utility_id=istanza_utility_id,
        utility_id=utility_id,
        code=E_PREV_VALIDAZIONE,
        msg_ba_fuori_coppia=_MSG_BA_FUORI_COPPIA,
        function_name=function_name,
        code_coppia_senza_ba="E_PREV_UTILITY_ISTANZA_INCOERENTE",
        campo_coppia_senza_ba="utility_id",
    )


# Scopo: traduce la FK composta del cliente del preventivo (R-2 di
#        brief-db-istanza-nasce-col-ba): un BA che non e' quello della coppia
#        (istanza, utility) del documento. Le altre violazioni proseguono
#        intatte verso il middleware, come prima.
@contextmanager
def _vincoli_cliente_preventivo() -> Iterator[None]:
    try:
        yield
    except IntegrityError as exc:
        if vincolo_violato(exc, ["fk_preventivi_ba_coppia"]) is None:
            raise
        ErrorManager.raise_error(
            code="E_VENDITE_FK",
            message=_MSG_BA_FUORI_COPPIA,
            detail=str(exc),
            context={"field": "billing_account_id"},
            cause=exc,
        )


# Scopo: Crea un nuovo preventivo in stato BOZZA.
# Obiettivo: validazione input, INSERT, restituisce id+uid+numero. Lo stato non
#            si passa: il preventivo nasce nello stato iniziale del suo
#            vocabolario, e lo mette il DB (BB `script.trgfn_doc_stato_iniziale`,
#            brief-modello-documento-vendita P-2).
#
# Regole di dominio:
#  - utility_id obbligatorio;
#  - il cliente e' la coppia (istanza, utility) col suo billing account, letto
#    dal lato che il payload porta (`_risolvi_cliente_preventivo`): il
#    preventivo ha sempre il BA (brief-db-istanza-nasce-col-ba, R-2).
#    Defense-in-depth: il trigger DB trgfn_preventivi_guard_utility_istanza_coerenza
#    e la FK composta fk_preventivi_ba_coppia.
#  - emittente_fiscale_id: opzionale nel payload. Se None il trigger DB
#    script.trgfn_default_emittente_fiscale (BB unico dal 2026-09-15; la copia
#    trgfn_preventivi_default_emittente e' droppata) lo valorizza da GUC
#    app.current_user_id, e senza sessione risolvibile solleva
#    E_EMITTENTE_NON_RISOLTO.
#    Specificarlo esplicito solo per admin globale (utente senza emittente
#    assegnato che sceglie l'emittente del documento).
def crea_preventivo(payload: dict[str, Any]) -> dict[str, Any]:
    # ⛔ Una chiave fuori whitelist e' un 400, non uno scarto silenzioso (2026-10-20,
    #    la regola del 2026-10-19 estesa ai gemelli): la risposta era ok e il valore
    #    non arrivava, senza che nessuno lo sapesse.
    _V.validate_allowed_keys(payload, allowed=CREATE_KEYS_PREVENTIVO, function_name=f"{_FN}.crea_preventivo")
    repo = PreventiviRepository()

    utility_id = payload.get("utility_id")
    ErrorManager.require(
        utility_id is not None,
        code=E_PREV_VALIDAZIONE,
        message="utility_id obbligatorio.",
        function_name=f"{_FN}.crea_preventivo",
    )

    assert utility_id is not None
    billing_account_id, istanza_utility_id = _risolvi_cliente_preventivo(
        billing_account_id=payload.get("billing_account_id"),
        istanza_utility_id=payload.get("istanza_utility_id"),
        utility_id=int(utility_id),
        function_name=f"{_FN}.crea_preventivo",
    )

    # Creazione e slot di default in UNA transazione (il riempimento non e'
    # best-effort: api.md §Atomicita').
    with _vincoli_cliente_preventivo(), transaction.atomic():
        result = repo.create_preventivo(
            billing_account_id=billing_account_id,
            utility_id=utility_id,
            istanza_utility_id=istanza_utility_id,
            emittente_fiscale_id=payload.get("emittente_fiscale_id"),
            valuta_id=payload.get("valuta_id"),
            termine_pagamento_id=payload.get("termine_pagamento_id"),
            validita_dal=payload.get("validita_dal"),
            validita_al=payload.get("validita_al"),
            competenza_mese=payload.get("competenza_mese"),
            # Un flag del corpo e' un booleano JSON (`"false"` e' un 400 sul campo).
            fatturazione_immediata=_V.optional_bool(payload, "fatturazione_immediata") or False,
            meta=payload.get("meta"),
        )
        # Slot di default dall'anagrafica del cliente: lo decide il DB
        # (`vendite.fn_doc_indirizzo_default`).
        repo.riempi_indirizzo_default(int(result["id"]))
    return result


# Scopo: Elimina (hard-delete) preventivo BOZZA orfano.
# Obiettivo: supporto al pattern "abbandono bozza" del drawer FE — quando
# l'operatore apre create, si crea automaticamente la BOZZA per abilitare
# subito l'inserimento righe (master-detail inline), ma esce senza inserire
# righe. La BOZZA orfana viene cancellata su conferma utente.
#
# Guard di dominio (defense-in-depth: il caller FE filtra gia' su righe_count=0,
# qui ricontrolliamo per sicurezza):
#  - preventivo deve esistere
#  - stato == BOZZA (DRAFT)
#  - zero righe attive
#  - zero pratiche collegate
# Non ammessa per preventivi gia' propagati a commessa o con stato avanzato:
# in quei casi la "cancellazione" semantica e' cambia_stato → ANNULLATO.
def elimina_preventivo(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = _get_testata_or_raise(repo, preventivo_id, op="elimina_preventivo")
    # Eliminabili solo i preventivi nello stato in cui nascono (la bozza: lo
    # stato iniziale del vocabolario). Qualsiasi stato successivo
    # (EMESSO/ACCETTATO/...) richiede cambia_stato → ANNULLATO invece
    # dell'hard-delete.
    ErrorManager.require(
        e_stato_iniziale(TESTATA_PREVENTIVI, testata["stato_codice_interno"]),
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Solo i preventivi in stato BOZZA possono essere eliminati.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.elimina_preventivo",
    )
    righe_count = repo.count_righe(preventivo_id)
    ErrorManager.require(
        righe_count == 0,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Impossibile eliminare un preventivo con righe. Eliminare prima le righe.",
        detail=f"righe_count={righe_count}",
        function_name=f"{_FN}.elimina_preventivo",
    )
    pratiche_count = len(repo.list_pratiche(preventivo_id))
    ErrorManager.require(
        pratiche_count == 0,
        code="E_PREV_STATO_NON_MODIFICABILE",
        message="Impossibile eliminare un preventivo con pratiche collegate.",
        detail=f"pratiche_count={pratiche_count}",
        function_name=f"{_FN}.elimina_preventivo",
    )
    deleted = repo.delete_preventivo(preventivo_id)
    return {"status": "ok" if deleted else "noop", "preventivo_id": preventivo_id}


# Scopo: Aggiorna testata preventivo.
#
# Quali colonne si cambiano in quale stato lo dice il DB, colonna per colonna:
# il lock di testata `vendite.trgfn_doc_testata_lock_fuori_bozza` (in bozza
# tutto; emesso e accettato le note e la competenza, D-9; chiuso niente). Fino
# al 2026-10-10 qui c'era un «solo in DRAFT» che ne era la seconda copia
# (brief-db-testata-dopo-emissione, D-0 e R-BE-2): il 409 del lock passa com'e'.
def aggiorna_preventivo(preventivo_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = PreventiviRepository()
    # ⛔ Fino al 2026-10-19 una chiave fuori whitelist si SCARTAVA in silenzio
    #    (anche `utility_id`: la risposta era ok e non cambiava niente). Ora le
    #    due colonne ferme sono un 400 sul campo, e ogni altra chiave ignota un
    #    400 (R-BE-10, scelta di Tid), come su offerta e contratto.
    rifiuta_colonne_ferme(
        payload, code=E_PREV_VALIDAZIONE, function_name=f"{_FN}.aggiorna_preventivo",
    )
    _V.validate_allowed_keys(payload, allowed=UPDATE_KEYS_PREVENTIVO)
    # Prima la testata: fuori perimetro o inesistente e' un 404.
    testata = _get_testata_or_raise(repo, preventivo_id, op="aggiorna_preventivo")

    update_fields: dict[str, Any] = {}
    for key in UPDATE_KEYS_PREVENTIVO:
        if key in payload:
            val = payload[key]
            update_fields[key] = empty_to_none(val) if isinstance(val, str) else val
    # ⛔ Il flag e' NOT NULL e booleano: presente, dev'essere `true`/`false`
    #    JSON. Prima `"false"` arrivava al DB come stringa e `""` come NULL.
    if "fatturazione_immediata" in payload:
        update_fields["fatturazione_immediata"] = _V.require_bool(payload, "fatturazione_immediata")

    # Il cliente si cambia per coppia: BA e istanza viaggiano insieme, letti dal
    # lato che il payload porta (stessa regola della creazione). Cambiare il
    # solo BA lascerebbe l'istanza vecchia, che la FK composta rifiuta.
    if "billing_account_id" in update_fields or "istanza_utility_id" in update_fields:
        (
            update_fields["billing_account_id"],
            update_fields["istanza_utility_id"],
        ) = _risolvi_cliente_preventivo(
            billing_account_id=update_fields.get("billing_account_id"),
            istanza_utility_id=update_fields.get("istanza_utility_id"),
            utility_id=int(testata["utility_id"]),
            function_name=f"{_FN}.aggiorna_preventivo",
        )

    # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
    #    2026-10-20, brief-be-verifica-documentazione-api §A2).
    _V.require_campi_da_aggiornare(update_fields)
    with _vincoli_cliente_preventivo():
        repo.update_preventivo(preventivo_id, **update_fields)

    return {"status": "ok", "preventivo_id": preventivo_id}


# Scopo: Cambia stato preventivo delegando al verbo DB.
#
# Caso speciale EMESSO → ACCETTATO (transizione "accettazione"):
#   l'operatore deve specificare la modalita' di fatturazione del preventivo
#   (proprieta' di processo, NON visibili in form testata BOZZA — vedi
#   sviluppo-preventivi.md). Parametri:
#     - fatturazione_immediata (bool obbligatorio)
#     - competenza_mese (date YYYY-MM-01, obbligatorio se immediata=False)
#   Regola di priorita': se immediata=True → competenza_mese forzata a oggi
#   (primo del mese corrente), il valore eventuale passato dal caller viene
#   ignorato. Per ora la regola e' applicata qui (BE service); future
#   defense-in-depth via trigger DB se servira'.
#   Su un preventivo gia' ACCETTATO la stessa richiesta aggiorna SOLO la
#   modalita' di fatturazione: lo stato non cambia, e il verbo non si chiama
#   (la matrice non ha ACCETTATO → ACCETTATO: fino al giro 6 la richiesta
#   finiva in E_PREV_TRANSIZIONE_NON_AMMESSA, brief-modello-documento-vendita
#   §8.7 punto 5).
#
# Le altre transizioni (EMESSO→RIFIUTATO, *→ANNULLATO, ...) ignorano i 2
# parametri.
#
# ⛔ Lo stato di emissione NO (M-2): il preventivo si emette solo da «Emetti»
#    (`emetti`), che produce numero e PDF nella stessa transazione. Quale stato
#    sia l'emissione lo dice il vocabolario (BB `rifiuta_stato_di_emissione`).
#
# ⭐ L'annullo (lo stato d'annullo del vocabolario, `is_abortito`) passa SEMPRE
# dal verbo `vendite.fn_annulla_preventivo`
# (brief-db-annullo-documento-con-legami): con legami il DB rifiuta
# (E_DOC_ANNULLO_CON_LEGAMI, `confirm_and_retry`) finche' la richiesta non
# dichiara `legami_confermati`, il numero letto da `get_legami`. La risposta ha
# la stessa forma di `fn_cambia_stato_preventivo`.
def cambia_stato(
    preventivo_id: int,
    nuovo_stato: str,
    *,
    fatturazione_immediata: bool | None = None,
    competenza_mese: date | None = None,
    user: AbstractBaseUser | AnonymousUser | None = None,
    legami_confermati: Any = None,
) -> dict[str, Any]:
    repo = PreventiviRepository()

    rifiuta_stato_di_emissione(
        TESTATA_PREVENTIVI, nuovo_stato, campo="nuovo_stato",
        validation_code=E_PREV_VALIDAZIONE, function_name=f"{_FN}.cambia_stato",
    )

    # Gate accettazione: i 2 parametri servono dall'emissione all'accettazione e
    # sull'aggiornamento di un accettato (finche' il preventivo e' fatturabile).
    # Su altre transizioni i parametri sono ignorati. Emissione e accettazione
    # dal vocabolario (§17.6 BE-T2), non `"EMESSO"` / `"ACCETTATO"`.
    if e_stato_di_accettazione(TESTATA_PREVENTIVI, nuovo_stato):
        # Lo stato corrente decide se servono i due parametri. Un preventivo
        # che non c'e' (None) salta il ramo e lo rifiuta il verbo
        # (E_PREV_NOT_FOUND, regola del 1).
        stato_attuale = repo.get_stato_codice(preventivo_id)
        gia_accettato = stato_attuale == nuovo_stato
        if stato_attuale is not None and (
            gia_accettato or e_stato_di_emissione(TESTATA_PREVENTIVI, stato_attuale)
        ):
            ErrorManager.require(
                fatturazione_immediata is not None,
                code=E_PREV_VALIDAZIONE,
                message="Modalita' di fatturazione obbligatoria per accettare il preventivo.",
                detail="fatturazione_immediata: bool obbligatorio.",
                function_name=f"{_FN}.cambia_stato",
            )
            # Regola di priorita': immediata=True ⇒ competenza = primo giorno
            # del mese corrente (snapshot tx-time). Eventuale valore esplicito
            # passato dal caller viene sovrascritto (immediata ha priorita').
            if fatturazione_immediata:
                competenza_mese = oggi_aziendale().replace(day=1)
            else:
                ErrorManager.require(
                    competenza_mese is not None,
                    code=E_PREV_VALIDAZIONE,
                    message=(
                        "Mese di competenza obbligatorio quando fatturazione "
                        "non e' immediata."
                    ),
                    function_name=f"{_FN}.cambia_stato",
                )
            # La modalita' PRIMA del passaggio, nella stessa transazione: il
            # guard dell'accettazione la trova gia' scritta.
            with _db_errors("cambia_stato"), transaction.atomic():
                repo.update_preventivo(
                    preventivo_id,
                    fatturazione_immediata=bool(fatturazione_immediata),
                    competenza_mese=competenza_mese,
                )
                if gia_accettato:
                    return {
                        "preventivo_id": preventivo_id,
                        "stato_precedente": stato_attuale,
                        "stato_nuovo": stato_attuale,
                    }
                return repo.cambia_stato(preventivo_id, nuovo_stato)

    if e_stato_di_annullo(TESTATA_PREVENTIVI, nuovo_stato):
        confermati = dichiarazione_legami(
            legami_confermati, validation_code=E_PREV_VALIDAZIONE,
            function_name=f"{_FN}.cambia_stato",
        )
        # Lo stato di partenza per la risposta: il verbo d'annullo rende i soli
        # legami. «Il preventivo c'e'» lo dice il verbo (E_PREV_NOT_FOUND,
        # regola del 1), e il None di qui non arriva al client.
        stato_prec = repo.get_stato_codice(preventivo_id)
        with _db_errors("cambia_stato"):
            repo.annulla(preventivo_id, confermati)
        return {
            "preventivo_id": preventivo_id,
            "stato_precedente": stato_prec,
            "stato_nuovo": nuovo_stato,
        }

    with _db_errors("cambia_stato"):
        result = repo.cambia_stato(preventivo_id, nuovo_stato)
    return result


# Scopo: I legami del preventivo per la finestra di conferma dell'annullo (BB
#        `legami_del_documento`): righe di commessa da emettere. Prima la
#        testata: il lettore del DB non applica il perimetro.
def get_legami(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata_o_not_found(
        repo.get_stato_codice, preventivo_id,
        code="E_PREV_NOT_FOUND", message="Preventivo non trovato.",
        id_name="preventivo_id", function_name=f"{_FN}.get_legami",
    )
    return legami_del_documento(SORGENTE_PREVENTIVO, preventivo_id)


# Scopo: GUIDA (D4) — «Accetta/Rifiuta» in-pratica → azione sul DOCUMENTO
#        standalone. Risolve il preventivo ROOT della pratica e ne cambia lo
#        stato via `cambia_stato`. Sostituisce l'handler
#        `vendita.accetta_preventivo` (inversione handler→proiezione): il
#        documento e' sovrano, il milestone della pratica avanza da solo via
#        trigger DB `pratiche.fn_reconcile_sorgente` (binding
#        template_flussi_avanzamento_proiezione). Nessun completamento di flusso
#        qui: la pratica NON e' toccata dal BE.
def cambia_stato_da_pratica(
    pratica_id: int,
    nuovo_stato: str,
    *,
    fatturazione_immediata: bool | None = None,
    competenza_mese: date | None = None,
    user: AbstractBaseUser | AnonymousUser | None = None,
) -> dict[str, Any]:
    preventivo_id = PreventiviRepository().get_preventivo_id_by_pratica_root(pratica_id)
    ErrorManager.require(
        preventivo_id is not None,
        code="E_VENDITA_PREVENTIVO_NON_COLLEGATO",
        message="Nessun preventivo ROOT collegato alla pratica.",
        detail=f"pratica_id={pratica_id}",
        function_name=f"{_FN}.cambia_stato_da_pratica",
    )
    assert preventivo_id is not None
    return cambia_stato(
        preventivo_id,
        nuovo_stato,
        fatturazione_immediata=fatturazione_immediata,
        competenza_mese=competenza_mese,
        user=user,
    )


# Scopo: BOZZA -> EMESSO (transizione di stato). Solo la transizione: la view
#        multipart `ApiPreventivoEmetti` incapsula questa chiamata insieme a
#        `DocumentGenerationService.genera_documento(allegati=...)` in
#        un'unica `transaction.atomic()` esterna, garantendo che EMESSO
#        implichi sempre l'esistenza del documento generato (invariante di
#        dominio). Mirror del pattern offerta `OfferteService.emetti`.
#        Bypassa il guard di `cambia_stato` sull'emissione via accesso
#        diretto al repository. Lo stato che scrive lo dice il vocabolario (BB
#        `stato_di_emissione`, brief-modello-documento-vendita §8.11 B-3).
def emetti(preventivo_id: int, *, user: str | None = None) -> dict[str, Any]:
    repo = PreventiviRepository()
    stato = stato_di_emissione(TESTATA_PREVENTIVI, function_name=f"{_FN}.emetti")
    result = repo.cambia_stato(preventivo_id, stato.codice)
    # Percorso pratica-first: l'emissione del preventivo completa il flusso di
    # preventivazione ancora aperto (quello che ha aperto questo drawer via
    # azione_ui APRI_PREVENTIVO). No-op se il preventivo non nasce da una pratica
    # o se il flusso e' gia' chiuso (idempotenza ri-emissione). Gira nella stessa
    # transazione atomica della view (emetti + genera_documento): completamento
    # flusso e emissione sono atomici.
    _completa_flusso_preventivazione(preventivo_id, user=user)
    return result


# Scopo: Completa il flusso d'origine del preventivo (aggancio per-flusso) quando
#        questo viene emesso. Esito POSITIVO: l'emissione e' il successo della
#        preventivazione e sblocca i passi a valle (es. APPROVAZIONE_CLIENTE).
#        Il preventivo conosce IL SUO flusso (pratiche_sorgenti.flusso_id) → lo
#        completo direttamente, senza cercarlo per azione_ui. No-op se il
#        preventivo non nasce da un flusso o il flusso non e' IN_CORSO (gia'
#        completato/non avviato → idempotenza ri-emissione). Direzione
#        vendite→pratiche, import lazy (mirror del pattern handler).
def _completa_flusso_preventivazione(preventivo_id: int, *, user: str | None = None) -> None:
    from apps.pratiche.db.pratiche_repository import PraticheRepository
    from apps.pratiche.services import pratiche_service

    flusso_id = PreventiviRepository().get_flusso_id_by_preventivo_root(preventivo_id)
    if flusso_id is None:
        return
    flusso = PraticheRepository().get_flusso(flusso_id)
    if flusso is None or flusso.get("stato_codice_interno") != "IN_CORSO":
        return
    pratiche_service.completa_flusso(flusso_id, esito="POSITIVO", user=user)


# Scopo: Crea nuova revisione del preventivo delegando alla funzione DB.
def crea_revisione(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    result = repo.crea_revisione(preventivo_id, "django_api")
    return result


# Scopo: Lista catena revisioni del preventivo (tutte le righe con stesso
#        `numero`, ordinate per `rev`). Mirror del pattern offerte
#        `list_revisioni`; differenza chiave: preventivi sono catenate via
#        `numero` non via `revisione_padre_id`.
#        Legge prima la testata: fuori perimetro e' un 404 (e non una lista
#        vuota, che direbbe «nessuna revisione» di un documento che non c'e').
#        Paginata dal 2026-09-27: ritorna (righe, totale) per `paginated_envelope`.
def list_revisioni(
    preventivo_id: int, *,
    limit: int = DEFAULT_LIMIT, offset: int = 0,
    order_by: str | None = None, order_dir: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    repo = PreventiviRepository()
    _get_testata_or_raise(repo, preventivo_id, op="list_revisioni")
    return repo.list_revisioni(
        preventivo_id,
        limit=limit, offset=offset, order_by=order_by, order_dir=order_dir,
    )


# Scopo: Aggancia il preventivo come ROOT a una pratica (pratiche_sorgenti).
#        Usato a PREVENTIVAZIONE sul percorso pratica-first. Idempotente.
#        È la fonte di verità del legame preventivo↔pratica, da cui handler e
#        M2 risolvono il preventivo. Direzione vendite→pratiche, import lazy.
def collega_pratica(
    preventivo_id: int, *, pratica_id: int, flusso_id: int | None = None,
) -> dict[str, Any]:
    from apps.pratiche.db.pratiche_repository import PraticheRepository

    repo = PreventiviRepository()
    prev = _get_testata_or_raise(repo, preventivo_id, op="collega_pratica")
    # Aggancio ROOT per-flusso: flusso_id ancora il documento al flusso d'origine
    # (brief-db-aggancio-documento-flusso). L'indice unico parziale impedisce un
    # secondo ROOT sullo stesso flusso; il trigger guard verifica che il flusso
    # sia DI questa pratica. flusso_id None = retrocompat / link non da flusso.
    PraticheRepository().upsert_pratica_sorgente(
        pratica_id=pratica_id, sorgente_codice=SORGENTE_PREVENTIVO,
        sorgente_uid=prev["uid"], ruolo_link="ROOT", flusso_id=flusso_id,
    )
    return {
        "preventivo_id": preventivo_id, "pratica_id": pratica_id,
        "flusso_id": flusso_id, "uid": prev["uid"],
    }


# Scopo: Risolve il preventivo ROOT collegato a un FLUSSO (percorso pratica-first,
#        aggancio per-flusso). Ritorna {"preventivo_id": id|None}. Alimenta la
#        RIAPERTURA: l'attivita' UI "apri preventivo" ha il flusso_id e riapre il
#        ROOT di quel flusso in edit invece di crearne uno nuovo.
def get_root_per_flusso(flusso_id: int) -> dict[str, Any]:
    ErrorManager.require(
        flusso_id > 0,
        code="E_FLUSSO_ID_INVALIDO",
        message="flusso_id non valido.",
        detail=f"flusso_id={flusso_id}",
        function_name=f"{_FN}.get_root_per_flusso",
    )
    preventivo_id = PreventiviRepository().get_preventivo_id_by_flusso_root(flusso_id)
    return {"preventivo_id": preventivo_id}


# Scopo: risolve il preventivo ROOT della PRATICA (non per-flusso). Usato dal
# percorso pratica per gli step a valle (es. SMISTAMENTO) che operano sul
# preventivo gia' agganciato a monte (flusso PREVENTIVAZIONE), non sul proprio.
def get_root_per_pratica(pratica_id: int) -> dict[str, Any]:
    ErrorManager.require(
        pratica_id > 0,
        code="E_PRATICA_ID_INVALIDO",
        message="pratica_id non valido.",
        detail=f"pratica_id={pratica_id}",
        function_name=f"{_FN}.get_root_per_pratica",
    )
    preventivo_id = PreventiviRepository().get_preventivo_id_by_pratica_root(pratica_id)
    return {"preventivo_id": preventivo_id}


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Righe
# ══════════════════════════════════════════════════════════


# Scopo: risolve il trattamento IVA di una riga preventivo, e ritorna
#        `(iva_id, meta_patch)`.
# ⭐ Wrapper sottile sul BB `IvaResolverService.applica_riga_documento`.
# ⚠️ L'EMITTENTE IN DUE PASSI, come gia' fa l'init dei componenti: prima quello
#    esplicito del preventivo (admin globale che l'ha scelto), poi quello
#    dell'operatore. ⛔ Ma qui, a differenza dei componenti, l'assenza NON e'
#    uno skip silenzioso: senza emittente il risolutore leggerebbe zero titoli
#    sotto RLS e risponderebbe con l'aliquota ordinaria senza sollevare — una
#    riga sbagliata che nessuno segnala. `P3`: ci si ferma.
# ⛔ E' la PK di `emittenti_fiscali`, non il `soggetto_ruolo_id` che
#    `resolve_emittente_sr_id_for_testata` produce per il pricing.
# ⭐ Costruito da una FACTORY e non scritto qui: i tre domini avevano tre copie
#    identiche a meno del codice errore. Stesso stampo di
#    `make_db_errors_translator` — i parametri di dominio si fissano una volta,
#    la regola resta in un posto solo.
_risolvi_iva_riga = make_risolvi_iva_riga(
    error_code=E_PREV_VALIDAZIONE,
    function_name=f"{_FN}._risolvi_iva_riga",
    usa_auth_user=True,
)




# Scopo: Aggiunge riga al preventivo con guard su stato + ricalcolo totali.
#        Auto-fill prezzo da resolver v5 (Sprint 2 B+L1): se il payload non
#        specifica `prezzo_unitario`, viene risolto automaticamente tramite
#        `PricingService.resolve_prezzo`. Se il caller passa un prezzo
#        diverso dal suggerito, serve il permesso di azione processo
#        `prezzo_override_manuale`; altrimenti `E_PRICING_OVERRIDE_NON_AUTORIZZATO`.
#        Tracciamento sempre in `meta.prezzo_resolver_context`.
#
#        L3 (Sprint E): se payload contiene `richiesta_approvazione=true`
#        e il prezzo viola L2, la riga viene salvata con
#        `stato_approvazione_prezzo='PENDING'` collegata a una pratica
#        di approvazione (workflow vendite §14.6) invece di sollevare errore.
@transaction.atomic
def gestisci_riga(
    preventivo_id: int,
    payload: dict[str, Any],
    *,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    _V.validate_allowed_keys(payload, allowed=CREATE_KEYS_RIGA, function_name=f"{_FN}.gestisci_riga")
    repo = PreventiviRepository()
    testata = _get_testata_or_raise(repo, preventivo_id, op="gestisci_riga")
    richiedi_righe_in_bozza(
        testata, documento=SORGENTE_PREVENTIVO, documento_id=preventivo_id, verbo="aggiungere",
        function_name=f"{_FN}.gestisci_riga",
    )

    articolo_id = payload.get("articolo_id")
    ErrorManager.require(
        articolo_id is not None,
        code=E_PREV_VALIDAZIONE,
        message="articolo_id obbligatorio.",
        function_name=f"{_FN}.gestisci_riga",
    )
    assert articolo_id is not None

    # Validazione vincoli economici (prezzo >= 0, quantita > 0) prima del
    # resolver: anticipa i CHECK DB con messaggio parlante.
    _validate_riga_economic(payload, function_name=f"{_FN}.gestisci_riga")
    # La FORMA della data di consegna si controlla QUI, con le altre
    # validazioni di payload, e non al momento dell'INSERT: fra i due punti
    # stanno il resolver del prezzo, il gate L2 e la richiesta L3, che crea
    # una pratica e MANDA UN'EMAIL (side-effect fuori dalla transazione) — una
    # data malformata scoperta dopo avrebbe spedito l'avviso di una pratica
    # poi annullata dal rollback.
    data_consegna_richiesta = _data_consegna_da_payload(
        payload, function_name=f"{_FN}.gestisci_riga",
    )

    # Gating L1 sui componenti_overrides (form atomic 2026-05-12): se il
    # payload contiene overrides ma l'operatore non ha l'azione
    # prezzo_override_manuale, solleva 403 prima di toccare DB.
    validate_componenti_overrides_authorization(
        payload, auth_user_id, function_name=f"{_FN}.gestisci_riga",
    )

    uom_id = payload.get("uom_operativa_id")
    payload_prezzo = payload.get("prezzo_unitario")
    richiesta_approvazione = _V.optional_bool(payload, "richiesta_approvazione") is True
    prezzo_finale, prezzo_meta = _resolve_or_check_override_prezzo(
        testata=testata,
        articolo_id=articolo_id,
        uom_id=uom_id,
        payload_prezzo=payload_prezzo,
        auth_user_id=auth_user_id,
        function_name=f"{_FN}.gestisci_riga",
        richiesta_approvazione=richiesta_approvazione,
    )

    # Padre composito (modello unificato 2026-05-13): il FE omette
    # `prezzo_unitario` perche' il prezzo padre e' SUM(figli × coeff_qta)
    # calcolata dal trigger DB `_z90_ricalcola_padre` post-init componenti.
    # Il resolver `fn_resolve_prezzo_listino_v2` non risolve per articoli
    # compositi (errore: nessun listino diretto sul composito,
    # `E_LISTINO_RIGA_COMPOSITO_VIETATO` lato DB). Default a 0 come
    # placeholder: il trigger lo sovrascrive sincrono dopo
    # `fn_preventivo_riga_componenti_init` nello stesso `@transaction.atomic`.
    # Senza default: NOT NULL violation -> E_DATABASE generico.
    # NB: per articoli NON compositi senza prezzo, il `canSave` FE blocca
    # prima dell'invio; defense-in-depth lato BE: il valido_riga_economic
    # accetta prezzo None (skip), poi qui rilanciamo errore parlante.
    if prezzo_finale is None:
        if articolo_id and repo.is_articolo_composito(str(articolo_id)):
            prezzo_finale = Decimal("0")
        else:
            ErrorManager.require(
                False,
                code=E_PREV_VALIDAZIONE,
                message="Prezzo unitario obbligatorio per articoli non compositi.",
                detail=f"articolo_id={articolo_id}",
                function_name=f"{_FN}.gestisci_riga",
            )

    # Merge meta esistente del payload con audit prezzo.
    merged_meta = _coerce_meta_to_dict(payload.get("meta"))
    if prezzo_meta is not None:
        merged_meta.update(prezzo_meta)

    # Workflow L3: se la chiamata ha attivato richiesta_approvazione e il
    # prezzo viola L2, crea la pratica PRIMA dell'INSERT riga per ottenere
    # pratica_id da inserire come FK. Tutto in transazione atomica del
    # decorator: failure post-pratica annulla anche la riga.
    pratica_id_l3: int | None = None
    stato_approvazione: str | None = None
    if prezzo_meta and prezzo_meta.get("richiesta_approvazione_pending"):
        pratica_id_l3 = _orchestrate_l3_request(
            preventivo_id=preventivo_id,
            articolo_id=articolo_id,
            prezzo_finale=prezzo_finale,
            prezzo_meta=prezzo_meta,
            auth_user_id=auth_user_id,
            # riga_id non noto: link post-create_riga.
        )
        stato_approvazione = STATO_APPROVAZIONE_PENDING

    # Modello qta_operativa-sorgente (refactor 2026-05-31): il FE invia
    # `qta_operativa` (UoM operativa scelta) + `uom_operativa_id`; il trigger DB
    # `trgfn_qta_from_operativa` deriva `quantita` (base) e riempie
    # `factor_to_base` dalla mappa UoM. Il BE non deriva piu' nulla e NON invia
    # `quantita` (colonna derivata, calcolata dal DB). Allineato a contratti/offerte.
    # ⭐ L'IVA DI RIGA VIENE DALLA SEDE UNICA (I3, 2026-08-31).
    # ⛔ `payload_iva_id=None` da `I6`: la casella e' chiusa, quindi non c'e'
    #    piu' nessuna scelta manuale da rispettare e la risoluzione e'
    #    AUTORITATIVA — i suoi errori PASSANO. Meglio fermarsi che scrivere
    #    un'aliquota inventata su un documento che diventera' fiscale.
    iva_id_riga, iva_meta = _risolvi_iva_riga(
        testata,
        articolo_id=str(articolo_id),
        payload_iva_id=None,
        auth_user_id=auth_user_id,
    )
    if iva_meta:
        merged_meta = {**(merged_meta or {}), **iva_meta}

    result = repo.create_riga(
        preventivo_id=preventivo_id,
        articolo_id=articolo_id,
        descrizione=payload.get("descrizione"),
        quantita=None,
        qta_operativa=payload.get("qta_operativa"),
        uom_operativa_id=uom_id,
        factor_to_base=payload.get("factor_to_base"),
        prezzo_unitario=prezzo_finale,
        sconto_percentuale=payload.get("sconto_percentuale"),
        iva_id=iva_id_riga,
        ordine=payload.get("ordine"),
        meta=merged_meta or None,
        stato_approvazione_prezzo=stato_approvazione,
        pratica_approvazione_prezzo_id=pratica_id_l3,
        data_consegna_richiesta_cliente=data_consegna_richiesta,
    )
    # L3: registra riga_id nel meta della pratica per permettere all'approver
    # di risalire alla riga dalla coda (UI ApprovazioniPrezzoListView).
    # Update post-create_riga: la pratica esisteva gia' ma riga_id non era noto.
    if pratica_id_l3 is not None and result.get("id"):
        from apps.vendite.services.approvazioni_prezzo_service import (
            link_riga_a_pratica,
        )
        link_riga_a_pratica(pratica_id=pratica_id_l3, riga_id=int(result["id"]))

    # Init componenti BoM CASO A (refactor componenti, 2026-05-11).
    # La fn DB e' idempotente e gestisce il caso "articolo non composito"
    # come no-op (ritorna 0). La fn DB richiede emittente_sr_id NOT NULL.
    #
    # Risoluzione emittente in 2 step (precedenza preventivo > operatore):
    #  1) Se il preventivo ha `emittente_fiscale_id` esplicito (caso admin
    #     globale che ha settato l'emittente nel payload, o operatore che
    #     ha cambiato emittente del preventivo), uso quello. Altrimenti:
    #  2) Fallback all'emittente assegnato all'operatore (operatore singolo
    #     emittente: il preventivo eredita).
    # Senza emittente da nessuna fonte (admin globale + preventivo senza
    # emittente esplicito) lo skip silenzioso resta — caso edge per cui
    # non sappiamo come pricing.
    # Il prezzo_unitario della riga padre verra' immediatamente
    # sovrascritto dal trigger DB di ricalcolo se almeno un componente
    # viene creato (CASO A). CASO B: prezzo padre invariato.
    # Vedi guida `gestione-listini.md` §5.2.1 e brief DB.
    riga_id_created = result.get("id")
    data_riferimento_str = testata.get("data")
    if riga_id_created is not None and data_riferimento_str is not None:
        emittente_sr_id = resolve_emittente_sr_id_for_testata(
            testata, auth_user_id,
            repo_get_sr_id_by_fiscale_id=repo.get_emittente_sr_id_by_fiscale_id,
        )
        if emittente_sr_id is not None:
            # Form atomic (decisione di dominio 2026-05-12): il FE invia
            # `componenti_overrides` raccolti nel drawer riga in 2 step.
            # Mappa {componente_id_uuid: prezzo}. Il caller deve aver
            # gia' applicato il gating L1 (prezzo_override_manuale): vedi
            # _validate_componenti_overrides_authorization sopra. Senza
            # overrides equivale al comportamento strict (resolver mancante
            # -> raise E_DOC_COMPONENTE_LISTINO_MANCANTE).
            componenti_overrides = normalize_componenti_overrides(
                payload.get("componenti_overrides"),
                function_name=f"{_FN}.gestisci_riga",
                error_code=E_PREV_VALIDAZIONE,
            )
            # Mappa attivazioni opzionali (modello unificato 2026-05-13):
            # default DB inserisce obbligatori `attivo=TRUE` e opzionali
            # `attivo=FALSE`; l'operatore puo' sovrascrivere via
            # `componenti_attivazioni`. Disattivare obbligatori e' bloccato
            # dal trigger guard DB.
            componenti_attivazioni = normalize_componenti_attivazioni(
                payload.get("componenti_attivazioni"),
                function_name=f"{_FN}.gestisci_riga",
                error_code=E_PREV_VALIDAZIONE,
            )
            repo.init_componenti_riga(
                riga_id=int(riga_id_created),
                emittente_soggetto_ruolo_id=emittente_sr_id,
                data_riferimento=date.fromisoformat(str(data_riferimento_str)),
                componenti_overrides=componenti_overrides,
                componenti_attivazioni=componenti_attivazioni,
            )

    # Ricalcolo totali gestito da trigger DB AFTER su preventivi_righe
    return result


# Note: gestisci_riga e aggiorna_riga condividono la fase di orchestrazione
# L3 (creazione pratica + salvataggio PENDING). Per la create il pratica_id
# viene ottenuto PRIMA di create_riga (FK necessaria) e il link riga<->pratica
# avviene DOPO (riga_id non noto prima dell'insert). Per la update il
# riga_id e' gia' noto: link_riga_a_pratica puo' essere invocato subito.
# Vedi _orchestrate_l3_request sopra.


# Scopo: Aggiorna riga esistente con guard su stato + ricalcolo totali.
#        L1 override prezzo: se il payload modifica `prezzo_unitario`,
#        verifica che il valore passato sia il prezzo resolver o che
#        l'operatore abbia permesso di override (azione
#        `prezzo_override_manuale`). La verifica viene fatta solo se
#        `prezzo_unitario` e' esplicitamente nel payload (campo modificato).
#
#        L3 (Sprint E): se payload contiene `richiesta_approvazione=true`
#        e il nuovo prezzo viola L2, la riga viene aggiornata con
#        `stato_approvazione_prezzo='PENDING'` e collegata a una pratica
#        di approvazione. Una riga gia' PENDING e' bloccata dal trigger DB
#        (DB-E-5): l'admin deve attendere esito o annullare la richiesta.
@transaction.atomic
def aggiorna_riga(
    preventivo_id: int,
    riga_id: int,
    payload: dict[str, Any],
    *,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = _get_testata_or_raise(repo, preventivo_id, op="aggiorna_riga")
    richiedi_righe_in_bozza(
        testata, documento=SORGENTE_PREVENTIVO, documento_id=preventivo_id, verbo="modificare",
        function_name=f"{_FN}.aggiorna_riga",
    )
    # ⛔ La riga dev'essere DEL preventivo dell'URL: la bozza appena verificata
    #    e' quella del preventivo chiesto, e l'UPDATE va per il solo `riga_id`.
    #    Senza, una riga di un altro preventivo si modificava con il controllo
    #    di stato fatto sul documento sbagliato.
    riga_esistente = riga_del_padre_o_not_found(
        repo.get_riga, riga_id, padre_id=preventivo_id, chiave_padre="preventivo_id",
        code="E_PREV_RIGA_NOT_FOUND", message="Riga preventivo non trovata.",
        function_name=f"{_FN}.aggiorna_riga",
    )

    # Validazione vincoli economici: anticipa i CHECK DB con messaggio
    # parlante. In update i campi possono essere assenti: il helper li
    # ignora se non presenti nel payload.
    _validate_riga_economic(payload, function_name=f"{_FN}.aggiorna_riga")

    # Guard "componenti via PATCH riga": il drawer FE puo' riusare lo
    # stesso payload del CREATE per re-applicare scelte sui componenti,
    # ma la PATCH riga e' solo testata. Senza guard quei due campi
    # verrebbero scartati silenziosamente da `update_fields` (whitelist).
    # Path corretto per modificare i componenti: endpoint dedicati
    # `/preventivi/<id>/righe/<riga_id>/componenti/<componente_id>/`
    # (PATCH/DELETE singoli) — vedi Fase D del piano refactor-componenti.
    for _campo_componenti in ("componenti_overrides", "componenti_attivazioni"):
        ErrorManager.require(
            _campo_componenti not in payload,
            code=E_PREV_VALIDAZIONE,
            message=(
                f"Campo '{_campo_componenti}' non ammesso in PATCH riga: "
                "modifica componenti via endpoint dedicato "
                "/righe/<riga_id>/componenti/."
            ),
            function_name=f"{_FN}.aggiorna_riga",
        )

    # ⛔ Dopo il rifiuto parlante dei componenti, ogni altra chiave ignota e' un
    #    400 (2026-10-20): prima la PATCH riga la scartava in silenzio. Oltre
    #    alle colonne, le chiavi lette a parte (la stessa costante dello schema).
    _V.validate_allowed_keys(
        payload, allowed=UPDATE_KEYS_RIGA | UPDATE_RIGA_LETTE_A_PARTE,
        function_name=f"{_FN}.aggiorna_riga",
    )
    richiesta_approvazione = _V.optional_bool(payload, "richiesta_approvazione") is True
    update_fields: dict[str, Any] = {}
    # `quantita` (base) e' derivata dal trigger e non e' aggiornabile dal client:
    # la sorgente e' `qta_operativa`.
    # ⛔ `iva_id` NON C'E' PIU' (`I6`, 2026-08-31): l'aliquota la decide il
    #    risolutore e la casella a video e' spenta.
    # ⚠️ E non si ri-risolve in UPDATE, ed e' corretto: `articolo_id` non e' in
    #    questo elenco — l'articolo di una riga non si cambia — quindi non c'e'
    #    niente, qui, che possa spostare la risposta.
    for key in UPDATE_KEYS_RIGA:
        if key in payload:
            update_fields[key] = payload[key]
    # La data di consegna richiesta: presente nel payload -> si scrive (anche
    # `null`, che azzera); assente -> non si tocca.
    if _CHIAVE_DATA_CONSEGNA in payload:
        update_fields[_CHIAVE_DATA_CONSEGNA] = _data_consegna_da_payload(
            payload, function_name=f"{_FN}.aggiorna_riga",
        )

    pratica_id_l3: int | None = None

    # L1 check + audit meta se prezzo toccato esplicitamente. Serve contesto
    # riga esistente (`riga_esistente`, letta sopra) per articolo_id/uom_id
    # non sempre presenti nel payload.
    if "prezzo_unitario" in update_fields:
        articolo_id = riga_esistente["articolo_id"]
        uom_id = update_fields.get("uom_operativa_id") or riga_esistente.get("uom_operativa_id")
        prezzo_finale, prezzo_meta = _resolve_or_check_override_prezzo(
            testata=testata,
            articolo_id=articolo_id,
            uom_id=uom_id,
            payload_prezzo=update_fields["prezzo_unitario"],
            auth_user_id=auth_user_id,
            function_name=f"{_FN}.aggiorna_riga",
            richiesta_approvazione=richiesta_approvazione,
        )
        update_fields["prezzo_unitario"] = prezzo_finale
        if prezzo_meta is not None:
            # `meta` puo' arrivare come dict (caso normale: psycopg deserializza
            # jsonb) o come stringa JSON (regressione di adapter / payload FE
            # serializzato). _coerce_meta_to_dict normalizza entrambi i casi
            # ed evita il classico ValueError "dictionary update sequence
            # element #0 has length 1; 2 is required".
            base = update_fields.get("meta")
            if not base:
                base = riga_esistente.get("meta")
            merged_meta = _coerce_meta_to_dict(base)
            merged_meta.update(prezzo_meta)
            update_fields["meta"] = merged_meta

        # Workflow L3: violazione L2 + flag richiesta_approvazione=true
        # -> crea pratica e salva PENDING. Helper condiviso con gestisci_riga.
        # Per update il riga_id e' gia' noto: link riga<->pratica eseguito dentro l'helper.
        if prezzo_meta and prezzo_meta.get("richiesta_approvazione_pending"):
            pratica_id_l3 = _orchestrate_l3_request(
                preventivo_id=preventivo_id,
                articolo_id=articolo_id,
                prezzo_finale=prezzo_finale,
                prezzo_meta=prezzo_meta,
                auth_user_id=auth_user_id,
                riga_id_for_link=riga_id,
            )
            update_fields["stato_approvazione_prezzo"] = STATO_APPROVAZIONE_PENDING
            update_fields["pratica_approvazione_prezzo_id"] = pratica_id_l3
        else:
            # Auto-reset stato approvazione: l'operatore ha modificato il prezzo
            # e il nuovo valore non richiede approvazione (resolver applicabile
            # o override entro L2). Se la riga era REJECTED/APPROVED il flag
            # era riferito al prezzo precedente — non e' piu' valido. Il reset
            # sblocca il preventivo (un REJECTED blocca Emetti/Accetta a DB,
            # script.fn_check_prezzi_autorizzati) e permette di emettere senza
            # che il vecchio rifiuto resti come blocco fantasma.
            #
            # Cleanup denormalizzato meta: rimuoviamo `approvazione_rifiuto`
            # (motivazione precedente irrilevante post-correzione).
            stato_attuale = riga_esistente.get("stato_approvazione_prezzo")
            if stato_attuale in {STATO_APPROVAZIONE_REJECTED, STATO_APPROVAZIONE_APPROVED}:
                update_fields["stato_approvazione_prezzo"] = None
                update_fields["pratica_approvazione_prezzo_id"] = None
                cleanup_meta = update_fields.get("meta")
                if isinstance(cleanup_meta, dict) and "approvazione_rifiuto" in cleanup_meta:
                    cleanup_meta.pop("approvazione_rifiuto", None)
                    update_fields["meta"] = cleanup_meta

    # `qta_operativa` (sorgente) arriva diretta dal FE; il trigger DB ricalcola
    # `quantita` (base) + `factor_to_base`. Nessuna derivazione lato BE.

    if update_fields:
        updated = repo.update_riga(riga_id, **update_fields)
        ErrorManager.require(
            updated,
            code="E_PREV_RIGA_NOT_FOUND",
            message="Riga preventivo non trovata.",
            detail=f"riga_id={riga_id}",
            function_name=f"{_FN}.aggiorna_riga",
        )
        # Ricalcolo totali gestito da trigger DB AFTER su preventivi_righe

    # Nota: il link riga<->pratica e' gia' stato eseguito dentro
    # _orchestrate_l3_request (riga_id_for_link=riga_id).
    #
    # Cambio articolo padre: NON gestito qui per design. `articolo_id` non
    # e' nella whitelist `update_fields` sopra — la regola del dominio e'
    # "articolo immutabile post-create" (l'operatore elimina + ricrea la
    # riga). Quindi i componenti CASO A iniziali dell'init (gestisci_riga)
    # restano coerenti per tutta la vita della riga.

    return {"status": "ok", "riga_id": riga_id}


# Scopo: Helper condiviso gestisci_riga / aggiorna_riga per la risoluzione
#        del prezzo via resolver v5 + check L1 override + costruzione meta
#        audit. Vive qui per evitare duplicazione tra create e update.
#
#        Comportamento:
#        - se payload_prezzo e' None -> auto-fill dal resolver, origine
#          = valore del resolver (PROMO/CONTRATTO_*/CATEGORIA)
#        - se payload_prezzo == resolver_prezzo -> OK, origine resolver
#        - se payload_prezzo != resolver_prezzo -> check azione
#          prezzo_override_manuale; se negato E_PRICING_OVERRIDE_NON_AUTORIZZATO
#        - meta audit sempre popolato con prezzo_resolver_context
#
#        Ritorna (prezzo_finale: Decimal|str, meta_patch: dict|None).
#        Se articolo_id/uom_id mancano, salta il resolver e ritorna il
#        prezzo del payload (retrocompatibilita': non tutti i preventivi
#        hanno UoM configurata — il resolver e' best-effort).
# Scopo: orchestra la creazione pratica L3 + link riga<->pratica per i flussi
#        di gestisci_riga e aggiorna_riga. Centralizza l'unica logica
#        Sprint E condivisa tra create e update riga (stessa transazione
#        atomica del chiamante: failure annulla anche la riga).
#
#        Restituisce pratica_id (per inserimento FK in create_riga).
#        Per update_riga, riga_id e' gia' noto: passare apply_link=True
#        per fare update meta pratica con riga_preventivo_id.
def _orchestrate_l3_request(
    *,
    preventivo_id: int,
    articolo_id: Any,
    prezzo_finale: Any,
    prezzo_meta: dict[str, Any],
    auth_user_id: int | None,
    riga_id_for_link: int | None = None,
) -> int:
    from apps.vendite.services.approvazioni_prezzo_service import (
        crea_richiesta_approvazione,
        link_riga_a_pratica,
    )
    pratica_id = crea_richiesta_approvazione(
        preventivo_id=preventivo_id,
        articolo_id=str(articolo_id),
        prezzo_resolver=Decimal(prezzo_meta["prezzo_base_resolver"])
        if prezzo_meta.get("prezzo_base_resolver") else None,
        prezzo_manuale=Decimal(str(prezzo_finale)),
        violazione=prezzo_meta["violazione_l2"],
        auth_user_id=auth_user_id,
    )
    if riga_id_for_link is not None:
        link_riga_a_pratica(pratica_id=pratica_id, riga_id=riga_id_for_link)
    return pratica_id


# Scopo: Normalizza `meta` a dict, accettando dict (caso normale: psycopg
#        deserializza jsonb), stringa JSON (caso regressione adapter o
#        payload FE serializzato in stringa) o None/falsy (→ dict vuoto).
#        Senza questa normalizzazione, `dict("...")` su una stringa solleva
#        ValueError "dictionary update sequence element #0 has length 1;
#        2 is required" che il middleware traduce in E_VALIDATION_INPUT,
#        mascherando il vero problema (un meta serializzato non riconosciuto).
def _coerce_meta_to_dict(value: Any) -> dict[str, Any]:
    if value is None or value == "" or value == {}:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        # Tentativo di parsing JSON. Stringa malformata → dict vuoto:
        # non bloccante, il merge col prezzo_meta avviene comunque.
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    # Tipo inatteso (lista, numero, bool): fallback dict vuoto.
    return {}


# Scopo: Validazione lato BE dei vincoli economici di una riga preventivo
#        prima del resolver/INSERT/UPDATE. Anticipa i CHECK constraint DB
#        (`chk_prevrighe_quantita_prezzo`: prezzo >= 0 AND quantita > 0)
#        per restituire un errore parlante invece dell'E_DATABASE generico
#        che il middleware mostrerebbe sul violation Postgres.
#        Chiamata sia da gestisci_riga (create) sia da aggiorna_riga (update).
#        Salta i campi assenti dal payload: in update non tutti i campi
#        passano sempre.
#        ⚠️ La coercizione (da `str`, bool e NaN rifiutati) e' del BB
#        `PayloadValidator`: fino al 2026-09-18 le due copie inline qui sotto
#        costruivano `Decimal("NaN")` senza protestare, e `NaN >= 0` solleva
#        `InvalidOperation` — un 500 al posto del 400 col campo — mentre
#        `NaN != 0` e' vero, quindi una quantita' NaN passava fino al DB, dove
#        `NaN > 0` e' vero e il CHECK la lascia entrare. Qui restano i guard
#        stretti di dominio, con la loro frase.
def _validate_riga_economic(payload: dict[str, Any], *, function_name: str) -> None:
    prezzo = _V.optional_decimal(
        payload, "prezzo_unitario",
        message="Prezzo unitario non numerico.", function_name=function_name,
    )
    if prezzo is not None:
        ErrorManager.require(
            prezzo >= 0,
            code=E_PREV_VALIDAZIONE,
            message="Il prezzo unitario non puo' essere negativo.",
            detail=f"prezzo_unitario={payload['prezzo_unitario']!r}",
            context={"field": "prezzo_unitario"},
            function_name=function_name,
        )

    # Sorgente quantita = `qta_operativa` (UoM operativa scelta dall'operatore);
    # `quantita` (base) e' derivata dal trigger DB e non arriva piu' dal FE.
    qta_operativa = _V.optional_decimal(
        payload, "qta_operativa",
        message="Quantita' non numerica.", function_name=function_name,
    )
    if qta_operativa is not None:
        ErrorManager.require(
            qta_operativa != 0,
            code=E_PREV_VALIDAZIONE,
            message="La quantita' deve essere diversa da zero.",
            detail=f"qta_operativa={payload['qta_operativa']!r}",
            context={"field": "qta_operativa"},
            function_name=function_name,
        )


# Scopo: Thin wrapper sul BB `resolve_or_check_override_prezzo` (estratto
#        2026-05-15 per simmetria preventivi/contratti). La logica di
#        orchestrazione dei 3 gate (L1+L2+L3) vive in
#        `_pricing_gate_helpers.resolve_or_check_override_prezzo`; qui
#        passiamo direttamente `suggerisci_prezzo_riga` come resolver_fn
#        (la signature `(documento_id, *, articolo_id, uom_id, auth_user_id)`
#        e' gia' quella attesa dal BB — niente adapter intermedio).
#
#        Firma e comportamento INVARIATI rispetto alla versione precedente:
#        tutti i call site dei test continuano a funzionare senza modifica.
def _resolve_or_check_override_prezzo(
    *,
    testata: Mapping[str, Any],
    articolo_id: Any,
    uom_id: Any,
    payload_prezzo: Any,
    auth_user_id: int | None,
    function_name: str,
    richiesta_approvazione: bool = False,
) -> tuple[Any, dict[str, Any] | None]:
    return resolve_or_check_override_prezzo(
        testata=testata,
        articolo_id=articolo_id,
        uom_id=uom_id,
        payload_prezzo=payload_prezzo,
        auth_user_id=auth_user_id,
        function_name=function_name,
        resolver_fn=suggerisci_prezzo_riga,
        error_code_validazione=E_PREV_VALIDAZIONE,
        richiesta_approvazione=richiesta_approvazione,
    )


# Gate autorizzazioni prezzi (L1+L2+L3) estratti come BB condiviso 2026-05-15
# in `apps.vendite.services._pricing_gate_helpers`:
#   - `check_permesso_override_prezzo` (era `_check_permesso_override_prezzo`)
#   - `check_limite_variazione_prezzo` (era `_check_limite_variazione_prezzo`)
#   - `check_limite_variazione_globale` (nuovo, per testata contratto)
# Vedi catalogo BB sezione "Vendite — Gate autorizzazioni prezzi".
# I caller di preventivi importano direttamente dal BB; nessun alias qui.


# Helper componenti BoM estratti in `_componenti_service_helpers.py`
# (refactor Fase H 2026-05-14): `normalize_componenti_overrides`,
# `normalize_componenti_attivazioni`, `resolve_emittente_sr_id_safe`,
# `resolve_emittente_sr_id_for_testata`. Importati al top del modulo.
# I test importano direttamente dal modulo helpers (no piu' alias qui).


# NB: il gating L1 sugli override prezzo componenti (`componenti_overrides`)
# vive ora nel BB condiviso `_pricing_gate_helpers.validate_componenti_overrides_authorization`
# (estratto 2026-06-01, regola del 2: riusato da preventivi/contratti/offerte).


# Scopo: Estrae l'unico (o primo) emittente_soggetto_ruolo_id autorizzato
#        per l'utente. Helper privato condiviso da `suggerisci_prezzo_riga`
#        (flusso resolver prezzo) e da altri ingressi che richiedono
#        emittente obbligatorio. Solleva E_PREV_VALIDAZIONE se l'utente non
#        e' trovato o non ha emittenti. Modello operatore-emittenti 1-a-1:
#        in pratica la lista ha sempre 1 elemento (a parte admin globali
#        che non passano per qui).
def _resolve_emittente_sr_id_or_raise(
    auth_user_id: int | None, *, function_name: str,
) -> int:
    user_model = get_user_model()
    try:
        # `pk=None` e' ammesso da Django (diventa `IS NULL`, nessuna riga ->
        # DoesNotExist, gestito sotto): e' lo stub a non accettare None.
        user = user_model.objects.get(pk=auth_user_id)  # type: ignore[misc]  # pk=None -> DoesNotExist
    except user_model.DoesNotExist:
        ErrorManager.raise_error(
            code=E_PREV_VALIDAZIONE,
            message="Utente non trovato.",
            detail=f"auth_user_id={auth_user_id}",
            function_name=function_name,
        )
    emittenti_sr = PermissionResolver.get_emittenti_sr_ids(user) or []
    ErrorManager.require(
        len(emittenti_sr) > 0,
        code=E_PREV_VALIDAZIONE,
        message="Impossibile risolvere l'emittente fiscale dell'operatore.",
        detail="L'operatore non ha emittenti autorizzati.",
        function_name=function_name,
    )
    return int(emittenti_sr[0])


#        Uso tipico: chiamata FE all'apertura del drawer riga per
#        pre-compilare il campo prezzo. L'operatore puo' accettare il
#        suggerito o fornire un override (controllato da permesso L1 in
#        gestisci_riga).
#
#        Riferimento: docs/it/dev/work-in-progress/sviluppo-autorizzazioni-prezzi.md
def suggerisci_prezzo_riga(
    preventivo_id: int,
    *,
    # Opzionali: il service li valida da se' (require / guard qui sotto).
    articolo_id: str | None,
    uom_id: int | None,
    auth_user_id: int | None,
) -> dict[str, Any]:
    from apps.vendite.services.pricing_service import PricingService

    function_name = f"{_FN}.suggerisci_prezzo_riga"

    ErrorManager.require(
        articolo_id is not None and str(articolo_id).strip() != "",
        code=E_PREV_VALIDAZIONE,
        message="articolo_id obbligatorio.",
        function_name=function_name,
    )
    guard_uom_id_positive(
        uom_id, error_code=E_PREV_VALIDAZIONE, function_name=function_name,
    )
    ErrorManager.require(
        auth_user_id is not None,
        code=E_PREV_VALIDAZIONE,
        message="auth_user_id obbligatorio per risolvere l'emittente.",
        function_name=function_name,
    )

    repo = PreventiviRepository()
    testata = _get_testata_or_raise(repo, preventivo_id, op="suggerisci_prezzo_riga")
    ErrorManager.require(
        testata.get("billing_account_id") is not None,
        code=E_PREV_VALIDAZIONE,
        message="Preventivo senza billing_account: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    ErrorManager.require(
        testata.get("utility_id") is not None,
        code=E_PREV_VALIDAZIONE,
        message="Preventivo senza utility: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    assert testata["billing_account_id"] is not None

    # Emittente dell'operatore: PermissionResolver ritorna lista (o None=admin).
    # Prendiamo il primo disponibile: per operatori 1-a-1 e' sempre univoco.
    emittente_sr_id = _resolve_emittente_sr_id_or_raise(
        auth_user_id, function_name=function_name,
    )

    # Data di riferimento: data del preventivo (il resolver la usa per
    # selezionare la versione listino attiva, il contratto nel periodo
    # corretto e le promo in vigore).
    data_riferimento_str = testata.get("data")
    ErrorManager.require(
        data_riferimento_str is not None,
        code=E_PREV_VALIDAZIONE,
        message="Preventivo senza data: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    assert data_riferimento_str is not None
    data_riferimento = date.fromisoformat(str(data_riferimento_str))

    # Delega al building block centrale. Gli errori di dominio
    # (E_CATEGORIA_LISTINO_NON_MAPPATA ecc.) sono tradotti dal service
    # e propagati al chiamante come ServiceError.
    # I due require in testa (articolo_id, guard_uom_id_positive) li garantiscono.
    assert articolo_id is not None and uom_id is not None
    result = PricingService().resolve_prezzo(
        articolo_id=articolo_id,
        uom_id=int(uom_id),
        data_riferimento=data_riferimento,
        ba_id=int(testata["billing_account_id"]),
        utility_id=int(testata["utility_id"]),
        emittente_soggetto_ruolo_id=emittente_sr_id,
    )

    # Normalizzazione valori Decimal/date in stringhe per stabilita' JSON.
    from decimal import Decimal
    def _normalize(v: Any) -> Any:
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, date):
            return v.isoformat()
        return v

    return {k: _normalize(v) for k, v in result.items()}


# Scopo: Elimina riga preventivo (HARD DELETE) con guard su stato +
# ricalcolo totali. Pattern simmetrico a `contratti_service.delete_riga`:
# la guard limita l'operazione a DRAFT, dove la riga non e' ancora pushed
# in commessa. Eventuali componenti BoM su `preventivi_righe_componenti`
# vengono puliti automaticamente dal DB via FK ON DELETE CASCADE (no
# trigger UPDATE attivato).
def elimina_riga(preventivo_id: int, riga_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = _get_testata_or_raise(repo, preventivo_id, op="elimina_riga")
    richiedi_righe_in_bozza(
        testata, documento=SORGENTE_PREVENTIVO, documento_id=preventivo_id, verbo="togliere",
        function_name=f"{_FN}.elimina_riga",
    )
    # ⛔ La riga dev'essere DEL preventivo dell'URL (vedi `aggiorna_riga`): il
    #    DELETE va per il solo `riga_id`.
    riga_del_padre_o_not_found(
        repo.get_riga, riga_id, padre_id=preventivo_id, chiave_padre="preventivo_id",
        code="E_PREV_RIGA_NOT_FOUND", message="Riga preventivo non trovata.",
        function_name=f"{_FN}.elimina_riga",
    )

    deleted = repo.delete_riga(riga_id)
    ErrorManager.require(
        deleted,
        code="E_PREV_RIGA_NOT_FOUND",
        message="Riga preventivo non trovata.",
        function_name=f"{_FN}.elimina_riga",
    )
    # Ricalcolo totali gestito da trigger DB AFTER su preventivi_righe
    return {"status": "ok", "riga_id": riga_id}


# Scopo: «Aggiorna date di consegna» del preventivo: la data richiesta dal
#        cliente su piu' righe, in modalita' TUTTE o SOLO_VUOTE
#        (brief-db-date-consegna-righe-in-blocco, D-2, D-4). Segue il lock
#        delle righe (solo bozza), che la rifiuta nello stesso UPDATE. Regola e
#        forma nel BB `_date_consegna_righe`; qui la testata e il codice.
def aggiorna_date_consegna(preventivo_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = PreventiviRepository()
    _get_testata_or_raise(repo, preventivo_id, op="aggiorna_date_consegna")
    with _db_errors("aggiorna_date_consegna"):
        return aggiorna_date_consegna_righe(
            repo, preventivo_id, payload,
            error_code=E_PREV_VALIDAZIONE,
            function_name=f"{_FN}.aggiorna_date_consegna",
        )


# ══════════════════════════════════════════════════════════
#  Componenti BoM CASO A — service pubblico
# ══════════════════════════════════════════════════════════
# Refactor componenti 2026-05-11. Vedi `refactor-componenti.md` +
# `gestione-listini.md` §5.2.1. I componenti vivono in
# `vendite.preventivi_righe_componenti`; `init_componenti_riga` e' chiamato
# automaticamente da `gestisci_riga` / `aggiorna_riga` (cambio articolo).
# Qui le API di consultazione + modifica fine ai singoli componenti.


# Scopo: Preview componenti CASO A per il drawer riga (form atomic
#        2026-05-12). Read-only: il FE invoca PRIMA del save di una riga
#        composita per ottenere i prezzi suggeriti dei componenti esposti.
#        Per ogni componente: prezzo_suggerito + origine_prezzo, oppure
#        NULL + resolver_error_reason se il listino manca. Il FE pre-popola
#        la tabella editabile; l'operatore valorizza i NULL prima del save.
#        Il payload del save include `componenti_overrides` con i prezzi
#        manuali (vedi `gestisci_riga` + gating L1).
#
#        Risoluzione emittente: stesso pattern di `gestisci_riga`
#        (precedenza emittente del preventivo > operatore).
#        Solleva 404 se preventivo non esiste, 422 se data preventivo NULL
#        o emittente non risolvibile.
def preview_componenti_riga(
    preventivo_id: int,
    *,
    articolo_id: str,
    uom_operativa_id: int | None,
    quantita,
    auth_user_id: int | None = None,
) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    testata = _get_testata_or_raise(repo, preventivo_id, op="preview_componenti_riga")
    data_riferimento_str = testata.get("data")
    ErrorManager.require(
        data_riferimento_str is not None,
        code=E_PREV_VALIDAZIONE,
        message="Data preventivo obbligatoria per preview componenti.",
        function_name=f"{_FN}.preview_componenti_riga",
    )
    emittente_sr_id = resolve_emittente_sr_id_for_testata(
        testata, auth_user_id,
        repo_get_sr_id_by_fiscale_id=repo.get_emittente_sr_id_by_fiscale_id,
    )
    ErrorManager.require(
        emittente_sr_id is not None,
        code=E_PREV_VALIDAZIONE,
        message="Impossibile risolvere l'emittente fiscale per la preview.",
        function_name=f"{_FN}.preview_componenti_riga",
    )
    assert emittente_sr_id is not None
    # Guard utility_id: la preview ha senso solo con utility nota (il
    # resolver deriva listino/categoria da (utility, data)). Senza guard
    # un utility_id NULL sarebbe coerciato silenziosamente a 0 e farebbe
    # esplodere la fn DB con un errore poco parlante.
    utility_id_raw = testata.get("utility_id")
    ErrorManager.require(
        utility_id_raw is not None,
        code=E_PREV_VALIDAZIONE,
        message="Utility preventivo obbligatoria per preview componenti.",
        function_name=f"{_FN}.preview_componenti_riga",
    )
    assert utility_id_raw is not None

    return repo.preview_componenti_riga(
        articolo_id=articolo_id,
        uom_id=uom_operativa_id,
        quantita_padre=quantita,
        data_riferimento=date.fromisoformat(str(data_riferimento_str)),
        ba_id=testata.get("billing_account_id"),
        utility_id=int(utility_id_raw),
        emittente_soggetto_ruolo_id=emittente_sr_id,
    )


# Scopo: Lista componenti BoM di una riga padre composita per la UI.
#        Guard di esistenza: riga padre deve esistere ed appartenere al
#        preventivo richiesto.
#        `solo_attivi=True` (default backcompat — expander tabella righe
#        readonly): solo componenti `attivo=TRUE`.
#        `solo_attivi=False` (EDIT panel): include anche opzionali
#        disattivati, per permettere all'operatore di riattivarli.
def list_componenti_riga(
    preventivo_id: int, riga_id: int, *, solo_attivi: bool = True,
) -> list[dict[str, Any]]:
    repo = PreventiviRepository()
    riga_del_padre_o_not_found(
        repo.get_riga, riga_id, padre_id=preventivo_id, chiave_padre="preventivo_id",
        code="E_PREV_RIGA_NOT_FOUND", message="Riga preventivo non trovata.",
        function_name=f"{_FN}.list_componenti_riga",
    )
    return repo.list_componenti_riga(riga_id, solo_attivi=solo_attivi)


# Scopo: Helper privato condiviso da update/delete componente. Esegue
#        guard + scope check (riga_id URL + preventivo_id) + stato
#        preventivo modificabile in UN'unica query JOIN
#        componente→riga→preventivo (Fix #2 perf, refactor-componenti.md).
#        Solleva `E_PREV_COMPONENTE_NOT_FOUND` su componente inesistente
#        o fuori scope, `E_RIGA_DOC_NON_BOZZA` (BB `richiedi_righe_in_bozza`,
#        col `verbo` del chiamante) se il preventivo non e' in bozza.
#        Defense-in-depth: scope check sia su `riga_id` (anti-tampering
#        URL) sia su `preventivo_id` via JOIN runtime.
def _load_componente_for_modification(
    repo: PreventiviRepository,
    *,
    preventivo_id: int,
    riga_id: int,
    componente_id: int,
    verbo: Verbo,
    function_name: str,
) -> None:
    scope = repo.load_componente_with_scope(componente_id)
    ErrorManager.require(
        scope is not None,
        code="E_PREV_COMPONENTE_NOT_FOUND",
        message="Componente non trovato.",
        detail=f"componente_id={componente_id}",
        function_name=function_name,
    )
    assert scope is not None

    # Anti-tampering URL: il `riga_id` dalla rotta deve matchare la riga
    # padre reale del componente.
    riga_reale = int(scope["riga_preventivo_id"])
    ErrorManager.require(
        riga_reale == riga_id,
        code="E_PREV_COMPONENTE_NOT_FOUND",
        message="Componente non trovato.",
        detail=(
            f"componente_id={componente_id} non appartiene a "
            f"riga_id={riga_id} (riga reale={riga_reale})"
        ),
        function_name=function_name,
    )

    # Scope preventivo: defense-in-depth contro URL forgiati.
    ErrorManager.require(
        int(scope["preventivo_id"]) == preventivo_id,
        code="E_PREV_COMPONENTE_NOT_FOUND",
        message="Componente non trovato.",
        detail=(
            f"componente_id={componente_id} fuori scope "
            f"preventivo_id={preventivo_id}"
        ),
        function_name=function_name,
    )

    # Guard stato modificabile: il JOIN porta gia' lo stato — niente
    # round-trip extra a `get_preventivo`.
    richiedi_righe_in_bozza(
        scope, documento=SORGENTE_PREVENTIVO, documento_id=preventivo_id, verbo=verbo,
        function_name=function_name,
    )


# Scopo: Modifica componente esistente. Guard stato preventivo modificabile
#        + esistenza componente + match URL anti-tampering. Whitelist campi
#        via repo.
#        TODO (post-smoke iniziale): L1/L2/L3 sui componenti come per la
#        riga padre. Oggi accettiamo qualsiasi `prezzo_unitario` se il
#        preventivo e' modificabile — sufficiente per UI di test (3.4.A/B/C
#        in `sviluppo-listini-v5-test-ui.md`). Il trigger DB di guard
#        PENDING `trgfn_preventivi_righe_componenti_guard_pending` resta
#        come safety net.
def update_componente(
    preventivo_id: int,
    riga_id: int,
    componente_id: int,
    payload: dict[str, Any],
    *,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    repo = PreventiviRepository()
    _load_componente_for_modification(
        repo,
        preventivo_id=preventivo_id, riga_id=riga_id, componente_id=componente_id,
        verbo="modificare", function_name=f"{_FN}.update_componente",
    )

    # ⛔ Contratto dell'OPERATORE (BB unico per i cinque documenti), non la
    #    whitelist del repository: fino al 2026-09-26 qui si validava contro
    #    `COMPONENTE_UPDATE_ALLOWED`, che contiene `stato_approvazione_prezzo`
    #    — un operatore poteva approvarsi da solo un prezzo L3 PENDING.
    #    `origine_prezzo` la deriva il server dal prezzo.
    # Il prezzo_unitario del padre verra' ricalcolato dal trigger DB.
    data = dati_patch_componente(
        payload, auth_user_id=auth_user_id, function_name=f"{_FN}.update_componente",
        error_code=E_PREV_VALIDAZIONE,
    )
    repo.update_componente(componente_id, **data)
    return {"status": "ok", "componente_id": componente_id}


# Scopo: Soft delete componente (`attivo=FALSE`). Guard stato + esistenza
#        + match URL anti-tampering. Il trigger DB di ricalcolo padre
#        esclude i componenti inattivi dalla SUM, quindi il prezzo padre
#        si aggiorna in automatico.
def delete_componente(
    preventivo_id: int, riga_id: int, componente_id: int,
) -> dict[str, Any]:
    repo = PreventiviRepository()
    _load_componente_for_modification(
        repo,
        preventivo_id=preventivo_id, riga_id=riga_id, componente_id=componente_id,
        verbo="togliere", function_name=f"{_FN}.delete_componente",
    )
    deleted = repo.delete_componente(componente_id)
    # idempotenza: se gia' soft-deleted ritorna False — non e' errore qui.
    return {"status": "ok", "componente_id": componente_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  INTEGRAZIONE — Commesse / Fatturazione
# ══════════════════════════════════════════════════════════


# Scopo: Push preventivo accettato in commessa per pipeline fatturazione.
# Obiettivo: guard stato ACCETTATO + discovery righe eleggibili, poi delega
# al CommessaPushOrchestrator filtrato sul singolo preventivo
# (`pr_run_commesse_push_one(sorgente_codice='PREVENTIVO', sorgente_uid=preventivo_id)`).
# Perimetro: questa fn copre solo la Fase 1 (commesse_attivita); l'emit
# verso attivita_fatturabili (Fase 3) per preventivi `fatturazione_immediata=TRUE`
# e' tracciato in PR2 (vedi WIP sviluppo-push-singolo-preventivo §9).
# Idempotente via segment_key sul layer DB (lo gestisce fn_upsert_commessa_attivita).
# `righe_ids` (opzionale): sottoinsieme righe servizio da pushare (smistamento
# selettivo dal Pannello Smistamento); None = tutte le eleggibili.
def push_a_commessa(
    preventivo_id: int, righe_ids: list[int] | None = None,
) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = _get_testata_or_raise(repo, preventivo_id, op="push_a_commessa")
    ErrorManager.require(
        e_stato_di_accettazione(TESTATA_PREVENTIVI, testata["stato_codice_interno"]),
        code="E_PREV_STATO_TRANSIZIONE",
        message="Solo preventivi ACCETTATI possono essere inviati a fatturazione.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.push_a_commessa",
    )
    righe_count = repo.count_righe_pushable(preventivo_id)
    ErrorManager.require(
        righe_count > 0,
        code="E_PREV_NESSUNA_RIGA",
        message="Nessuna riga eleggibile per fatturazione.",
        detail=f"preventivo_id={preventivo_id}",
        function_name=f"{_FN}.push_a_commessa",
    )

    # Delega al CommessaPushOrchestrator filtrato: scrive commesse + righe
    # via fn DB esistenti, logga su commesse_push_log.
    # Import locale per evitare ciclo (commesse_service importa repo che importa
    # preventivi_repository in altri punti).
    from apps.vendite.services.commesse_service import pr_run_commesse_push_one

    # Fix analisi-fix-transazioni #5 (Classe B): push + aggancio commessa-servizi
    # alla pratica in UN solo transaction.atomic(). Prima erano scritture
    # autocommit separate: se `_aggancia_commessa_servizi_a_pratica` falliva
    # DOPO il push, le commesse (+ ponte emittibilita') restavano committate ma
    # il ramo servizi non agganciato alla pratica (orfano). Ora un fallimento
    # dell'aggancio rolla TUTTO il push, che e' idempotente/ri-eseguibile
    # (advisory lock + dedup segment_key → retry sicuro). L'atomic interno di
    # `pr_run_commesse_push_one` diventa un savepoint annidato.
    # ⭐ Il passaggio ACCETTATO → EVASO lo fa il DB (D-10 / R-8 di
    #    brief-db-annullo-a-valle-riapre-a-monte, 2026-10-12): il trigger delle
    #    righe di commessa riproietta il preventivo dal residuo sulle due strade
    #    (`vendite.fn_preventivo_proietta_stato_smistamento`), nella stessa
    #    transazione dell'invio. E' la stessa sede che lo riporta ad ACCETTATO
    #    quando la commessa si annulla. Fino a quel giorno lo faceva qui il
    #    backend, «best-effort» (`transiziona_a_evaso_se_smistato`, ritirato).
    with transaction.atomic():
        report = pr_run_commesse_push_one(
            sorgente_codice=SORGENTE_PREVENTIVO,
            sorgente_uid=preventivo_id,
            righe_ids=righe_ids,
        )

        if report["stato"] == "COMPLETATO":
            # Aggancio del RAMO SERVIZI dello split (rev.3 bivio-per-esito): lo
            # split standalone e' il punto d'aggancio di ENTRAMBI i rami.
            # post_smistamento e' merce-only (retro-aggancio ordine), quindi la
            # commessa-servizi la lega qui — senza, sul ramo SOLO_SERVIZI la pratica
            # resterebbe priva del link commessa. No-op se il preventivo non nasce da
            # una pratica. NON best-effort: un fallimento qui rolla l'intero push.
            _aggancia_commessa_servizi_a_pratica(preventivo_id, str(testata["uid"]))

    return {
        "preventivo_id": preventivo_id,
        "stato": report["stato"],
        "push_log_id": report["push_log_id"],
        "durata_ms": report["durata_ms"],
        "handlers": report["handlers"],
        # Commesse toccate dal push (gia' rese emittibili dal ponte in
        # pr_run_commesse_push_one): il FE puo' navigare/ispezionare.
        "commesse_ids": report.get("commesse_ids", []),
        # Diagnostico pre-push: utile a confronto con il delta operato dall'orchestrator.
        "righe_pushable": righe_count,
        # Flag testata necessario al FE per decidere se mostrare l'hint
        # "fatturazione immediata: emit AF avverra' al prossimo run pipeline lotto"
        # (PR2 implementera' il servizio emissione immediata).
        "fatturazione_immediata": bool(testata.get("fatturazione_immediata")),
    }


# Scopo: Smistamento del preventivo per il Pannello Smistamento — aggregato per
#        ramo (progress X/Y verso EVASO) + righe con natura, destinazione e
#        `stato_smistamento` autorevole. Sostituisce il vecchio
#        `stato_fatturazione` (viste DB rinominate/rifatte natura-aware,
#        brief-db-smistamento-preventivi.md B). Una sola chiamata FE.
def smistamento(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    _get_testata_or_raise(repo, preventivo_id, op="smistamento")
    # `aggregato` e' None per preventivo senza righe attive (la vista GROUP BY
    # non produce la riga): si propaga cosi' com'e', senza fabbricare un
    # fallback che duplicherebbe lo schema della vista (drift garantito alla
    # prima colonna nuova). Il FE tratta null come "niente da smistare".
    return {
        "aggregato": repo.stato_smistamento(preventivo_id),
        "righe": repo.list_righe_smistamento(preventivo_id),
    }


# ══════════════════════════════════════════════════════════
#  INTEGRAZIONE — Pratiche
# ══════════════════════════════════════════════════════════

# Esiti di RAMO dello SMISTAMENTO (bivio-per-esito rev.3, seed
# config.esiti_flussi_pratiche): MERCE_PRESENTE rende percorribili+obbligatori i
# flussi ordine 9013/9014; SOLO_SERVIZI e' ramo morto (pratica chiude subito).
_ESITO_SMISTAMENTO_MERCE = "MERCE_PRESENTE"
_ESITO_SMISTAMENTO_SERVIZI = "SOLO_SERVIZI"
_CODICE_FLUSSO_SMISTAMENTO = "SMISTAMENTO"
_RUOLO_COLLEGATO = "COLLEGATO"


# Scopo: Risolve la pratica di appartenenza di un preventivo dal suo link ROOT
#        (pratiche_sorgenti.pratica_id). None se il preventivo non nasce da una
#        pratica (percorso standalone). NB: risolve dalla pratica sul link, non
#        dal flusso — funziona anche se il ROOT e' agganciato senza flusso_id.
def _resolve_pratica_id_da_preventivo(preventivo_id: int) -> int | None:
    return PreventiviRepository().get_pratica_id_by_preventivo_root(preventivo_id)


# Scopo: Lega la commessa-servizi del preventivo alla sua pratica come COLLEGATO
#        (idempotente, ON CONFLICT DO NOTHING). Aggancio del RAMO SERVIZI dello
#        split (rev.3): post_smistamento e' merce-only, quindi la commessa-servizi
#        si aggancia dal push standalone. No-op se il preventivo non e' in una
#        pratica o se non sta in nessuna commessa APERTA: una commessa chiusa o
#        annullata resta nel link come storia, ma non e' quella dell'invio.
def _aggancia_commessa_servizi_a_pratica(preventivo_id: int, preventivo_uid: str) -> None:
    from apps.pratiche.db.pratiche_repository import PraticheRepository
    from apps.vendite.db.commesse_repository import CommesseRepository

    pratica_id = _resolve_pratica_id_da_preventivo(preventivo_id)
    if pratica_id is None:
        return
    commessa_id = CommesseRepository().get_commessa_viva_by_sorgente(
        sorgente_codice=SORGENTE_PREVENTIVO, sorgente_chiave=preventivo_uid,
    )
    if commessa_id is None:
        return
    PraticheRepository().upsert_pratica_sorgente(
        pratica_id=pratica_id, sorgente_codice=SORGENTE_COMMESSA,
        sorgente_uid=str(commessa_id), ruolo_link=_RUOLO_COLLEGATO,
    )


# Scopo: Completa il flusso SMISTAMENTO della pratica con l'esito di RAMO
#        CALCOLATO dal dominio (MERCE_PRESENTE/SOLO_SERVIZI), non scelto
#        dall'operatore (rev.3 bivio-per-esito, brief-db-chiusura-pratica-nessun-
#        lavoro-pendente). L'esito e' scritto nella STESSA UPDATE che completa il
#        flusso: il check di chiusura template-based lo legge subito → sul ramo
#        merce 9013/9014 restano dovuti (pratica APERTA), sul ramo servizi sono
#        ramo morto (pratica si chiude). Guard: smistamento completo su ENTRAMBI i
#        rami (nessun residuo). Idempotente: no-op se lo step e' gia' terminale.
#        Direzione vendite→pratiche, import lazy.
def completa_smistamento(preventivo_id: int, *, user: str | None = None) -> dict[str, Any]:
    from apps.pratiche.services import pratiche_service
    from apps.vendite.db.ordini_repository import OrdiniRepository

    repo = PreventiviRepository()

    # 1. Pratica del preventivo (percorso pratica-first).
    pratica_id = _resolve_pratica_id_da_preventivo(preventivo_id)
    ErrorManager.require(
        pratica_id is not None,
        code="E_VENDITA_PREVENTIVO_NON_COLLEGATO",
        message="Il preventivo non e' collegato a una pratica.",
        detail=f"preventivo_id={preventivo_id}",
        function_name=f"{_FN}.completa_smistamento",
    )
    assert pratica_id is not None

    # 2. Guard smistamento completo (bi-ramo): nessun residuo su ORDINE ne' COMMESSA
    #    (l'operatore deve aver smistato tutto dal Pannello prima di completare).
    #    Idempotenti su ri-azione: dopo lo smistamento non c'e' piu' residuo → non
    #    bloccano; l'idempotenza effettiva la garantisce completa_step_pratica.
    ErrorManager.require(
        not repo.preventivo_ha_residuo_ordine(preventivo_id),
        code="E_VENDITA_SMISTAMENTO_NON_ESEGUITO",
        message="Esegui lo smistamento della merce (genera ordine) prima di completare lo step.",
        detail=f"preventivo_id={preventivo_id}: residuo merce non smistato",
        function_name=f"{_FN}.completa_smistamento",
    )
    ErrorManager.require(
        not repo.preventivo_ha_residuo_commessa(preventivo_id),
        code="E_VENDITA_SMISTAMENTO_NON_ESEGUITO",
        message="Esegui lo smistamento dei servizi (invia a commessa) prima di completare lo step.",
        detail=f"preventivo_id={preventivo_id}: residuo servizi non smistato",
        function_name=f"{_FN}.completa_smistamento",
    )

    # 3. Esito di RAMO: MERCE_PRESENTE se e' nato un ordine dal preventivo,
    #    altrimenti SOLO_SERVIZI (copre anche il misto: c'e' merce → MERCE_PRESENTE).
    #    STESSO lookup dell'handler post_smistamento (get_ordine_by_documento_origine)
    #    → MERCE_PRESENTE ⟺ l'handler trovera' l'ordine da agganciare: nessun
    #    disallineamento fra classificatore d'esito e handler (evita il fail-safe
    #    su artefatti incoerenti).
    ha_ordine = OrdiniRepository().get_ordine_by_documento_origine(
        SORGENTE_PREVENTIVO, preventivo_id,
    ) is not None
    esito = _ESITO_SMISTAMENTO_MERCE if ha_ordine else _ESITO_SMISTAMENTO_SERVIZI

    # 4. Completa (idempotente) lo step SMISTAMENTO via BB motore: l'esito scritto
    #    qui e' letto dal check chiusura nella stessa transazione.
    result = pratiche_service.completa_step_pratica(
        pratica_id, template_codice=_CODICE_FLUSSO_SMISTAMENTO, esito=esito, user=user,
    )
    ErrorManager.require(
        result["flusso_id"] is not None,
        code=E_PREV_VALIDAZIONE,
        message="Flusso SMISTAMENTO non avviato per questa pratica.",
        detail=f"pratica_id={pratica_id}",
        function_name=f"{_FN}.completa_smistamento",
    )

    return {
        "preventivo_id": preventivo_id, "pratica_id": pratica_id,
        "flusso_id": result["flusso_id"], "esito": esito,
        "gia_completato": not result["completato"],
    }


# Scopo: Genera pratica esecutiva da preventivo accettato.
# Obiettivo: guard stato preventivo, poi creazione pratica + link ROOT in UNA
#   sola funzione madre atomica (vendite.fn_genera_pratica_da_preventivo).
# Perimetro: crea pratica + link; non gestisce flussi (quelli si scelgono in UI pratica).
#   Fix analisi-fix-transazioni #3 (Classe A): prima crea_pratica (@atomic a se')
#   e link_pratica erano due scritture autocommit separate → pratica orfana se il
#   link falliva. Ora la fn madre risolve contesto (emittente/soggetto/ruolo/
#   istanza) e tipo sorgente PREVENTIVO internamente e fonde le due scritture.
def genera_pratica(
    preventivo_id: int,
    tipo_prestazione_id: int,
    priorita_id: int,
    descrizione: str | None = None,
) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = _get_testata_or_raise(repo, preventivo_id, op="genera_pratica")
    # Guard "a buon mercato" sulla testata gia' letta (esistenza, stato, billing):
    # errori applicativi anticipati e chiari. La fn madre ri-guarda esistenza e
    # billing come difesa-in-profondita' (E_PREV_NOT_FOUND / E_PREV_VALIDAZIONE),
    # ma NON il guard di stato → resta qui.
    ErrorManager.require(
        e_stato_di_accettazione(TESTATA_PREVENTIVI, testata["stato_codice_interno"]),
        code="E_PREV_PRATICA_STATO",
        message="Stato preventivo non ammette generazione pratica.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.genera_pratica",
    )
    ErrorManager.require(
        testata["billing_account_id"] is not None,
        code=E_PREV_VALIDAZIONE,
        message="Preventivo senza billing account: impossibile derivare contesto pratica.",
        function_name=f"{_FN}.genera_pratica",
    )

    # Una sola SELECT fn_madre(): crea pratica + link ROOT in atomica.
    pratica_id = repo.genera_pratica_da_preventivo(
        preventivo_id=preventivo_id,
        tipo_prestazione_id=tipo_prestazione_id,
        priorita_id=priorita_id,
        descrizione=descrizione,
    )

    return {
        "pratica_id": pratica_id,
        "preventivo_id": preventivo_id,
    }


