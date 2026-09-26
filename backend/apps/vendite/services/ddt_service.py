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
# data-driven, numero assegnato a EMESSO dal trigger DB, cliente/destinatario
# immutabile post-creazione).
#
# NOTA emittente (addendum §15 + uniformazione 2026-07-13): l'emittente del
# DDT e' legato allo USER, come ordini/preventivi/contratti. Il FE prefilla
# `emittente_fiscale_id` dal profilo operatore (admin globale: Select) e il
# create lo accetta nel payload (whitelist). La colonna resta MEMORIZZATA
# (NOT NULL, scope RLS `rls_ddt_ef_whitelist`) con reti di sicurezza DB in
# `trgfn_ddt_normalize`: eredita dall'ordine sorgente (evasione) o, se il
# payload non lo porta, fallback dal billing_account. Il service LEGGE la
# colonna dalla testata e non la risolve a runtime; il billing_account resta
# richiesto alla creazione (deriva il destinatario e ancora il fallback).

import logging
from datetime import date
from typing import Any, NamedTuple

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.vendite.services._righe_bozza_guard import richiedi_righe_in_bozza
from apps.vendite.services._iva_contesto_documento import make_risolvi_iva_riga
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.payload_helpers import make_db_errors_translator
from apps.core.services.testata_guard import riga_del_padre_o_not_found, testata_o_not_found
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.services._componenti_service_helpers import (
    dati_patch_componente,
    normalize_componenti_overrides,
)
from apps.vendite.services._indirizzi_documento_helpers import (
    IndirizziDocumentoConfig,
    auto_assegna_indirizzo_default,
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
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {}
_FK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "fk_ddt_vendita_r_articolo": (E_VENDITE_FK, "Articolo non valido."),
    "fk_ddt_v_billing_account": (E_VENDITE_FK, "Cliente (billing account) non valido."),
    "fk_ddt_vendita_destinatario_ruolo": (E_VENDITE_FK, "Destinatario non valido."),
    "fk_ddt_vendita_r_iva": (E_VENDITE_FK, "Aliquota IVA non valida."),
    "fk_ddt_v_emittente_fiscale": (E_VENDITE_FK, "Emittente fiscale non valido."),
}

# ── Costanti di dominio ──
_FN = "vendite.ddt_service"
_STATO_BOZZA = "DRAFT"
_STATO_EMESSO = "EMESSO"
_STATI_MODIFICABILI: frozenset[str] = frozenset({"DRAFT"})

# Whitelist campi testata accettati in create (null_vs_empty -> None).
# `destinatario_soggetto_ruolo_id` opzionale nel payload: derivato dal
# billing_account se assente (cliente=BA, come ordini).
CREATE_KEYS_DDT: frozenset[str] = frozenset({
    "billing_account_id", "destinatario_soggetto_ruolo_id", "utility_id",
    "emittente_fiscale_id",
    "valuta_id", "mittente_soggetto_ruolo_id", "vettore_soggetto_ruolo_id",
    "causale_trasporto_id", "aspetto_bene_id", "modalita_addebito_trasporto_id",
    "num_colli", "peso_lordo", "peso_netto", "volume", "targa", "autista",
    "tracking_code", "data", "meta",
    # Corsia di instradamento della fatturazione (simmetria del flag, Fase B
    # del brief emissione mirata): si decide PRIMA del push in commessa, dove
    # il flag entra nella chiave di dedup; dopo e' inerte e il guard DB
    # `trgfn_guard_fatturazione_immediata_immutabile` respinge l'UPDATE. La
    # testata DDT e' editabile solo in DRAFT: le due finestre non si toccano.
    "fatturazione_immediata",
})
# NB: billing_account_id/destinatario NON aggiornabili (cliente immutabile
# post-creazione, vedi aggiorna_ddt): cambiare cliente = nuovo DDT.
UPDATE_KEYS_DDT: frozenset[str] = frozenset({
    "utility_id", "valuta_id", "mittente_soggetto_ruolo_id",
    "vettore_soggetto_ruolo_id", "causale_trasporto_id", "aspetto_bene_id",
    "modalita_addebito_trasporto_id", "num_colli", "peso_lordo", "peso_netto",
    "volume", "targa", "autista", "tracking_code", "data", "meta",
    "fatturazione_immediata",
})
    # ⛔ `iva_id` NON C'E' PIU' (`I6`, 2026-08-31): l'aliquota della riga la
    # decide il risolutore, e la casella a video e' spenta. Rimetterla qui
    # riaprirebbe la seconda risposta alla stessa domanda che tutto questo
    # cantiere e' servito a togliere.
    # ⚠️ Una chiave fuori whitelist viene SCARTATA, non respinta: un client
    # vecchio che la manda ancora non riceve un errore — il valore semplicemente
    # non arriva. E' voluto, ed e' il motivo per cui BE e FE vanno insieme.
