# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per DDT di vendita (CRUD, stato, righe, evasione
#        da ordine, push a commessa).
# ------------------------------------------------------------

# Orchestrazione DDT di vendita: validazione, guard su stato, delega al
# repository, componenti BoM via fn DB `fn_ddt_riga_componenti_*`, generazione
# DDT da ordine (evasione, fn madre atomica `fn_genera_ddt_da_ordine`) e push
# singolo a commessa (sorgente DDT_VENDITA). Clone strutturale di
# `ordini_service` (modulo di funzioni libere, non classe): stessa impronta,
# logica DDT (macchina a stati DRAFT->EMESSO->SPEDITO->CONSEGNATO->RESO(+ANNULLATO)
# data-driven, numero assegnato a EMESSO dal trigger DB; cliente e destinatario
# si scelgono in bozza, fuori bozza li blocca il DB).
#
# NOTA cliente (brief-db-esecutivi-ba-coppia, D-2/D-4, 2026-10-10): il BA e'
# FACOLTATIVO. Lo pretende l'emissione quando la causale manda merce a un
# cliente (`config.causali_trasporto.richiede_cliente`: motivo
# `E_DDT_CLIENTE_OBBLIGATORIO`, capability CLIENTE_MANCANTE). Col BA,
# destinatario e utility sono copie del BA e le scrive `trgfn_ddt_normalize`;
# senza, il destinatario (terzista, deposito) lo sceglie l'operatore. Nessuna
# di queste regole e' ricopiata qui.
#
# NOTA emittente (addendum §15 + uniformazione 2026-07-13): l'emittente del
# DDT e' legato allo USER, come ordini/preventivi/contratti. Il FE prefilla
# `emittente_fiscale_id` dal profilo operatore (admin globale: Select) e il
# create lo accetta nel payload (whitelist). La colonna resta MEMORIZZATA
# (NOT NULL, scope RLS `rls_ddt_ef_whitelist`) con reti di sicurezza DB in
# `trgfn_ddt_normalize`: eredita dall'ordine sorgente (evasione) o, se il
# payload non lo porta, fallback dal billing_account. Il service LEGGE la
# colonna dalla testata e non la risolve a runtime.

import logging
from datetime import date
from collections.abc import Callable
from typing import Any, NamedTuple

from django.db import transaction

from apps.config.sorgenti import SORGENTE_DDT_VENDITA
from apps.core.db._helpers import richiedi_codice_a_vocabolario
from apps.core.api.constants import MAX_LIMIT
from apps.core.services.documento_modello import (
    e_stato_di_annullo,
    rifiuta_stato_di_emissione,
    stato_di_emissione,
)
from apps.core.services.error_manager import ErrorManager
from apps.vendite.services._cliente_dal_ba import FK_CLIENTE_DIVERSO_DA_BA
from apps.vendite.services._righe_bozza_guard import richiedi_righe_in_bozza
from apps.vendite.services._annullo_con_legami import (
    legami_del_documento,
    legami_confermati as dichiarazione_legami,
)
from apps.vendite.services._iva_contesto_documento import make_risolvi_iva_riga
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.payload_helpers import PayloadValidator, make_db_errors_translator
from apps.core.services.testata_guard import (
    pagina_dopo_testata,
    riga_del_padre_o_not_found,
    testata_o_not_found,
)
from apps.core.services.value_normalizer import empty_to_none
from apps.core.services.partitioned_note_service import contatori_documento
from apps.vendite.db.note_repositories import NOTE_REPO_DDT
from apps.vendite.db.ddt_repository import TESTATA_DDT, DdtRepository
from apps.vendite.services._componenti_service_helpers import (
    dati_patch_componente,
    normalize_componenti_overrides,
)
from apps.vendite.services._indirizzi_documento_helpers import (
    IndirizziDocumentoConfig,
    delete_indirizzo_documento,
    list_indirizzi_documento,
    upsert_indirizzo_documento,
)
from apps.vendite.services._pricing_gate_helpers import (
    validate_componenti_overrides_authorization,
)

logger = logging.getLogger(__name__)

# Codici errore vendite (registrati in error_policies.py) usati come fallback
# nella traduzione errori DB. I codici trigger E_DDT_*/E_STATO_DDT_*/E_QTA_*
# sollevati dai guard DB sono estratti via regex dal MESSAGE del RAISE.
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"

# Mappe vincolo DB -> (codice, messaggio) per map_integrity_error (frammento
# nome vincolo). Minime: i casi non mappati cadono su E_VENDITE_VALIDATION.
# `vendite.ddt`/`vendite.ddt_righe` non hanno UNIQUE di dominio (numerazione
# gestita dal trigger a EMESSO, fuori da sistema_codici) -> solo FK.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    # Lo stesso lotto / seriale / ubicazione due volte sotto la stessa voce: si
    # aumenta la quantita' del prelievo che c'e' (Lotto 3 D-L3-b).
    "uq_ddt_righe_prelievi_posizione": (
        E_VENDITE_DUPLICATO,
        "Questa voce ha gia' un prelievo da questa posizione: aumentane la quantita'.",
    ),
}
_FK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "fk_ddt_vendita_r_articolo": (E_VENDITE_FK, "Articolo non valido."),
    "fk_ddt_v_billing_account": (E_VENDITE_FK, "Cliente (billing account) non valido."),
    "fk_ddt_vendita_destinatario_ruolo": (E_VENDITE_FK, "Destinatario non valido."),
    "fk_ddt_vendita_r_iva": (E_VENDITE_FK, "Aliquota IVA non valida."),
    "fk_ddt_v_emittente_fiscale": (E_VENDITE_FK, "Emittente fiscale non valido."),
    # Rete sotto il BB `fn_cliente_dal_billing_account` (che risponde prima,
    # col suo codice): destinatario o utility diversi da quelli del BA.
    "fk_ddt_ba_cliente": FK_CLIENTE_DIVERSO_DA_BA,
}
# «BA e utility tutti e due o nessuno»: la utility e' copia del BA.
_CHECK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "chk_ddt_ba_utility_insieme": (
        E_VENDITE_VALIDATION,
        "La utility della bolla e' quella del suo billing account: senza billing account non c'e'.",
        "billing_account_id",
    ),
    # I prelievi (Lotto 3 D-L3-b): la quantita' e' positiva (il verso lo mette
    # il movimento), e un seriale e' un pezzo.
    "chk_ddt_righe_prelievi_qta_positiva": (
        E_VENDITE_VALIDATION, "La quantita' prelevata deve essere maggiore di zero.", "qta",
    ),
    "chk_ddt_righe_prelievi_qta_finito": (
        E_VENDITE_VALIDATION, "La quantita' prelevata non e' un numero valido.", "qta",
    ),
    "chk_ddt_righe_prelievi_asset_qta_unitaria": (
        E_VENDITE_VALIDATION, "Un seriale e' un pezzo solo: la quantita' deve essere 1.", "qta",
    ),
}

# ── Costanti di dominio ──
_FN = "vendite.ddt_service"
_V = PayloadValidator(validation_code="E_DDT_VALIDAZIONE")
# Gli id della controparte che il payload puo' portare: si coerciscono a
# intero (un valore non numerico e' un 400 col campo, non un 500 da `int()`).
_ID_CONTROPARTE: tuple[str, ...] = ("billing_account_id", "destinatario_soggetto_ruolo_id")
_STATI_MODIFICABILI: frozenset[str] = frozenset({"DRAFT"})