CREATE_KEYS_RIGA: frozenset[str] = frozenset({
    "articolo_id", "descrizione", "quantita", "qta_operativa",
    "uom_operativa_id", "factor_to_base", "prezzo_unitario", "sconto_percentuale",
    "meta",
})
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
    max_limit: int = 200,
) -> tuple[list[Any], int]:
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
    search: str | None = None,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if search:
        out["Ricerca"] = search
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
def get_ddt(ddt_id: int) -> dict[str, object]:
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
    }


# Scopo: Lista righe di un DDT. Legge prima la testata: un DDT fuori
#        perimetro (o inesistente) e' un 404, non un pannello vuoto.
def list_righe(ddt_id: int) -> list[dict[str, Any]]:
    repo = DdtRepository()
    _get_testata_or_raise(repo, ddt_id, op="list_righe")
    return repo.list_righe(ddt_id)


# ── Indirizzi documento (BB condiviso _indirizzi_documento_helpers) ──

# Configurazione unica del BB per il dominio DDT: guard esistenza/stato,
# ownership picker e traduzione errori DB vivono nel helper condiviso.
_INDIRIZZI_CFG = IndirizziDocumentoConfig(
    # lambda (non la classe): risolve il nome a call-time, cosi' i @patch
    # dei test unit raggiungono anche il ramo auto-assegnazione.
    repo_factory=lambda: DdtRepository(),
    stati_modificabili=_STATI_MODIFICABILI,
    not_found_code="E_DDT_NOT_FOUND",
    stato_error_code="E_DDT_STATO_TRANSIZIONE",
    error_code="E_DDT_VALIDAZIONE",
    fn_prefix=_FN,
)


# Scopo: Pannello indirizzi del DDT: tipi ammessi per l'ambito DDT + slot
#        correnti (snapshot congelati + origine soft).
def list_indirizzi(ddt_id: int) -> dict[str, Any]:
    return list_indirizzi_documento(_INDIRIZZI_CFG, ddt_id)


# Scopo: Upsert slot indirizzo (uno-per-tipo, solo DRAFT: dopo l'emissione lo
#        snapshot e' congelato col documento). Picker: snapshot server-side da
#        fn_snapshot_indirizzo + guard ownership; una-tantum: dal payload.
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

# Scopo: Crea un nuovo DDT standalone in stato DRAFT (BOZZA). `numero` NON
#        assegnato in DRAFT: lo valorizza il trigger DB a EMESSO (C6).
#        `destinatario_soggetto_ruolo_id` derivato dal billing_account se
#        assente (cliente=BA, come ordini).
def crea_ddt(payload: dict[str, Any]) -> dict[str, Any]:
    repo = DdtRepository()
    data = {k: empty_to_none(v) for k, v in payload.items() if k in CREATE_KEYS_DDT}

    billing_account_id = data.get("billing_account_id")
    # Cliente obbligatorio: deriva il destinatario e ancora il fallback DB
    # dell'emittente (`trgfn_ddt_normalize`) quando il payload non lo porta.
    # Senza BA l'INSERT fallirebbe a DB con un errore non parlante.
    ErrorManager.require(
        billing_account_id is not None,
        code="E_DDT_VALIDAZIONE",
        message=(
            "Cliente (billing_account_id) obbligatorio: risolve l'emittente "
            "fiscale del DDT."
        ),
        context={"field": "billing_account_id"},
        function_name=f"{_FN}.crea_ddt",
    )
    assert billing_account_id is not None
    destinatario_id = data.get("destinatario_soggetto_ruolo_id")
    if destinatario_id is None:
        # BA garantito non-None dal guard sopra: derivazione sempre tentabile.
        destinatario_id = repo.get_soggetto_ruolo_id_by_ba(int(billing_account_id))
    ErrorManager.require(
        destinatario_id is not None,
        code="E_DDT_VALIDAZIONE",
        message="Destinatario non risolvibile dal billing_account: indicare "
                "destinatario_soggetto_ruolo_id esplicito.",
        context={"field": "destinatario_soggetto_ruolo_id"},
        function_name=f"{_FN}.crea_ddt",
    )
    assert destinatario_id is not None

    stato_bozza_id = repo.get_stato_id_by_codice(_STATO_BOZZA)
    ErrorManager.require(
        stato_bozza_id is not None,
        code="E_DDT_VALIDAZIONE",
        message="Stato DRAFT non configurato in config.stati_doc_ddt.",
        function_name=f"{_FN}.crea_ddt",
    )
    assert stato_bozza_id is not None

    meta = data.get("meta")
    with _db_errors("crea_ddt"):
        creato = repo.create_ddt(
            destinatario_soggetto_ruolo_id=int(destinatario_id),
            stato_doc_ddt_id=int(stato_bozza_id),
            billing_account_id=int(billing_account_id) if billing_account_id is not None else None,
            # Emittente dallo user (prefill FE dal profilo, mirror ordini).
            # Se None: fallback DB dal BA in trgfn_ddt_normalize.
            emittente_fiscale_id=data.get("emittente_fiscale_id"),
            utility_id=data.get("utility_id"),
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
        )
    # UX v2: auto-assegnazione best-effort dell'indirizzo di consegna default
    # (indirizzo di ruolo CON del cliente, fallback FATT). Mai bloccante.
    auto_assegna_indirizzo_default(_INDIRIZZI_CFG, int(creato["id"]))
    return creato