# Whitelist campi testata accettati in create (null_vs_empty -> None).
# Col BA il destinatario lo scrive il DB (e rifiuta un valore diverso); senza
# BA e' obbligatorio (NOT NULL: il 23502 arriva col campo). ⛔ `utility_id`
# NON c'e': e' una copia del BA (CHECK «tutti e due o nessuno»), la scrive il
# DB. ⛔ Una chiave fuori whitelist e' un 400, come in modifica (2026-10-19,
# scelta di Tid): fino ad allora la creazione la SCARTAVA in silenzio.
CREATE_KEYS_DDT: frozenset[str] = frozenset({
    "billing_account_id", "destinatario_soggetto_ruolo_id",
    "emittente_fiscale_id",
    "valuta_id", "mittente_soggetto_ruolo_id", "vettore_soggetto_ruolo_id",
    "causale_trasporto_id", "aspetto_bene_id", "modalita_addebito_trasporto_id",
    "num_colli", "peso_lordo", "peso_netto", "volume", "targa", "autista",
    "tracking_code", "data", "meta",
    # Magazzino di partenza e, per la bolla di trasferimento, di arrivo (Lotto 3
    # D-L3-a). Senza partenza la propone il DB (il predefinito dell'emittente,
    # `trgfn_ddt_default_magazzino`); le regole — stesso emittente, arrivo solo
    # per il trasferimento e diverso dalla partenza, fermi fuori bozza — sono
    # dei guard DB, qui non si ricopiano.
    "magazzino_id", "magazzino_arrivo_id",
    # Corsia di instradamento della fatturazione (simmetria del flag, Fase B
    # del brief emissione mirata): si decide PRIMA del push in commessa, dove
    # il flag entra nella chiave di dedup; dopo e' inerte e il guard DB
    # `trgfn_guard_fatturazione_immediata_immutabile` respinge l'UPDATE. Il
    # lock di testata fuori bozza non lo nomina: decide quel guard, non lo stato.
    "fatturazione_immediata",
})
# Cliente e destinatario si cambiano in BOZZA (D-2: la bolla puo' nascere senza
# BA e riceverlo prima dell'emissione); fuori bozza li blocca il DB
# (`trg_ddt_a05_lock_fuori_bozza_upd`, E_DDT_CLIENTE_IMMUTABILE). Al cambio di
# BA il destinatario non toccato segue il BA nuovo; un BA tolto toglie la
# utility e lascia il destinatario (`trgfn_ddt_normalize`). ⛔ `utility_id`
# fuori, come in create.
# ⛔ Una chiave fuori whitelist e' un 400, in modifica come in creazione (dal
#    2026-10-19, scelta di Tid, come preventivo, offerta e contratto). Fino ad
#    allora si SCARTAVA in silenzio, per tollerare un client vecchio: la
#    risposta era ok e il valore non arrivava, senza che nessuno lo sapesse.
UPDATE_KEYS_DDT: frozenset[str] = frozenset({
    "billing_account_id", "destinatario_soggetto_ruolo_id",
    "valuta_id", "mittente_soggetto_ruolo_id",
    "vettore_soggetto_ruolo_id", "causale_trasporto_id", "aspetto_bene_id",
    "modalita_addebito_trasporto_id", "num_colli", "peso_lordo", "peso_netto",
    "volume", "targa", "autista", "tracking_code", "data", "meta",
    "fatturazione_immediata", "magazzino_id", "magazzino_arrivo_id",
})
    # ⛔ `iva_id` NON C'E' PIU' (`I6`, 2026-08-31): l'aliquota della riga la
    # decide il risolutore, e la casella a video e' spenta. Rimetterla qui
    # riaprirebbe la seconda risposta alla stessa domanda che tutto questo
    # cantiere e' servito a togliere.
    # ⛔ Una chiave fuori whitelist e' un 400 anche sulle RIGHE (2026-10-19,
    #    scelta di Tid: la stessa regola della testata, come il contratto).
    #    Fino ad allora `gestisci_riga` e `aggiorna_riga` la SCARTAVANO in
    #    silenzio.
CREATE_KEYS_RIGA: frozenset[str] = frozenset({
    "articolo_id", "descrizione", "quantita", "qta_operativa",
    "uom_operativa_id", "factor_to_base", "prezzo_unitario", "sconto_percentuale",
    "meta",
})
# Le chiavi AMMESSE nella creazione di una riga: le colonne qui sopra piu' la
# mappa degli override dei prezzi dei componenti, che non e' una colonna e si
# legge a parte (`normalize_componenti_overrides`).
CREATE_PAYLOAD_RIGA: frozenset[str] = CREATE_KEYS_RIGA | {"componenti_overrides"}
UPDATE_KEYS_RIGA: frozenset[str] = frozenset({
    "descrizione", "quantita", "qta_operativa", "uom_operativa_id",
    "factor_to_base", "prezzo_unitario", "sconto_percentuale", "meta",
})


# ══════════════════════════════════════════════════════════
#  LETTURE — Lista (envelope + rows per export)
# ══════════════════════════════════════════════════════════

# Scopo: Letture grezze (righe + totale) della lista DDT. Condivisa tra lista
#        paginata (envelope) ed export futuro — regola del 2.
def list_ddt_rows(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    search: str | None = None,
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
        "config.stati_doc_ddt", "codice_interno", stato_codice,
        codice_errore="E_DDT_VALIDAZIONE", parametro="stato_codice_interno",
    )
    repo = DdtRepository()
    return repo.list_ddt(
        stato_codice=stato_codice,
        billing_account_id=billing_account_id,
        utility_id=utility_id,
        data_da=data_da,
        data_al=data_al,
        search=search,
        auth_user_id=auth_user_id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
        max_limit=max_limit,
    )