# Scopo: Aggiorna testata DDT (solo in DRAFT).
#
# Cliente immutabile post-creazione: billing_account_id NON e' nella whitelist
# UPDATE_KEYS_DDT. `vendite.ddt` denormalizza il cliente su billing_account_id
# + destinatario_soggetto_ruolo_id (NOT NULL): cambiare il BA lascerebbe il
# destinatario stantio -> incoerenza cliente<->soggetto. Regola "cambiare
# cliente = nuovo DDT". Un tentativo ESPLICITO di cambiare BA e' rifiutato (non
# ignorato in silenzio); un BA invariato nel payload e' tollerato.
def aggiorna_ddt(ddt_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = DdtRepository()
    # Lettura singola: la testata copre sia il guard stato sia il confronto
    # billing_account (evita get_stato_codice + get_ddt sullo stesso record).
    testata = _get_testata_or_raise(repo, ddt_id, op="aggiorna_ddt")
    stato = testata["stato_codice_interno"]
    ErrorManager.require(
        stato in _STATI_MODIFICABILI,
        code="E_DDT_STATO_TRANSIZIONE",
        message=f"Operazione non ammessa nello stato {stato}.",
        detail=f"ammessi={sorted(_STATI_MODIFICABILI)}",
        function_name=f"{_FN}.aggiorna_ddt",
    )

    if "billing_account_id" in payload:
        raw_ba = empty_to_none(payload["billing_account_id"])
        # Coercion difensiva: un billing_account_id non numerico e' input
        # invalido -> 4xx parlante, non 500.
        try:
            nuovo_ba = int(raw_ba) if raw_ba is not None else None
        except (TypeError, ValueError):
            nuovo_ba = None
            ErrorManager.require(
                False,
                code="E_DDT_VALIDAZIONE",
                message="billing_account_id non valido.",
                detail=f"billing_account_id={payload['billing_account_id']!r}",
                context={"field": "billing_account_id"},
                function_name=f"{_FN}.aggiorna_ddt",
            )
        attuale_ba = testata.get("billing_account_id")
        attuale_ba = int(attuale_ba) if attuale_ba is not None else None
        ErrorManager.require(
            nuovo_ba == attuale_ba,
            code="E_DDT_CLIENTE_IMMUTABILE",
            message=(
                "Cliente (billing_account_id) immutabile dopo la creazione. "
                "Per cambiare cliente crea un nuovo DDT."
            ),
            detail=f"attuale={attuale_ba} richiesto={nuovo_ba}",
            function_name=f"{_FN}.aggiorna_ddt",
        )

    data = {k: empty_to_none(v) for k, v in payload.items() if k in UPDATE_KEYS_DDT}
    ErrorManager.require(
        len(data) > 0,
        code="E_DDT_VALIDAZIONE",
        message="Nessun campo aggiornabile nel payload.",
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
    righe_count = len(repo.list_righe(ddt_id))
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


# Scopo: Esegue una transizione di stato data-driven del DDT (es. EMESSO,
#        SPEDITO, CONSEGNATO, RESO, ANNULLATO). Generico: lo stato destinazione
#        arriva dal codice interno (`available_actions[].target_state` della fn
#        capabilities). L'ammissibilita' e' validata dal trigger DB
#        `trgfn_ddt_guard_transizione` (matrice config.transizioni_stati_ddt):
#        il service non duplica il grafo. Alla transizione a EMESSO il DB
#        assegna il `numero` (trgfn_ddt_gen_numero_emesso) e scatta il guard
#        approvazione componenti BoM.
def cambia_stato(ddt_id: int, stato_codice: str) -> dict[str, Any]:
    repo = DdtRepository()
    # Guard esistenza leggero: serve solo lo stato corrente, non la testata
    # completa (vista + JOIN); la validazione della coppia e' del trigger DB.
    stato_prec = testata_o_not_found(
        repo.get_stato_codice, ddt_id,
        code="E_DDT_NOT_FOUND", message="DDT non trovato.",
        id_name="ddt_id", function_name=f"{_FN}.cambia_stato",
    )
    target = (stato_codice or "").strip()
    ErrorManager.require(
        bool(target),
        code="E_DDT_VALIDAZIONE",
        message="stato_codice obbligatorio per il cambio stato.",
        context={"field": "stato_codice"},
        function_name=f"{_FN}.cambia_stato",
    )
    stato_id = repo.get_stato_id_by_codice(target)
    ErrorManager.require(
        stato_id is not None,
        code="E_DDT_VALIDAZIONE",
        message=f"Stato '{target}' non configurato in config.stati_doc_ddt.",
        function_name=f"{_FN}.cambia_stato",
    )
    assert stato_id is not None
    # La transizione (stato_prec -> target) e' validata dal trigger guard DB;
    # eventuale errore tradotto da _db_errors (E_STATO_DDT_TRANSIZIONE_NON_VALIDA
    # / E_DOC_PREZZO_PENDENTE / E_DOC_PREZZO_RIFIUTATO alla transizione a
    # EMESSO, dal 2026-09-24 via script.fn_check_prezzi_autorizzati).
    with _db_errors("cambia_stato"):
        repo.update_stato(ddt_id, int(stato_id))
    return {"ddt_id": ddt_id, "stato_precedente": stato_prec, "stato": target}


# Scopo: Emette il DDT (DRAFT -> EMESSO). Alla transizione il DB assegna il
#        `numero` (C6, trgfn_ddt_gen_numero_emesso) e scatta il guard
#        approvazione componenti BoM (brief DB §6). Ritorna il risultato LIGHT
#        della transizione ({ddt_id, stato_precedente, stato}), parita' con
#        `ordini_service.conferma`: la view emissione documentale chiama emetti
#        dentro `transaction.atomic()` e il detail pesante (vista + capability
#        + count righe) non va materializzato nella sezione critica — il FE
#        ricarica comunque il detail dopo l'emissione.
def emetti(ddt_id: int) -> dict[str, Any]:
    return cambia_stato(ddt_id, _STATO_EMESSO)


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
    repo = DdtRepository()
    testata = _get_testata_or_raise(repo, ddt_id, op="gestisci_riga")
    richiedi_righe_in_bozza(
        testata, documento="DDT", documento_id=ddt_id, verbo="aggiungere",
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

    data = {k: empty_to_none(v) for k, v in payload.items() if k in CREATE_KEYS_RIGA}
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
    repo = DdtRepository()
    testata = _get_testata_or_raise(repo, ddt_id, op="aggiorna_riga")
    richiedi_righe_in_bozza(
        testata, documento="DDT", documento_id=ddt_id, verbo="modificare",
        function_name=f"{_FN}.aggiorna_riga",
    )
    _get_riga_or_raise(repo, ddt_id, riga_id, op="aggiorna_riga")
    data = {k: empty_to_none(v) for k, v in payload.items() if k in UPDATE_KEYS_RIGA}
    ErrorManager.require(
        len(data) > 0,
        code="E_DDT_VALIDAZIONE",
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
#        `trgfn_dlt_block_ordrig_ddtrig`, ridotto ai soli legami: riga legata
#        a un fulfillment -> E_DELETE_BLOCKED_FUL; riga usata in un reso o in
#        una riconsegna -> E_DELETE_RIGA_DOC_REFERENZIATA; altrimenti la
#        cancellazione RIESCE.
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
        testata, documento="DDT", documento_id=ddt_id, verbo="togliere",
        function_name=f"{_FN}.elimina_riga",
    )
    _get_riga_or_raise(repo, ddt_id, riga_id, op="elimina_riga")
    with _db_errors("elimina_riga"):
        deleted = repo.delete_riga(riga_id)
    return {"ddt_id": ddt_id, "riga_id": riga_id, "deleted": deleted}


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
        scope, documento="DDT", documento_id=ddt_id, verbo="modificare",
        function_name=f"{_FN}.update_componente",
    )
    # Contratto dell'operatore unico per i cinque documenti (BB): chiavi
    # estranee -> 400, `origine_prezzo` derivata dal prezzo. ⚠️ Fino al
    # 2026-09-26 qui c'era un filtro locale che SCARTAVA in silenzio le chiavi
    # estranee, compresa l'`origine_prezzo` mandata dal pannello: l'origine
    # manuale non veniva mai scritta.
    data = dati_patch_componente(
        payload, function_name=f"{_FN}.update_componente",
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
        scope, documento="DDT", documento_id=ddt_id, verbo="togliere",
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
#        PARZIALMENTE_EVASO/EVASO). NIENTE transaction.atomic() extra (come
#        crea_ordine_da_preventivo). `righe` = [{ordine_riga_id, qta_da_evadere}]
#        in UNITA' OPERATIVA; None = tutto il residuo. Ritorna
#        {ddt_id, numero(None in DRAFT), ordine_id}.
def crea_ddt_da_ordine(
    ordine_id: int, righe: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    repo = DdtRepository()
    # Errori del guard fulfillment/evasione (E_DDT_ORDINE_NOT_FOUND,
    # E_DDT_ORDINE_STATO_NON_EVADIBILE, E_DDT_NIENTE_DA_EVADERE,
    # E_QTA_SUPERA_RESIDUO) sollevati dalla fn DB -> tradotti da _db_errors.
    with _db_errors("crea_ddt_da_ordine"):
        ddt_id = repo.push_da_ordine(int(ordine_id), righe)
    # UX v2: la cascata DB copia gli indirizzi dell'ordine; se l'ordine non
    # aveva la consegna, fallback best-effort dall'anagrafica di ruolo
    # (l'helper salta se lo slot default e' gia' valorizzato).
    auto_assegna_indirizzo_default(_INDIRIZZI_CFG, int(ddt_id))
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
            sorgente_codice="DDT_VENDITA",
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
)


# Scopo: Carica la testata DDT o solleva E_DDT_NOT_FOUND (BB core
#        `testata_o_not_found`: qui solo codice e messaggio del dominio).
def _get_testata_or_raise(
    repo: DdtRepository, ddt_id: int, *, op: str,
) -> dict[str, Any]:
    return testata_o_not_found(
        repo.get_ddt, ddt_id,
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