# Scopo: Etichette leggibili dei filtri applicati per il metadato del file
#        export (DEF-1). Gemello resolve_filtri_export_label ordini.
def resolve_filtri_export_label(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
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
    return out


# Scopo: Dettaglio testata DDT + capability (righe lette a parte via /righe/).
def get_ddt(ddt_id: int) -> dict[str, Any]:
    repo = DdtRepository()
    testata = _get_testata_or_raise(repo, ddt_id, op="get_ddt")
    # Capability data-driven da script.fn_available_actions_ddt (matrice
    # config.transizioni_stati_ddt): available_actions, can_change_state,
    # can_edit_testata/righe, can_push_commessa(+reason), non_editable_fields,
    # stato_codice. La verita' e' a DB (lettura) + trigger guard (enforcement).
    # ⛔ Il blob viaggia SOTTO `capabilities`, non fuso nella testata (api.md
    #    §«Il blob sta SOTTO `capabilities`», decisione Tid 2026-09-23).
    capabilities = repo.get_capabilities(ddt_id)
    return {
        **testata,
        "capabilities": capabilities,
        # COUNT dedicato: l'elenco righe completo (JOIN + EXISTS per riga)
        # sarebbe materializzato solo per contarlo.
        "righe_count": repo.count_righe(ddt_id),
        "contatori": contatori_documento(NOTE_REPO_DDT, ddt_id),
    }


# Scopo: Lista righe di un DDT. Legge prima la testata: un DDT fuori
#        perimetro (o inesistente) e' un 404, non un pannello vuoto.
def list_righe(ddt_id: int) -> list[dict[str, Any]]:
    repo = DdtRepository()
    _get_testata_or_raise(repo, ddt_id, op="list_righe")
    return repo.list_righe(ddt_id)


# Scopo: Una PAGINA delle righe del DDT, per la lista configurabile
#        (`GET …/righe/lista/`): ricerca, ordinamento e pagina dal BB del
#        repository, dopo la testata (BB core `pagina_dopo_testata`).
#        Ritorna `(righe, totale)`.
def list_righe_pagina(ddt_id: int, **opzioni: Any) -> tuple[list[dict[str, Any]], int]:
    repo = DdtRepository()
    return pagina_dopo_testata(
        lambda: _get_testata_or_raise(repo, ddt_id, op="list_righe_pagina"),
        repo.list_righe_pagina, ddt_id, **opzioni,
    )


# ── Indirizzi documento (BB condiviso _indirizzi_documento_helpers) ──

# Configurazione unica del BB per il dominio DDT: guard di esistenza e
# traduzione errori DB vivono nel helper condiviso (l'appartenenza al cliente
# la giudica il DB).
_INDIRIZZI_CFG = IndirizziDocumentoConfig(
    # lambda (non la classe): risolve il nome a call-time, cosi' i @patch
    # dei test unit raggiungono il repository.
    repo_factory=lambda: DdtRepository(),
    not_found_code="E_DDT_NOT_FOUND",
    error_code="E_DDT_VALIDAZIONE",
    fn_prefix=_FN,
)


# Scopo: Pannello indirizzi del DDT: tipi ammessi per l'ambito DDT + slot
#        correnti (snapshot congelati + origine soft).
def list_indirizzi(ddt_id: int) -> dict[str, Any]:
    return list_indirizzi_documento(_INDIRIZZI_CFG, ddt_id)


# Scopo: Upsert slot indirizzo (uno-per-tipo, solo DRAFT: dopo l'emissione lo
#        snapshot e' congelato col documento). Picker: snapshot server-side da
#        fn_snapshot_indirizzo; una-tantum: dal payload. Che sia del cliente
#        lo giudica il guard DB.
def upsert_indirizzo(ddt_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return upsert_indirizzo_documento(_INDIRIZZI_CFG, ddt_id, payload)


# Scopo: Rimozione slot indirizzo (solo DRAFT). L'obbligatorieta' di CON e'
#        verificata dal guard DB all'emissione, non qui.
def delete_indirizzo(ddt_id: int, indirizzo_id: int) -> dict[str, Any]:
    return delete_indirizzo_documento(_INDIRIZZI_CFG, ddt_id, indirizzo_id)


# Scopo: Riepilogo IVA aggregato del DDT (una riga per aliquota). Calcolo
#        fiscalmente corretto gia' applicato in DB via la vista derivata
#        vw_ddt_riepilogo_iva_dettaglio (stessa formula di preventivi/ordini;
#        righe con prezzo NULL escluse in vista): il service legge, nessun
#        ricalcolo Python. Usato dal FE per il pannello "Riepilogo IVA" del
#        drawer DDT e (futuro) dal context builder della stampa.
#        Legge prima la testata: fuori perimetro e' un 404.
def list_riepilogo_iva(ddt_id: int) -> list[dict[str, Any]]:
    repo = DdtRepository()
    _get_testata_or_raise(repo, ddt_id, op="list_riepilogo_iva")
    return repo.list_riepilogo_iva(ddt_id)


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Testata
# ══════════════════════════════════════════════════════════

# Scopo: Crea un nuovo DDT standalone. Lo stato non si passa: il DDT nasce
#        nello stato iniziale del suo vocabolario, e lo mette il DB (BB
#        `script.trgfn_doc_stato_iniziale`, brief-modello-documento-vendita
#        P-2). `numero` NON assegnato in bozza: lo valorizza il trigger DB a
#        EMESSO (C6). Cliente (BA) facoltativo: col BA il destinatario lo
#        scrive il DB, senza va indicato (terzista, deposito). Vedi la NOTA
#        cliente in testa.
def crea_ddt(payload: dict[str, Any]) -> dict[str, Any]:
    repo = DdtRepository()
    # Una chiave fuori whitelist e' un 400 (vedi CREATE_KEYS_DDT).
    _V.validate_allowed_keys(
        payload, allowed=CREATE_KEYS_DDT, function_name=f"{_FN}.crea_ddt",
    )
    data = {k: empty_to_none(v) for k, v in payload.items()}
    _coerci_id_controparte(data, op="crea_ddt")

    meta = data.get("meta")
    # Creazione e slot di default in UNA transazione: il riempimento non e'
    # best-effort, e un suo errore non deve lasciare la bozza senza chi l'ha
    # chiesta (ATOMIC_REQUESTS e' spento, api.md §Atomicita').
    with _db_errors("crea_ddt"), transaction.atomic():
        creato = repo.create_ddt(
            destinatario_soggetto_ruolo_id=data.get("destinatario_soggetto_ruolo_id"),
            billing_account_id=data.get("billing_account_id"),
            # Emittente dallo user (prefill FE dal profilo, mirror ordini).
            # Se None: fallback DB dal BA in trgfn_ddt_normalize.
            emittente_fiscale_id=data.get("emittente_fiscale_id"),
            valuta_id=data.get("valuta_id"),
            mittente_soggetto_ruolo_id=data.get("mittente_soggetto_ruolo_id"),
            vettore_soggetto_ruolo_id=data.get("vettore_soggetto_ruolo_id"),
            causale_trasporto_id=data.get("causale_trasporto_id"),
            aspetto_bene_id=data.get("aspetto_bene_id"),
            modalita_addebito_trasporto_id=data.get("modalita_addebito_trasporto_id"),
            num_colli=data.get("num_colli"),
            peso_lordo=data.get("peso_lordo"),
            peso_netto=data.get("peso_netto"),
            volume=data.get("volume"),
            targa=data.get("targa"),
            autista=data.get("autista"),
            tracking_code=data.get("tracking_code"),
            data=data.get("data"),
            meta=meta if isinstance(meta, dict) else None,
            fatturazione_immediata=data.get("fatturazione_immediata"),
            magazzino_id=data.get("magazzino_id"),
            magazzino_arrivo_id=data.get("magazzino_arrivo_id"),
        )
        # Slot di default dall'anagrafica del cliente: lo decide il DB
        # (`vendite.fn_doc_indirizzo_default`, slot e ripiego sono dati).
        repo.riempi_indirizzo_default(int(creato["id"]))
    return creato


# Scopo: Aggiorna testata DDT.
#
# Quali colonne si cambiano in quale stato lo dice il DB, colonna per colonna:
# il lock di testata `vendite.trgfn_doc_testata_lock_fuori_bozza` (in bozza
# tutto; dopo l'emissione trasporto, tracciamento e note finche' la bolla non
# e' chiusa). Fino al 2026-10-10 qui c'era un «solo in DRAFT» che ne era la
# seconda copia (brief-db-testata-dopo-emissione, D-0 e R-BE-2): il 409 del
# lock passa com'e'.
# Cliente e destinatario sono nella whitelist (vedi UPDATE_KEYS_DDT): cosa
# succede alle copie lo decide il DB. Fino al 2026-10-10 qui c'era un guard
# «cliente immutabile dopo la creazione» che contraddiceva D-2: una bolla nata
# senza BA non l'avrebbe mai ricevuto (brief-db-esecutivi-ba-coppia §9.6).
def aggiorna_ddt(ddt_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = DdtRepository()
    # Una chiave fuori whitelist e' un 400, prima di qualunque lettura (vedi
    # UPDATE_KEYS_DDT): da qui in giu' il payload contiene solo chiavi ammesse.
    _V.validate_allowed_keys(
        payload, allowed=UPDATE_KEYS_DDT, function_name=f"{_FN}.aggiorna_ddt",
    )
    # Poi la testata: fuori perimetro o inesistente e' un 404. Basta sapere
    # che esiste: il lettore leggero, non la testata intera.
    _get_testata_or_raise(repo, ddt_id, op="aggiorna_ddt", getter=repo.get_stato_codice)

    data = {k: empty_to_none(v) for k, v in payload.items()}
    _coerci_id_controparte(data, op="aggiorna_ddt")
    _V.require_campi_da_aggiornare(
        data,
        function_name=f"{_FN}.aggiorna_ddt",
    )
    with _db_errors("aggiorna_ddt"):
        repo.update_ddt(ddt_id, **data)
    return {"ddt_id": ddt_id, "updated": True}


# Scopo: Hard-delete DDT BOZZA ORFANO (solo supporto al pattern "abbandono
#        bozza" del drawer: create auto-salva una BOZZA per abilitare le righe;
#        se l'operatore esce senza inserirne, la bozza vuota viene rimossa).
#        NON e' un'azione di cancellazione di DDT reali: un DDT con righe o non
#        in bozza NON si cancella, si ANNULLA (cambia_stato -> ANNULLATO).
# Guard di dominio (defense-in-depth: il FE filtra gia' su righe_count=0):
#  - DDT esistente, stato BOZZA (DRAFT), zero righe.
def elimina_ddt(ddt_id: int) -> dict[str, Any]:
    repo = DdtRepository()
    _assert_stato(repo, ddt_id, _STATI_MODIFICABILI, op="elimina_ddt")
    righe_count = repo.count_righe(ddt_id)
    ErrorManager.require(
        righe_count == 0,
        code="E_DDT_STATO_TRANSIZIONE",
        message=(
            "Impossibile eliminare un DDT con righe: annullare il DDT "
            "(cambio stato -> ANNULLATO) invece di cancellarlo."
        ),
        detail=f"righe_count={righe_count}",
        function_name=f"{_FN}.elimina_ddt",
    )
    with _db_errors("elimina_ddt"):
        deleted = repo.delete_ddt(ddt_id)
    return {"ddt_id": ddt_id, "deleted": deleted}


# Scopo: Esegue una transizione di stato data-driven del DDT (SPEDITO,
#        CONSEGNATO, ANNULLATO). Generico: lo stato destinazione
#        arriva dal codice interno (`available_actions[].target_state` della fn
#        capabilities). Ogni passaggio va al DB per un verbo
#        (`vendite.fn_cambia_stato_ddt`, Lotto 3 R-1): l'ammissibilita' la
#        valida `trgfn_ddt_guard_transizione` (matrice
#        config.transizioni_stati_ddt), il service non duplica il grafo. Alla
#        transizione a EMESSO il DB assegna il `numero`, scatta il guard
#        approvazione componenti BoM e, se la bolla muove merce, scarica il
#        magazzino. Lo stato richiesto si valida qui solo per dare un 400 a un
#        codice inesistente (il verbo lo tratterebbe da chiamante rotto).
#        ⭐ ANNULLATO passa SEMPRE dal verbo `vendite.fn_annulla_ddt`
#        (brief-db-annullo-documento-con-legami): una bolla con legami si
#        annulla solo se chi conferma DICHIARA quanti legami ha visto
#        (`legami_confermati`, letto da `get_legami`); senza la dichiarazione
#        il DB risponde E_DOC_ANNULLO_CON_LEGAMI (`confirm_and_retry`). Una
#        bolla senza legami si annulla senza dichiarazione. Il verbo ritira i
#        legami e passa da `fn_cambia_stato_ddt` (matrice, permesso, storno).
#        ⛔ EMESSO NO (M-2, brief-modello-documento-vendita §7.6): la bolla si
#        emette solo da `emetti`, cioe' da «Emetti», che produce numero e PDF
#        nella stessa transazione. Dal cambio stato generico e' un 400.
def cambia_stato(
    ddt_id: int, stato_codice: str | None,
    *, legami_confermati: Any = None,
) -> dict[str, Any]:
    return _passa_a(
        ddt_id, stato_codice, legami_confermati=legami_confermati, emissione=False,
    )


# Scopo: Il corpo comune di `cambia_stato` ed `emetti`. `emissione` dice se la
#        chiamata viene da «Emetti», l'unica strada che porta a EMESSO.
def _passa_a(
    ddt_id: int, stato_codice: str | None,
    *, legami_confermati: Any, emissione: bool,
) -> dict[str, Any]:
    repo = DdtRepository()
    # ⛔ Nessun controllo «la bolla c'e'» qui (regola del 1, Tid 2026-10-27):
    #    i verbi prendono la testata nel perimetro e rifiutano da se'
    #    (E_DDT_NOT_FOUND). Lo stato di partenza serve solo alla risposta, e
    #    il suo None (bolla che non c'e') non arriva al client.
    stato_prec = repo.get_stato_codice(ddt_id)
    # Un valore non testuale (un numero nel JSON) e' «stato mancante», un 400:
    # fino al 2026-10-09 `.strip()` su un int era un 500.
    target = stato_codice.strip() if isinstance(stato_codice, str) else ""
    ErrorManager.require(
        bool(target),
        code="E_DDT_VALIDAZIONE",
        message="stato_codice obbligatorio per il cambio stato.",
        context={"field": "stato_codice"},
        function_name=f"{_FN}.cambia_stato",
    )
    if not emissione:
        rifiuta_stato_di_emissione(
            TESTATA_DDT, target, campo="stato_codice",
            validation_code="E_DDT_VALIDAZIONE", function_name=f"{_FN}.cambia_stato",
        )
    # «Lo stato esiste?» lo dice il verbo (E_STATO_WORKFLOW_NON_TROVATO, come
    # i gemelli: brief-modello-documento-vendita §9.10): qui non ce n'e' una copia.
    # L'annullo (lo stato d'annullo del vocabolario) dal suo verbo.
    if e_stato_di_annullo(TESTATA_DDT, target):
        confermati = dichiarazione_legami(
            legami_confermati, validation_code="E_DDT_VALIDAZIONE",
            function_name=f"{_FN}.cambia_stato",
        )
        with _db_errors("cambia_stato"):
            repo.annulla(ddt_id, confermati)
        return {"ddt_id": ddt_id, "stato_precedente": stato_prec, "stato": target}
    # Ogni altro passaggio dal verbo (Lotto 3 R-1): permesso, matrice, guard
    # di sempre e, se la bolla muove merce, i movimenti di magazzino. I rifiuti
    # li traduce _db_errors (E_STATO_DDT_TRANSIZIONE_NON_VALIDA, i motivi della
    # merce all'emissione, E_PERMESSO_NEGATO, i prezzi da autorizzare).
    with _db_errors("cambia_stato"):
        movimenti = repo.cambia_stato(ddt_id, target)
    return {
        "ddt_id": ddt_id, "stato_precedente": stato_prec, "stato": target,
        "movimenti_scritti": len(movimenti),
    }


# Scopo: Emette il DDT (DRAFT -> EMESSO). Alla transizione il DB assegna il
#        `numero` (C6, trgfn_ddt_gen_numero_emesso) e scatta il guard
#        approvazione componenti BoM (brief DB §6). Ritorna il risultato LIGHT
#        della transizione ({ddt_id, stato_precedente, stato}), parita' con
#        `ordini_service.conferma`: la view emissione documentale chiama emetti
#        dentro `transaction.atomic()` e il detail pesante (vista + capability
#        + count righe) non va materializzato nella sezione critica — il FE
#        ricarica comunque il detail dopo l'emissione.
#        Lo stato che scrive lo dice il vocabolario (BB `stato_di_emissione`,
#        brief-modello-documento-vendita §8.11 B-3): fino al 2026-10-25 era il
#        letterale `STATO_EMESSO`.
def emetti(ddt_id: int) -> dict[str, Any]:
    stato = stato_di_emissione(TESTATA_DDT, function_name=f"{_FN}.emetti")
    return _passa_a(ddt_id, stato.codice, legami_confermati=None, emissione=True)


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Righe (ricalcolo totali via trigger DB)
# ══════════════════════════════════════════════════════════

# Scopo: Aggiunge una riga al DDT (solo DRAFT). Pricing stile ordini: se il
#        prezzo non e' passato e l'articolo NON e' composito, lo risolve via
#        PricingService (BB condiviso). Per articolo composito il prezzo padre
#        e' 0 e i componenti BoM sono inizializzati via fn DB. NB: il pricing
#        auto-fill e l'init componenti richiedono l'emittente, non presente
#        sulla testata DDT (vedi _resolve_emittente_sr_id).
def gestisci_riga(
    ddt_id: int, payload: dict[str, Any], *, auth_user_id: int | None = None,
) -> dict[str, Any]:
    # Una chiave fuori whitelist e' un 400, prima di qualunque lettura; il dict
    # tiene le sole colonne, senza la mappa dei componenti (letta a parte).
    data = _V.solo_chiavi_ammesse(
        payload, ammesse=CREATE_PAYLOAD_RIGA, colonne=CREATE_KEYS_RIGA,
        function_name=f"{_FN}.gestisci_riga",
    )
    repo = DdtRepository()
    testata = _get_testata_or_raise(repo, ddt_id, op="gestisci_riga")
    richiedi_righe_in_bozza(
        testata, documento=SORGENTE_DDT_VENDITA, documento_id=ddt_id, verbo="aggiungere",
        function_name=f"{_FN}.gestisci_riga",
    )

    # Override prezzi componenti BoM (dialog pre-save, simmetria ordini).
    # Gate L1: l'override manuale richiede il permesso dedicato. Poi normalizza
    # la mappa {componente_id: prezzo} (None se assente). Applicata solo per
    # articolo composito (vedi init componenti sotto).
    validate_componenti_overrides_authorization(
        payload, auth_user_id, function_name=f"{_FN}.gestisci_riga",
    )
    componenti_overrides = normalize_componenti_overrides(
        payload.get("componenti_overrides"),
        function_name=f"{_FN}.gestisci_riga",
        error_code="E_DDT_VALIDAZIONE",
    )

    articolo_id = data.get("articolo_id")
    ErrorManager.require(
        articolo_id is not None and str(articolo_id).strip() != "",
        code="E_DDT_VALIDAZIONE",
        message="articolo_id obbligatorio.",
        context={"field": "articolo_id"},
        function_name=f"{_FN}.gestisci_riga",
    )
    assert articolo_id is not None

    is_composito = repo.is_articolo_composito(str(articolo_id))
    prezzo_unitario = data.get("prezzo_unitario")
    esito_codice: str | None = None
    meta_riga = data.get("meta") if isinstance(data.get("meta"), dict) else None

    # Pricing auto-fill (solo articolo NON composito, prezzo non passato).
    #
    # ⛔ NESSUN RAMO PER IL COMPOSITO, e l'assenza e' la modifica (V-6). Fino al
    # 2026-08-19 il padre di un kit si inseriva con "0" «per soddisfare
    # l'eventuale guard»: oggi il prezzo lo ricalcola
    # `fn_ricalcola_prezzo_padre_da_componenti` dopo l'init dei componenti, e
    # quel ricalcolo mette NULL se anche un solo figlio e' scoperto. Partire da
    # zero dichiarerebbe un prezzo che nessuno ha deciso — e lo zero, a
    # differenza del NULL, e' un valore che passa i controlli.
    if not is_composito and prezzo_unitario is None:
        esito = _resolve_prezzo_riga(
            repo, testata, articolo_id=str(articolo_id),
            uom_id=data.get("uom_operativa_id"),
        )
        prezzo_unitario = esito.prezzo
        esito_codice = esito.codice
        # F-7 / DEC-8: il PERCHE' del prezzo assente si persiste, o ricaricando
        # la lista sparisce e resta solo una riga vuota che nessuno sa spiegare.
        # Chiave `prezzo_resolver_context`: lo stesso nome della colonna che il
        # DB usa sui componenti — due tabelle, un nome. Si scrive SOLO quando il
        # prezzo manca (l'assenza della chiave e' informazione) e si FONDE col
        # meta del client, che e' suo.
        if prezzo_unitario is None and esito_codice is not None:
            meta_riga = {
                **(meta_riga or {}),
                "prezzo_resolver_context": {"esito_codice": esito_codice},
            }

    # ⭐ L'IVA DI RIGA VIENE DALLA SEDE UNICA (I3, 2026-08-31). Fino a oggi la
    # sceglieva il frontend copiandola dall'articolo in `onArticoloSelect`:
    # una seconda risposta alla stessa domanda, che ignorava l'uso della
    # fornitura e i titoli documentati del cliente — cioe' applicava l'aliquota
    # piena a un esportatore abituale senza che niente lo segnalasse.
    # ⚠️ Il payload VINCE finche' `I6` non chiude la casella (decisione di Tid,
    # opzione B): qui si registra soltanto cosa avrebbe detto il risolutore.
    iva_id_riga, iva_meta = _risolvi_iva_riga(
        # ⛔ `payload_iva_id=None`, e non e' pigrizia: da `I6` la riga NON
        #    porta piu' un'IVA scelta a mano, quindi la risoluzione e'
        #    AUTORITATIVA e i suoi errori PASSANO. Meglio fermarsi che scrivere
        #    un'aliquota inventata su un documento che diventera' fiscale.
        testata, articolo_id=str(articolo_id), payload_iva_id=None,
    )
    if iva_meta:
        meta_riga = {**(meta_riga or {}), **iva_meta}

    with _db_errors("gestisci_riga"), transaction.atomic():
        riga_nr = repo.next_riga_nr(ddt_id)
        created = repo.create_riga(
            ddt_id=ddt_id,
            riga_nr=riga_nr,
            articolo_id=str(articolo_id),
            descrizione=data.get("descrizione"),
            quantita=data.get("quantita"),
            qta_operativa=data.get("qta_operativa"),
            uom_operativa_id=data.get("uom_operativa_id"),
            factor_to_base=data.get("factor_to_base"),
            prezzo_unitario=prezzo_unitario,
            sconto_percentuale=data.get("sconto_percentuale"),
            iva_id=iva_id_riga,
            meta=meta_riga,
        )
        riga_id = int(created["id"])

        # Auto-init componenti BoM per articolo composito. Con override prezzi
        # dal dialog pre-save (se presenti); altrimenti la fn DB risolve i
        # prezzi componente dal pricing corrente.
        if is_composito:
            emittente_sr_id = _resolve_emittente_sr_id(repo, testata)
            data_rif = _data_riferimento(testata)
            repo.init_componenti_riga(
                riga_id=riga_id,
                emittente_soggetto_ruolo_id=emittente_sr_id,
                data_riferimento=data_rif,
                componenti_overrides=componenti_overrides,
            )

    # DEC-3: l'avviso viaggia nel `data` della risposta, non nell'envelope
    # errori — la riga e' stata salvata, quindi non e' un fallimento.
    # DEC-4: il testo si prende dal ripiego del catalogo (senza segnaposto), non
    # si riscrive qui e non si duplica in chiavi i18n del FE.
    prezzo_esito = None
    if esito_codice is not None:
        prezzo_esito = {
            "codice": esito_codice,
            "messaggio": ErrorPolicyRegistry.resolve(esito_codice).user_message,
        }
    return {
        "ddt_id": ddt_id,
        "riga_id": riga_id,
        "is_composito": is_composito,
        "prezzo_esito": prezzo_esito,
    }


# Scopo: Aggiorna una riga DDT esistente (solo DRAFT).
def aggiorna_riga(
    ddt_id: int, riga_id: int, payload: dict[str, Any],
    *, auth_user_id: int | None = None,
) -> dict[str, Any]:
    # Una chiave fuori whitelist e' un 400, prima di qualunque lettura (vedi
    # CREATE_KEYS_RIGA): da qui in giu' il payload contiene solo chiavi ammesse.
    _V.validate_allowed_keys(
        payload, allowed=UPDATE_KEYS_RIGA, function_name=f"{_FN}.aggiorna_riga",
    )
    repo = DdtRepository()
    testata = _get_testata_or_raise(repo, ddt_id, op="aggiorna_riga")
    richiedi_righe_in_bozza(
        testata, documento=SORGENTE_DDT_VENDITA, documento_id=ddt_id, verbo="modificare",
        function_name=f"{_FN}.aggiorna_riga",
    )
    _get_riga_or_raise(repo, ddt_id, riga_id, op="aggiorna_riga")
    data = {k: empty_to_none(v) for k, v in payload.items()}
    _V.require_campi_da_aggiornare(
        data,
        message="Nessun campo aggiornabile nel payload riga.",
        function_name=f"{_FN}.aggiorna_riga",
    )
    with _db_errors("aggiorna_riga"):
        repo.update_riga(riga_id, **data)
    return {"ddt_id": ddt_id, "riga_id": riga_id, "updated": True}


# Scopo: Elimina riga DDT (HARD DELETE, solo DRAFT). I componenti BoM hanno
#        ON DELETE CASCADE.
#        A DB gli esiti sono TRE, provati nell'ordine da DUE trigger: il
#        building block `trgfn_doc_righe_lock_fuori_bozza` (primo fra i BEFORE
#        ROW di `ddt_righe`, dal 2026-09-22 — D7 del brief partita) rifiuta
#        se il documento non e' piu' in bozza -> E_RIGA_DOC_NON_BOZZA (fino a
#        quel giorno era il ramo 1 di `trgfn_dlt_block_ordrig_ddtrig`, codice
#        E_DELETE_RIGA_DOC_NON_BOZZA, ritirato); poi
#        `trgfn_dlt_block_ordrig_ddtrig`, ridotto ai soli legami: riga usata
#        come origine di un reso -> E_DELETE_RIGA_DOC_REFERENZIATA; altrimenti
#        la cancellazione RIESCE.
#        ⭐ Dal 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine D-3, D-7) la
#        riga legata a un fulfillment o a un ponte di ri-consegna in bozza si
#        CANCELLA, e i legami si ritirano con lei (l'ordine si riproietta, il
#        reso torna da ri-consegnare): E_DELETE_BLOCKED_FUL dalla riga di DDT
#        non arriva piu' (fino a quel giorno era il ramo della riga evasa).
#        ⚠️ Il terzo esito non esisteva fino al 2026-08-26: la funzione
#        sollevava su OGNI ramo e il `RETURN OLD` era irraggiungibile, quindi
#        questo verbo NON ha mai potuto riuscire. Il commento che stava qui
#        diceva «blocca SE la riga e' collegata a un fulfillment» e descriveva
#        un guard condizionale che non esisteva. Trovato in collaudo in-app
#        (riga 32884, prezzo 0, zero legami), corretto a DB con
#        `20260826-2x-...-ramo-lecito`. ⛔ La lezione: un'assunzione sul
#        comportamento di un trigger va provata con una chiamata VERA — i test
#        di questo modulo mockano il repository e non l'avrebbero mai vista.
def elimina_riga(ddt_id: int, riga_id: int) -> dict[str, Any]:
    repo = DdtRepository()
    testata = _get_testata_or_raise(repo, ddt_id, op="elimina_riga")
    richiedi_righe_in_bozza(
        testata, documento=SORGENTE_DDT_VENDITA, documento_id=ddt_id, verbo="togliere",
        function_name=f"{_FN}.elimina_riga",
    )
    _get_riga_or_raise(repo, ddt_id, riga_id, op="elimina_riga")
    with _db_errors("elimina_riga"):
        deleted = repo.delete_riga(riga_id)
    return {"ddt_id": ddt_id, "riga_id": riga_id, "deleted": deleted}


# Scopo: Corregge la quantita' evasa di una riga (D-2 di
#        brief-db-ddt-righe-evase-dall-ordine): la riga evasa da un ordine o
#        da un reso ha articolo, UoM e quantita' fermi, e la quantita' cambia
#        solo da qui. Il verbo DB fa riga, componenti, legami e stato
#        dell'ordine insieme. ⛔ Nessuna regola ricopiata: bozza, riga evasa,
#        origine, residuo, quantita' positiva li giudica il DB
#        (`script.fn_check_ddt_riga_correggi_qta_evasa` e i guard dei
#        legami), il backend controlla solo che il valore sia un numero.
def correggi_qta_evasa(
    ddt_id: int, riga_id: int, payload: dict[str, Any],
) -> dict[str, Any]:
    repo = DdtRepository()
    _get_testata_or_raise(
        repo, ddt_id, op="correggi_qta_evasa", getter=repo.get_stato_codice,
    )
    _get_riga_or_raise(repo, ddt_id, riga_id, op="correggi_qta_evasa")
    qta_operativa = _V.require_decimal(
        payload, "qta_operativa", function_name=f"{_FN}.correggi_qta_evasa",
    )
    with _db_errors("correggi_qta_evasa"):
        qta_evasa = repo.correggi_qta_evasa(riga_id, qta_operativa)
    return {"ddt_id": ddt_id, "riga_id": riga_id, "qta_evasa": qta_evasa}


# ══════════════════════════════════════════════════════════
#  PRELIEVI — da dove esce la merce (Lotto 3 R-2b, piano-be-fe-magazzino-
#  lotto-3 B1). ⛔ Nessuna regola ricopiata: bozza (e l'ubicazione di arrivo
#  fino al CONSEGNATO), regola del kit, `usa_ubicazioni`, lotto e seriale
#  dell'articolo, somma rispetto alla riga li giudicano i trigger DB e, alla
#  emissione, `script.fn_check_ddt_merce`. Il backend porta e traduce.
# ══════════════════════════════════════════════════════════

# La voce si sceglie alla creazione (riga, o componente del kit) e non cambia.
CREATE_KEYS_PRELIEVO: frozenset[str] = frozenset({
    "ddt_riga_componente_id", "qta", "lotto_id", "asset_id",
    "ubicazione_id", "ubicazione_arrivo_id",
})
UPDATE_KEYS_PRELIEVO: frozenset[str] = frozenset({
    "qta", "lotto_id", "asset_id", "ubicazione_id", "ubicazione_arrivo_id",
})
_ID_PRELIEVO: tuple[str, ...] = (
    "ddt_riga_componente_id", "lotto_id", "asset_id", "ubicazione_id", "ubicazione_arrivo_id",
)


# Scopo: I prelievi della bolla per la griglia: la testata (muove merce?,
#        i magazzini e se usano ubicazioni) e le VOCI da movimentare (riga o
#        componente, quantita' e gia' prelevata in UoM base, automatico), ognuna
#        coi suoi prelievi. Una voce automatica non chiede niente: il prelievo
#        lo crea il DB all'emissione. Prima la testata: fuori perimetro e' 404.
def get_prelievi(ddt_id: int) -> dict[str, Any]:
    repo = DdtRepository()
    testata = _get_testata_or_raise(
        repo, ddt_id, op="get_prelievi", getter=repo.get_testata_prelievi,
    )
    per_voce: dict[tuple[int, int | None], list[dict[str, Any]]] = {}
    for prelievo in repo.list_prelievi(ddt_id):
        chiave = (prelievo["ddt_riga_id"], prelievo["ddt_riga_componente_id"])
        per_voce.setdefault(chiave, []).append(prelievo)
    voci = [
        {**voce, "prelievi": per_voce.get((voce["ddt_riga_id"], voce["ddt_riga_componente_id"]), [])}
        for voce in repo.list_merce_da_movimentare(ddt_id)
    ]
    return {**testata, "voci": voci}


# Scopo: Normalizza il payload di un prelievo: chiavi del contratto, vuoti a
#        None, id interi positivi, `qta` decimale (obbligatoria in creazione).
def _payload_prelievo(
    payload: dict[str, Any], chiavi: frozenset[str], *, op: str, qta_obbligatoria: bool,
) -> dict[str, Any]:
    # Il contratto: una chiave fuori whitelist e' un 400, mai uno scarto muto.
    data = _V.solo_chiavi_ammesse(payload, ammesse=chiavi, function_name=f"{_FN}.{op}")
    for chiave in _ID_PRELIEVO:
        if chiave in data:
            data[chiave] = _V.optional_positive_int(data, chiave, function_name=f"{_FN}.{op}")
    if qta_obbligatoria or "qta" in data:
        data["qta"] = _V.require_decimal(data, "qta", function_name=f"{_FN}.{op}")
    return data


# Scopo: Il prelievo, se e' di questa riga; altrimenti E_DDT_NOT_FOUND.
def _get_prelievo_or_raise(
    repo: DdtRepository, riga_id: int, prelievo_id: int, *, op: str,
) -> dict[str, Any]:
    return riga_del_padre_o_not_found(
        repo.get_prelievo, prelievo_id, padre_id=riga_id, chiave_padre="ddt_riga_id",
        code="E_DDT_NOT_FOUND", message="Prelievo non trovato per questa riga.",
        function_name=f"{_FN}.{op}",
    )


# Scopo: Nuovo prelievo sotto una riga (o un suo componente del kit).
def crea_prelievo(ddt_id: int, riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = DdtRepository()
    _get_testata_or_raise(repo, ddt_id, op="crea_prelievo", getter=repo.get_stato_codice)
    _get_riga_or_raise(repo, ddt_id, riga_id, op="crea_prelievo")
    data = _payload_prelievo(
        payload, CREATE_KEYS_PRELIEVO, op="crea_prelievo", qta_obbligatoria=True,
    )
    with _db_errors("crea_prelievo"):
        creato = repo.create_prelievo({**data, "ddt_riga_id": riga_id})
    return {"ddt_id": ddt_id, "riga_id": riga_id, "prelievo_id": int(creato["id"])}


# Scopo: Cambia quantita', lotto, seriale o ubicazioni di un prelievo.
def aggiorna_prelievo(
    ddt_id: int, riga_id: int, prelievo_id: int, payload: dict[str, Any],
) -> dict[str, Any]:
    repo = DdtRepository()
    _get_testata_or_raise(repo, ddt_id, op="aggiorna_prelievo", getter=repo.get_stato_codice)
    _get_riga_or_raise(repo, ddt_id, riga_id, op="aggiorna_prelievo")
    _get_prelievo_or_raise(repo, riga_id, prelievo_id, op="aggiorna_prelievo")
    data = _payload_prelievo(
        payload, UPDATE_KEYS_PRELIEVO, op="aggiorna_prelievo", qta_obbligatoria=False,
    )
    _V.require_campi_da_aggiornare(
        data,
        function_name=f"{_FN}.aggiorna_prelievo",
    )
    with _db_errors("aggiorna_prelievo"):
        repo.update_prelievo(prelievo_id, **data)
    return {"ddt_id": ddt_id, "riga_id": riga_id, "prelievo_id": prelievo_id, "updated": True}


# Scopo: Toglie un prelievo.
def elimina_prelievo(ddt_id: int, riga_id: int, prelievo_id: int) -> dict[str, Any]:
    repo = DdtRepository()
    _get_testata_or_raise(repo, ddt_id, op="elimina_prelievo", getter=repo.get_stato_codice)
    _get_riga_or_raise(repo, ddt_id, riga_id, op="elimina_prelievo")
    _get_prelievo_or_raise(repo, riga_id, prelievo_id, op="elimina_prelievo")
    with _db_errors("elimina_prelievo"):
        deleted = repo.delete_prelievo(prelievo_id)
    return {"ddt_id": ddt_id, "riga_id": riga_id, "prelievo_id": prelievo_id, "deleted": deleted}


# Scopo: I legami della bolla per la finestra di conferma dell'annullo (BB
#        `legami_del_documento`, comune a bolla, ordine, preventivo e
#        contratto): legami con ordini e resi, righe di commessa da emettere.
#        Prima la testata: il lettore del DB non applica il perimetro.
def get_legami(ddt_id: int) -> dict[str, Any]:
    repo = DdtRepository()
    _get_testata_or_raise(repo, ddt_id, op="get_legami", getter=repo.get_stato_codice)
    return legami_del_documento(SORGENTE_DDT_VENDITA, ddt_id)


# ══════════════════════════════════════════════════════════
#  Componenti riga (BoM CASO A)
# ══════════════════════════════════════════════════════════

# Scopo: Preview read-only componenti BoM per il drawer riga (pre-save).
#        Nessun gate autorizzativo: la preview non persiste nulla (il gate L1
#        sugli override e' applicato al salvataggio, in gestisci_riga).
def preview_componenti_riga(
    ddt_id: int, *, articolo_id: str, uom_operativa_id: int | None,
    quantita: Any,
) -> list[dict[str, Any]]:
    repo = DdtRepository()
    testata = _get_testata_or_raise(repo, ddt_id, op="preview_componenti_riga")
    emittente_sr_id = _resolve_emittente_sr_id(repo, testata)
    return repo.preview_componenti_riga(
        articolo_id=articolo_id,
        uom_id=uom_operativa_id,
        quantita_padre=quantita,
        data_riferimento=_data_riferimento(testata),
        ba_id=testata.get("billing_account_id"),
        utility_id=testata.get("utility_id"),
        emittente_soggetto_ruolo_id=emittente_sr_id,
    )


# Scopo: Lista componenti persistiti di una riga. Guard di esistenza: la riga
#        deve esistere ED appartenere al DDT richiesto (fuori perimetro o id
#        incrociato → E_DDT_NOT_FOUND, 404).
def list_componenti_riga(
    ddt_id: int, riga_id: int, *, solo_attivi: bool = True,
) -> list[dict[str, Any]]:
    repo = DdtRepository()
    _get_riga_or_raise(repo, ddt_id, riga_id, op="list_componenti_riga")
    return repo.list_componenti_riga(riga_id, solo_attivi=solo_attivi)


# Scopo: Aggiorna un componente BoM (solo DRAFT, scope componente->riga->ddt).
def update_componente(
    ddt_id: int, riga_id: int, componente_id: int, payload: dict[str, Any],
    *, auth_user_id: int | None = None,
) -> dict[str, Any]:
    repo = DdtRepository()
    scope = repo.load_componente_with_scope(componente_id)
    ErrorManager.require(
        scope is not None and scope["ddt_id"] == ddt_id
        and scope["riga_ddt_id"] == riga_id,
        code="E_DDT_NOT_FOUND",
        message="Componente non trovato in questo DDT/riga.",
        function_name=f"{_FN}.update_componente",
    )
    assert scope is not None
    richiedi_righe_in_bozza(
        scope, documento=SORGENTE_DDT_VENDITA, documento_id=ddt_id, verbo="modificare",
        function_name=f"{_FN}.update_componente",
    )
    # Contratto dell'operatore unico per i cinque documenti (BB): chiavi
    # estranee -> 400, `origine_prezzo` derivata dal prezzo. ⚠️ Fino al
    # 2026-09-26 qui c'era un filtro locale che SCARTAVA in silenzio le chiavi
    # estranee, compresa l'`origine_prezzo` mandata dal pannello: l'origine
    # manuale non veniva mai scritta.
    data = dati_patch_componente(
        payload, auth_user_id=auth_user_id, function_name=f"{_FN}.update_componente",
        error_code="E_DDT_VALIDAZIONE",
    )
    with _db_errors("update_componente"):
        repo.update_componente(componente_id, **data)
    return {"componente_id": componente_id, "updated": True}


# Scopo: Elimina (soft, attivo=FALSE via mixin) un componente BoM (solo DRAFT).
def delete_componente(
    ddt_id: int, riga_id: int, componente_id: int,
) -> dict[str, Any]:
    repo = DdtRepository()
    scope = repo.load_componente_with_scope(componente_id)
    ErrorManager.require(
        scope is not None and scope["ddt_id"] == ddt_id
        and scope["riga_ddt_id"] == riga_id,
        code="E_DDT_NOT_FOUND",
        message="Componente non trovato in questo DDT/riga.",
        function_name=f"{_FN}.delete_componente",
    )
    assert scope is not None
    richiedi_righe_in_bozza(
        scope, documento=SORGENTE_DDT_VENDITA, documento_id=ddt_id, verbo="togliere",
        function_name=f"{_FN}.delete_componente",
    )
    with _db_errors("delete_componente"):
        deleted = repo.delete_componente(componente_id)
    return {"componente_id": componente_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  INTEGRAZIONE — Evasione da ordine + push a commessa
# ══════════════════════════════════════════════════════════

# Scopo: Genera un DDT da un ordine (evasione). Delega alla primitiva DB madre
#        `vendite.fn_genera_ddt_da_ordine` (via DdtRepository.push_da_ordine),
#        atomica DB-first: crea testata DRAFT + righe (snapshot A-2) + componenti
#        + fulfillment riga<->riga e proietta lo stato ordine (CONFERMATO/
#        PARZIALMENTE_EVASO/EVASO). La transaction.atomic() tiene insieme il
#        verbo e il riempimento dello slot di default. `righe` =
#        [{ordine_riga_id, qta_da_evadere}] in UNITA' OPERATIVA; None = tutto il residuo. Ritorna
#        {ddt_id, numero(None in DRAFT), ordine_id}.
def crea_ddt_da_ordine(
    ordine_id: int, righe: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    repo = DdtRepository()
    # Errori del guard fulfillment/evasione (E_DDT_ORDINE_NOT_FOUND,
    # E_DDT_ORDINE_STATO_NON_EVADIBILE, E_DDT_NIENTE_DA_EVADERE,
    # E_QTA_SUPERA_RESIDUO) sollevati dalla fn DB -> tradotti da _db_errors.
    # Il verbo e il default nella stessa transazione: la cascata DB copia
    # gli indirizzi dell'ordine, e il default riempie lo slot SOLO se e'
    # rimasto vuoto (la sorgente vince).
    with _db_errors("crea_ddt_da_ordine"), transaction.atomic():
        ddt_id = repo.push_da_ordine(int(ordine_id), righe)
        repo.riempi_indirizzo_default(int(ddt_id))
    # Il DDT nasce sempre in DRAFT: il `numero` e' assegnato solo a EMESSO dal
    # trigger DB -> qui e' deterministicamente None (nessun re-read).
    return {"ddt_id": ddt_id, "numero": None, "ordine_id": int(ordine_id)}


# Scopo: Push singolo del DDT a commessa (chiusura giro, fatturazione differita).
#        Riusa l'orchestratore commesse esistente con sorgente DDT_VENDITA
#        (HandlerDdt + fn_list_ddt_da_pushare gia' esistenti): l'eleggibilita'
#        (tipicamente SPEDITO/CONSEGNATO) e' data-driven nella fn DB. Pattern
#        push singolo gemello ordini/preventivi/offerte.
def push_a_commessa(ddt_id: int, *, user: str | None = None) -> dict[str, Any]:
    repo = DdtRepository()
    # Existence-check leggero (lo stato basta): il NOT_FOUND resta distinto
    # dal caso "esiste ma senza righe eleggibili" (E_DDT_NESSUNA_RIGA).
    testata_o_not_found(
        repo.get_stato_codice, ddt_id,
        code="E_DDT_NOT_FOUND", message="DDT non trovato.",
        id_name="ddt_id", function_name=f"{_FN}.push_a_commessa",
    )
    righe_count = repo.count_righe_pushable(ddt_id)
    ErrorManager.require(
        righe_count > 0,
        code="E_DDT_NESSUNA_RIGA",
        message="Nessuna riga eleggibile per il push a commessa.",
        detail=f"ddt_id={ddt_id}",
        function_name=f"{_FN}.push_a_commessa",
    )
    # Import locale per evitare cicli.
    from apps.vendite.services.commesse_service import pr_run_commesse_push_one

    # Push + ponte emittibilita' in una sola unita' atomica (l'atomic interno di
    # pr_run_commesse_push_one diventa un savepoint annidato).
    with transaction.atomic():
        report = pr_run_commesse_push_one(
            sorgente_codice=SORGENTE_DDT_VENDITA,
            sorgente_uid=ddt_id,
            user=user,
        )

    return {
        "ddt_id": ddt_id,
        "stato": report["stato"],
        "push_log_id": report["push_log_id"],
        "durata_ms": report["durata_ms"],
        "handlers": report["handlers"],
        "commesse_ids": report.get("commesse_ids", []),
        "righe_pushable": righe_count,
    }


# ══════════════════════════════════════════════════════════
#  Helper privati
# ══════════════════════════════════════════════════════════

# Traduzione errori DB -> ServiceError parlanti via BB condiviso
# `make_db_errors_translator` (core payload_helpers, estratto 2026-07-13 —
# regola del 2 alla 5a copia): IntegrityError con le mappe vincolo del
# dominio; DatabaseError (trigger P0001) con estrazione del codice E_* per
# il routing UI del FE.
_db_errors = make_db_errors_translator(
    fn_prefix=_FN,
    fallback_code=E_VENDITE_VALIDATION,
    fallback_message="Violazione vincolo DB su DDT.",
    unique_constraints=_UNIQUE_CONSTRAINTS,
    fk_constraints=_FK_CONSTRAINTS,
    check_constraints=_CHECK_CONSTRAINTS,
)


# Scopo: Coerce a intero positivo gli id della controparte presenti nel
#        payload (BB `PayloadValidator`); un None resta None (BA tolto in
#        bozza, o destinatario lasciato al DB).
def _coerci_id_controparte(data: dict[str, Any], *, op: str) -> None:
    for chiave in _ID_CONTROPARTE:
        if chiave in data:
            data[chiave] = _V.optional_positive_int(data, chiave, function_name=f"{_FN}.{op}")


# Scopo: Carica la testata DDT o solleva E_DDT_NOT_FOUND (BB core
#        `testata_o_not_found`: qui solo codice e messaggio del dominio).
# `getter` ammette il lettore leggero `get_stato_codice`, dove al chiamante
# basta sapere che il documento esiste (stessa forma di
# `offerte_service._get_offerta_or_raise`).
def _get_testata_or_raise(
    repo: DdtRepository, ddt_id: int, *, op: str,
    getter: Callable[[int], Any] | None = None,
) -> Any:
    return testata_o_not_found(
        getter or repo.get_ddt, ddt_id,
        code="E_DDT_NOT_FOUND", message="DDT non trovato.",
        id_name="ddt_id", function_name=f"{_FN}.{op}",
    )


# Scopo: Carica la riga o solleva E_DDT_NOT_FOUND se non esiste o non e' di questo
#        documento (BB core `riga_del_padre_o_not_found`: qui solo codice e
#        messaggio del dominio).
def _get_riga_or_raise(
    repo: DdtRepository, ddt_id: int, riga_id: int, *, op: str,
) -> dict[str, Any]:
    return riga_del_padre_o_not_found(
        repo.get_riga, riga_id, padre_id=ddt_id, chiave_padre="ddt_id",
        code="E_DDT_NOT_FOUND", message="Riga non trovata per questo DDT.",
        function_name=f"{_FN}.{op}",
    )


# Scopo: Guard di stato leggero (solo codice_interno): E_DDT_NOT_FOUND se il
#        DDT non esiste, E_DDT_STATO_TRANSIZIONE se lo stato non e' ammesso.
def _assert_stato(
    repo: DdtRepository, ddt_id: int, ammessi: frozenset[str], *, op: str,
) -> str:
    # Stesso BB del guard di testata, col getter leggero (solo codice_interno).
    stato = testata_o_not_found(
        repo.get_stato_codice, ddt_id,
        code="E_DDT_NOT_FOUND", message="DDT non trovato.",
        id_name="ddt_id", function_name=f"{_FN}.{op}",
    )
    ErrorManager.require(
        stato in ammessi,
        code="E_DDT_STATO_TRANSIZIONE",
        message=f"Operazione non ammessa nello stato {stato}.",
        detail=f"ammessi={sorted(ammessi)}",
        function_name=f"{_FN}.{op}",
    )
    return stato


# Scopo: Risolve il soggetto_ruolo_id dell'emittente per i componenti/pricing
#        delle righe manuali. L'emittente e' MEMORIZZATO sulla testata
#        (`emittente_fiscale_id` NOT NULL, addendum §15: ereditato dall'ordine
#        sorgente o risolto dal billing_account da `trgfn_ddt_normalize`): qui
#        si converte solo la PK nel soggetto_ruolo_id atteso dalle fn
#        componenti/pricing (memoria feedback_emittente_pk_vs_soggetto_ruolo),
#        mirror del pattern ordini. L'evasione da ordine (snapshot atomico in
#        DB) NON passa di qui.
def _resolve_emittente_sr_id(repo: DdtRepository, testata: dict[str, Any]) -> int:
    fiscale_id = testata.get("emittente_fiscale_id")
    ErrorManager.require(
        fiscale_id is not None,
        code="E_DDT_VALIDAZIONE",
        message=(
            "DDT senza emittente fiscale (testata anomala: il trigger "
            "normalize lo garantisce NOT NULL alla creazione)."
        ),
        function_name=f"{_FN}._resolve_emittente_sr_id",
    )
    assert fiscale_id is not None
    sr_id = repo.get_emittente_sr_id_by_fiscale_id(int(fiscale_id))
    ErrorManager.require(
        sr_id is not None,
        code="E_DDT_VALIDAZIONE",
        message="Soggetto-ruolo emittente non risolvibile.",
        function_name=f"{_FN}._resolve_emittente_sr_id",
    )
    assert sr_id is not None
    return int(sr_id)


# Scopo: Data di riferimento pricing/componenti dalla testata (data documento).
def _data_riferimento(testata: dict[str, Any]) -> date:
    raw = testata.get("data")
    if isinstance(raw, date):
        return raw
    ErrorManager.require(
        raw is not None,
        code="E_DDT_VALIDAZIONE",
        message="DDT senza data: impossibile risolvere prezzi/componenti.",
        function_name=f"{_FN}._data_riferimento",
    )
    return date.fromisoformat(str(raw))


# Scopo: risolve il trattamento IVA di una riga DDT dal contesto della testata,
#        e ritorna `(iva_id, meta_patch)`.
# ⭐ Wrapper sottile sul BB `IvaResolverService.applica_riga_documento`: la
#    regola sta li' ed e' una sola per i tre domini. Qui c'e' solo il
#    passaggio dei campi di testata, che sono di questo dominio.
# ⛔ `emittente_fiscale_id` e' la PK di `anagrafiche.emittenti_fiscali`, NON il
#    `soggetto_ruolo_id` che `_resolve_emittente_sr_id` produce per il pricing:
#    i due numeri si somigliano abbastanza da passare inosservati, e con quello
#    sbagliato il risolutore non trova i titoli e risponde con l'aliquota
#    ordinaria senza sollevare.
# ⭐ Costruito da una FACTORY e non scritto qui: i tre domini avevano tre copie
#    identiche a meno del codice errore. Stesso stampo di
#    `make_db_errors_translator` — i parametri di dominio si fissano una volta,
#    la regola resta in un posto solo.
_risolvi_iva_riga = make_risolvi_iva_riga(
    error_code="E_DDT_VALIDAZIONE",
    function_name=f"{_FN}._risolvi_iva_riga",
)



# Scopo: l'esito della risoluzione prezzo di una riga DDT: il prezzo se c'e',
#        altrimenti il CODICE che dice perche' non c'e'. Non e' una tupla nuda
#        perche' il chiamante deve poter leggere i nomi: `esito.prezzo` e
#        `esito.codice` si capiscono, `esito[1]` no.
class _EsitoPrezzoRiga(NamedTuple):
    prezzo: str | None
    codice: str | None


# Scopo: Risolve il prezzo unitario riga via PricingService (BB condiviso, mai
#        query dirette su listini — memoria feedback_pricing_centralizzato).
#
#        ⛔ NIENTE RIPIEGO A "0" (V-6 del brief-ddt-righe-senza-prezzo). Fino al
#        2026-08-19 un prezzo non risolto diventava zero, e zero e' un prezzo:
#        la riga entrava in fattura a valore nullo invece di essere fermata.
#        Prezzo assente e prezzo zero sono due fatti diversi, e solo uno dei due
#        e' una decisione di qualcuno.
#
#        ⚠️ Usa il NUCLEO (`resolve_prezzo_esito`), non il guscio: sul DDT il
#        prezzo mancante non e' un errore — e' un esito da riportare. Gli altri
#        domini continuano a chiamare `resolve_prezzo`, che solleva (BE-3/DEC-2).
def _resolve_prezzo_riga(
    repo: DdtRepository, testata: dict[str, Any], *,
    articolo_id: str, uom_id: int | None,
) -> _EsitoPrezzoRiga:
    from apps.vendite.services.pricing_service import PricingService

    fn = f"{_FN}._resolve_prezzo_riga"
    ErrorManager.require(
        testata.get("billing_account_id") is not None,
        code="E_DDT_VALIDAZIONE",
        message="DDT senza billing_account: impossibile risolvere il prezzo.",
        function_name=fn,
    )
    ErrorManager.require(
        testata.get("utility_id") is not None,
        code="E_DDT_VALIDAZIONE",
        message="DDT senza utility: impossibile risolvere il prezzo.",
        function_name=fn,
    )
    ErrorManager.require(
        uom_id is not None,
        code="E_DDT_VALIDAZIONE",
        message="uom_operativa_id obbligatorio per risolvere il prezzo.",
        context={"field": "uom_operativa_id"},
        function_name=fn,
    )
    emittente_sr_id = _resolve_emittente_sr_id(repo, testata)
    assert uom_id is not None
    result = PricingService().resolve_prezzo_esito(
        articolo_id=articolo_id,
        uom_id=int(uom_id),
        data_riferimento=_data_riferimento(testata),
        ba_id=int(testata["billing_account_id"]),
        utility_id=int(testata["utility_id"]),
        emittente_soggetto_ruolo_id=emittente_sr_id,
    )
    prezzo = result.get("prezzo_finale")
    codice = result.get("esito_codice")
    if prezzo is None:
        return _EsitoPrezzoRiga(prezzo=None, codice=codice)
    return _EsitoPrezzoRiga(prezzo=str(prezzo), codice=codice)
