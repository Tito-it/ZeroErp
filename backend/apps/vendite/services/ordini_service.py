# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per ordini di vendita (CRUD, stato, righe, push).
# ------------------------------------------------------------

# Orchestrazione ordini di vendita: validazione, guard su stato, delega al
# repository, pricing via building block condivisi (PricingService — regola del
# 2, mai query dirette su listini), componenti BoM via fn DB
# `fn_ordine_riga_componenti_*`, push singolo a commessa.
#
# Scheletro (analisi-ordini-vendita.md §5): niente revisioni (gli ordini non le
# hanno). Il gate prezzi L2/L3 stile contratti e' una DECISIONE DI DOMINIO ANCORA
# APERTA (analisi §8.bis): qui si usa il pricing stile preventivo (resolve +
# prezzo passato dal caller), passando comunque dai BB condivisi.

import logging
from datetime import date
from collections.abc import Callable
from typing import Any

from django.db import transaction

from apps.config.sorgenti import (
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
)
from apps.core.db._helpers import richiedi_codice_a_vocabolario
from apps.core.api.constants import MAX_LIMIT
from apps.core.services.documento_modello import rifiuta_stato_di_emissione
from apps.core.services.error_manager import ErrorManager
from apps.vendite.services._cliente_dal_ba import FK_CLIENTE_DIVERSO_DA_BA
from apps.vendite.services._righe_bozza_guard import richiedi_righe_in_bozza
from apps.vendite.services._date_consegna_righe import aggiorna_date_consegna_righe
from apps.vendite.services._annullo_con_legami import (
    STATO_ANNULLATO,
    legami_del_documento,
    legami_confermati as dichiarazione_legami,
)
from apps.vendite.services._iva_contesto_documento import make_risolvi_iva_riga
from apps.core.services.payload_helpers import PayloadValidator, make_db_errors_translator
from apps.core.services.testata_guard import (
    pagina_dopo_testata,
    riga_del_padre_o_not_found,
    testata_o_not_found,
)
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.ordini_repository import TESTATA_ORDINI, OrdiniRepository
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
# nella traduzione errori DB. I codici trigger E_ORDINE_* sono estratti via regex.
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"

# Mappe vincolo DB -> (codice, messaggio) per map_integrity_error (frammento
# nome vincolo). Minime: i casi non mappati cadono su E_VENDITE_VALIDATION.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_ordrig_riga_nr": (E_VENDITE_DUPLICATO, "Numero riga duplicato sull'ordine."),
    "uq_ordini_v_anno_serie_numero": (E_VENDITE_DUPLICATO, "Numero ordine duplicato."),
    # Univocità 1:1 offerta→ordine: la violazione dell'indice parziale diventa
    # lo stesso errore parlante del verbo `fn_genera_ordine_da_offerta`. Il
    # verbo blocca l'offerta `FOR UPDATE`, quindi due generazioni si mettono in
    # fila: l'indice resta la rete.
    "uq_ordini_v_documento_origine_offerta": (
        "E_ORD_OFFERTA_GIA_CONVERTITA",
        "Un ordine è già stato generato da questa offerta.",
    ),
}
_FK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "fk_ordrig_articolo": (E_VENDITE_FK, "Articolo non valido."),
    "fk_ordini_v_billing_account": (E_VENDITE_FK, "Cliente (billing account) non valido."),
    "fk_ordini_v_cliente_ruolo": (E_VENDITE_FK, "Cliente non valido."),
    # Rete sotto il BB `fn_cliente_dal_billing_account` (che risponde prima,
    # col suo codice): ruolo o utility diversi da quelli del BA.
    "fk_ordini_ba_cliente": FK_CLIENTE_DIVERSO_DA_BA,
}

# CHECK di dominio. `chk_ordini_fatturazione_trigger` diventa raggiungibile solo
# con i changeSet del 2026-08-17: finora `trgfn_ordini_normalize` sovrascriveva
# il valore PRIMA che il CHECK guardasse, quindi la colonna accettava qualunque
# stringa e la riciclava in un valore valido — una difesa che sembrava esserci
# e non c'era (rilievo del team DB, scoperto dal loro pgTAP: «caught: no
# exception»). Da quell'apply un valore fuori dominio solleva davvero: senza
# questa riga arriverebbe al FE il messaggio generico di fallback, che non dice
# quale campo è sbagliato né quali valori sono ammessi.
_CHECK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "chk_ordini_fatturazione_trigger": (
        E_VENDITE_VALIDATION,
        "Trigger di fatturazione non valido: ammessi CONFERMATO, SPEDITO, CONSEGNATO.",
    ),
}

# ── Costanti di dominio ──
_FN = "vendite.ordini_service"
_STATO_CONFERMATO = "CONFERMATO"
_STATI_MODIFICABILI: frozenset[str] = frozenset({"DRAFT"})
# Stati che ammettono il push a commessa (fix orfano 2026-07-10, brief DB §16:
# decoupling fatturazione/spedizione). Per trigger CONFERMATO l'eleggibilita'
# sopravvive all'evasione in DDT (PARZIALMENTE_EVASO/EVASO): la FONTE UNICA e'
# `fn_list_ordini_da_pushare` (trigger + righe + anti-doppione EMESSA), questo
# guard e' solo il fail-fast parlante per gli stati mai pushabili (DRAFT/ANNULLATO).
_STATI_PUSHABILI: frozenset[str] = frozenset(
    {"CONFERMATO", "PARZIALMENTE_EVASO", "EVASO"},
)

# Whitelist campi testata accettati in create/update (null_vs_empty → None).
# `fatturazione_immediata` (simmetria del flag, Fase B del brief emissione
# mirata): instradamento di CORSIA deciso PRIMA del push in commessa — dopo il
# push il flag e' inerte (fa parte della chiave di dedup della commessa) e il
# guard DB `trgfn_guard_fatturazione_immediata_immutabile` respinge l'UPDATE.
# Qui non serve una difesa applicativa: dopo il push lo respinge quel guard,
# che guarda la commessa viva e non lo stato (il lock di testata fuori bozza
# non nomina il flag: resta modificabile da confermato finche' non c'e' una
# commessa, D-14 di brief-db-annullo-a-valle-riapre-a-monte).
# ⛔ `soggetto_ruolo_id` e `utility_id` NON ci sono (2026-10-10): sono copie
# del BA, le scrive `trgfn_ordini_normalize` col BB
# `script.fn_cliente_dal_billing_account` (brief-db-esecutivi-ba-coppia D-1,
# D-5, §10.2 domanda 2). Un client che le manda riceve un 400 (chiave fuori
# contratto, dal 2026-10-20; prima le vedeva scartate).
CREATE_KEYS_ORDINE: frozenset[str] = frozenset({
    "billing_account_id",
    "emittente_fiscale_id", "valuta_id", "modalita_pagamento_id",
    "termine_pagamento_id", "fatturazione_trigger", "agente_soggetto_ruolo_id",
    "data", "meta", "fatturazione_immediata",
})
# `billing_account_id` c'e' e arriva al DB, che lo blocca dopo la creazione
# (lock di colonna, E_ORD_CLIENTE_IMMUTABILE): rimandato invariato passa, un
# cambio e' rifiutato col codice del DB. Utility fuori, come in create.
UPDATE_KEYS_ORDINE: frozenset[str] = frozenset({
    "billing_account_id", "valuta_id", "modalita_pagamento_id",
    "termine_pagamento_id", "fatturazione_trigger", "agente_soggetto_ruolo_id",
    "data", "meta", "fatturazione_immediata",
})
    # ⛔ `iva_id` NON C'E' PIU' (`I6`, 2026-08-31): l'aliquota della riga la
    # decide il risolutore, e la casella a video e' spenta. Rimetterla qui
    # riaprirebbe la seconda risposta alla stessa domanda che tutto questo
    # cantiere e' servito a togliere.
    # ⛔ Una chiave fuori whitelist e' un 400 (dal 2026-10-20): prima veniva
    # scartata in silenzio, e un client vecchio non sapeva che il valore non
    # arrivava.
CREATE_KEYS_RIGA: frozenset[str] = frozenset({
    "articolo_id", "descrizione", "quantita", "qta_operativa",
    "uom_operativa_id", "factor_to_base", "prezzo_unitario", "sconto_percentuale",
    "meta",
    "data_consegna_richiesta_cliente", "data_consegna_confermata",
})
# Le chiavi AMMESSE nella creazione di una riga: le colonne qui sopra piu' la
# mappa degli override dei prezzi dei componenti, che non e' una colonna e si
# legge a parte (`normalize_componenti_overrides`). Come il gemello DDT.
CREATE_PAYLOAD_RIGA: frozenset[str] = CREATE_KEYS_RIGA | {"componenti_overrides"}
UPDATE_KEYS_RIGA: frozenset[str] = frozenset({
    "descrizione", "quantita", "qta_operativa", "uom_operativa_id",
    "factor_to_base", "prezzo_unitario", "sconto_percentuale", "meta",
    "data_consegna_richiesta_cliente", "data_consegna_confermata",
})
# Le due date di consegna della riga (brief-db-modifiche-certe-ciclo-vendita-e-
# articolo, Blocco A): la RICHIESTA e' del cliente, la CONFERMATA e' la nostra
# promessa. Entrambe nullable: ometterle resta legittimo, e in PATCH un `null`
# esplicito AZZERA (semantica dei documenti vendite, come per `meta`).
# ⛔ Nessun CHECK fra le due, ed e' una scelta del modello (brief §2.3): si puo'
#    confermare PRIMA di quanto chiesto. Qui si controlla solo la FORMA — una
#    data malformata e' un 400 col campo acceso, non un 500 dal DB.
# ⚠️ `data_consegna_confermata` e' «quando ci si impegna», cioe' si decide alla
#    conferma e puo' cambiare dopo; ma le righe si scrivono solo in DRAFT
#    (BB `richiedi_righe_in_bozza`, codice `E_RIGA_DOC_NON_BOZZA`). Dal
#    `20261008-90` lo dice anche il DB, sulle tre porte, con una sola
#    eccezione: un UPDATE della sola `data_consegna_confermata` in
#    CONFERMATO/PARZIALMENTE_EVASO (brief-db-righe-e-componenti-debiti-residui,
#    D-1). Quell'eccezione NON passa da `aggiorna_riga` (che resta «solo in
#    bozza»): ha il verbo suo, `cambia_data_consegna_confermata`, sulla
#    capability letta dal DB (brief-db-testata-dopo-emissione, fase 1).
_DATA_CONSEGNA_CONFERMATA = "data_consegna_confermata"
_DATE_RIGA: tuple[str, ...] = (
    "data_consegna_richiesta_cliente", _DATA_CONSEGNA_CONFERMATA,
)
# Validator del dominio (testata e date di riga): solleva `E_ORD_VALIDAZIONE`
# con `context.field` = la chiave, cosi' l'input si accende (`campiErrati`).
# Uno solo: il codice e' lo stesso, e il validator non ha stato da separare.
_V = PayloadValidator(validation_code="E_ORD_VALIDAZIONE")


# ══════════════════════════════════════════════════════════
#  LETTURE — Lista (envelope + rows per export)
# ══════════════════════════════════════════════════════════

# Scopo: Letture grezze (righe + totale) della lista ordini. Condivisa tra
#        lista paginata (envelope) ed export (DEF-1) — regola del 2.
def list_ordini_rows(
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
        "config.stati_doc_ordini", "codice_interno", stato_codice,
        codice_errore="E_ORD_VALIDAZIONE", parametro="stato_codice_interno",
    )
    repo = OrdiniRepository()
    return repo.list_ordini(
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
#        export (DEF-1). Gemello resolve_filtri_export_label preventivi.
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


# Scopo: Dettaglio testata ordine (righe lette a parte via /righe/).
def get_ordine(ordine_id: int) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="get_ordine")
    righe_count = repo.count_righe(ordine_id)
    # Capability data-driven da script.fn_available_actions_ordine (matrice
    # config.transizioni_stati_ordini): available_actions (conferma/annulla/
    # push), can_edit_testata/righe, can_push_commessa(+reason), non_editable_
    # fields, stato_codice. Sostituisce il calcolo hardcoded: la verita' e' a DB
    # (lettura) + trigger guard (enforcement). `can_conferma` non e' piu' un
    # flag: la conferma e' un'entry di available_actions (key='conferma').
    # Il blob viaggia SOTTO `capabilities` (api.md §«Il blob sta SOTTO
    # `capabilities`»).
    capabilities = repo.get_capabilities(ordine_id)
    return {
        **testata,
        "capabilities": capabilities,
        "righe_count": righe_count,
    }


# Scopo: Lista righe di un ordine. Legge prima la testata: un ordine fuori
#        perimetro (o inesistente) e' un 404, non un pannello vuoto.
def list_righe(ordine_id: int) -> list[dict[str, Any]]:
    repo = OrdiniRepository()
    _get_testata_or_raise(repo, ordine_id, op="list_righe")
    return repo.list_righe(ordine_id)


# Scopo: Una PAGINA delle righe del ordine, per la lista configurabile
#        (`GET …/righe/lista/`): ricerca, ordinamento e pagina dal BB del
#        repository, dopo la testata (BB core `pagina_dopo_testata`).
#        Ritorna `(righe, totale)`.
def list_righe_pagina(ordine_id: int, **opzioni: Any) -> tuple[list[dict[str, Any]], int]:
    repo = OrdiniRepository()
    return pagina_dopo_testata(
        lambda: _get_testata_or_raise(repo, ordine_id, op="list_righe_pagina"),
        repo.list_righe_pagina, ordine_id, **opzioni,
    )


# Scopo: risolve l'ordine COLLEGATO a una pratica (per gli step a valle del
# percorso: CONFERMA_ORDINE / INVIO_COMMESSA aprono l'OrdiniDrawer su quell'ordine).
# Ritorna {"ordine_id": <id|null>}.
def get_ordine_per_pratica(pratica_id: int) -> dict[str, Any]:
    ErrorManager.require(
        pratica_id > 0,
        code="E_PRATICA_ID_INVALIDO",
        message="pratica_id non valido.",
        detail=f"pratica_id={pratica_id}",
        function_name=f"{_FN}.get_ordine_per_pratica",
    )
    return {"ordine_id": OrdiniRepository().get_ordine_id_by_pratica(pratica_id)}


# Step ordine del percorso pratica (bivio-per-esito rev.3). Entrambi si completano
# POSITIVO all'azione standalone del programma base: CONFERMA_ORDINE alla conferma
# dell'ordine (sblocca INVIO_COMMESSA, prereq 60←50 POSITIVO); INVIO_COMMESSA al
# push a commessa (terminale → sblocca la chiusura della pratica).
_ESITO_STEP_ORDINE = "POSITIVO"
_CODICE_CONFERMA_ORDINE = "CONFERMA_ORDINE"
_CODICE_INVIO_COMMESSA = "INVIO_COMMESSA"


# Scopo: Auto-completa (idempotente) il flusso `codice_flusso` della pratica cui
#        l'ordine e' COLLEGATO, all'azione standalone del programma base. Mirror
#        di preventivi_service._completa_flusso_preventivazione per gli step
#        ordine: la pratica orchestra ma il "successo" dello step e' l'azione
#        stessa (conferma / push), non un handler che decide al posto
#        dell'operatore. No-op se: l'ordine non e' in una pratica; lo step non e'
#        istanziato; lo step e' gia' terminale (ri-azione). Direzione
#        vendite→pratiche, import lazy.
def _completa_flusso_ordine_pratica(
    ordine_id: int, *, codice_flusso: str, user: str | None = None,
) -> None:
    from apps.pratiche.db.pratiche_repository import PraticheRepository
    from apps.pratiche.services import pratiche_service

    pratica_id = PraticheRepository().get_pratica_id_by_sorgente(
        sorgente_codice=SORGENTE_ORDINE_VENDITA, sorgente_uid=str(ordine_id),
        ruolo_link="COLLEGATO",
    )
    if pratica_id is None:
        return  # ordine non nato da una pratica → nessuno step da completare
    # Idempotenza + percorso + avvia-e-completa/completa: delegati al BB motore
    # (completa_step_pratica). No-op se lo step non e' istanziato o gia' terminale.
    pratiche_service.completa_step_pratica(
        pratica_id, template_codice=codice_flusso, esito=_ESITO_STEP_ORDINE, user=user,
    )


# Scopo: Riepilogo IVA aggregato dell'ordine (una riga per aliquota). Calcolo
#        fiscalmente corretto gia' applicato in DB via la view derivata
#        vw_ordini_riepilogo_iva_dettaglio (stessa formula dei preventivi): il
#        service legge, nessun ricalcolo Python. Usato dal FE per il pannello
#        "Riepilogo IVA" del drawer ordine e dal context builder della stampa.
#        Legge prima la testata: fuori perimetro e' un 404.
def list_riepilogo_iva(ordine_id: int) -> list[dict[str, Any]]:
    repo = OrdiniRepository()
    _get_testata_or_raise(repo, ordine_id, op="list_riepilogo_iva")
    return repo.list_riepilogo_iva(ordine_id)


# ── Indirizzi documento (BB condiviso _indirizzi_documento_helpers) ──

_INDIRIZZI_CFG = IndirizziDocumentoConfig(
    # lambda (non la classe): risolve il nome a call-time, cosi' i @patch
    # dei test unit raggiungono il repository.
    repo_factory=lambda: OrdiniRepository(),
    not_found_code="E_ORD_NOT_FOUND",
    error_code="E_ORD_VALIDAZIONE",
    fn_prefix=_FN,
)


# Scopo: Pannello indirizzi dell'ordine (ambito ORDINI). Guard di esistenza e
#        traduzione errori DB nel BB condiviso.
def list_indirizzi(ordine_id: int) -> dict[str, Any]:
    return list_indirizzi_documento(_INDIRIZZI_CFG, ordine_id)


# Scopo: Upsert slot indirizzo (uno-per-tipo, solo DRAFT).
def upsert_indirizzo(ordine_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return upsert_indirizzo_documento(_INDIRIZZI_CFG, ordine_id, payload)


# Scopo: Rimozione slot indirizzo (solo DRAFT).
def delete_indirizzo(ordine_id: int, indirizzo_id: int) -> dict[str, Any]:
    return delete_indirizzo_documento(_INDIRIZZI_CFG, ordine_id, indirizzo_id)


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Testata
# ══════════════════════════════════════════════════════════

# Scopo: Crea un nuovo ordine. `numero` generato dal trigger DB. Il cliente e'
#        il BA (obbligatorio, D-1): ruolo e utility li scrive il DB dal BA.
#        Lo stato non si passa: l'ordine nasce nello stato iniziale del suo
#        vocabolario, e lo mette il DB (BB `script.trgfn_doc_stato_iniziale`,
#        brief-modello-documento-vendita P-2).
def crea_ordine(payload: dict[str, Any]) -> dict[str, Any]:
    repo = OrdiniRepository()
    # Il contratto: una chiave fuori whitelist e' un 400, mai uno scarto muto.
    data = _V.solo_chiavi_ammesse(payload, ammesse=CREATE_KEYS_ORDINE, function_name=f"{_FN}.crea_ordine")

    billing_account_id = _V.require_positive_int(
        data, "billing_account_id",
        message="Cliente (billing account) obbligatorio.",
        function_name=f"{_FN}.crea_ordine",
    )

    # Creazione e slot di default in UNA transazione (il riempimento non e'
    # best-effort: api.md §Atomicita').
    with _db_errors("crea_ordine"), transaction.atomic():
        creato = repo.create_ordine(
            billing_account_id=billing_account_id,
            emittente_fiscale_id=data.get("emittente_fiscale_id"),
            valuta_id=data.get("valuta_id"),
            modalita_pagamento_id=data.get("modalita_pagamento_id"),
            termine_pagamento_id=data.get("termine_pagamento_id"),
            fatturazione_trigger=data.get("fatturazione_trigger"),
            agente_soggetto_ruolo_id=data.get("agente_soggetto_ruolo_id"),
            data=data.get("data"),
            meta=data.get("meta") if isinstance(data.get("meta"), dict) else None,
            fatturazione_immediata=data.get("fatturazione_immediata"),
        )
        # Slot di default dall'anagrafica del cliente: lo decide il DB
        # (`vendite.fn_doc_indirizzo_default`). La conversione da offerta non
        # passa da qui: il verbo DB lo chiama da se'.
        repo.riempi_indirizzo_default(int(creato["id"]))
    return creato


# Scopo: Aggiorna testata ordine.
#
# Quali colonne si cambiano in quale stato lo dice il DB, colonna per colonna:
# il lock di testata `vendite.trgfn_doc_testata_lock_fuori_bozza` (in bozza
# tutto; dopo, le note finche' l'ordine non e' chiuso). Fino al 2026-10-10 qui
# c'era un «solo in DRAFT» che ne era la seconda copia
# (brief-db-testata-dopo-emissione, D-0 e R-BE-2): il 409 del lock passa com'e'.
# Il cliente non cambia dopo la creazione, e lo dice il DB (lock di colonna su
# `billing_account_id` e `soggetto_ruolo_id`, E_ORD_CLIENTE_IMMUTABILE): il BA
# e' in whitelist e arriva fin li'. Fino al 2026-10-10 qui c'era una copia del
# lock in Python, nata quando nessun trigger ri-sincronizzava il ruolo.
def aggiorna_ordine(ordine_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = OrdiniRepository()
    # Prima la testata: fuori perimetro o inesistente e' un 404. Basta sapere
    # che esiste: il lettore leggero, non la testata intera.
    _get_testata_or_raise(repo, ordine_id, op="aggiorna_ordine", getter=repo.get_stato_codice)

    # Il contratto: una chiave fuori whitelist e' un 400, mai uno scarto muto.
    data = _V.solo_chiavi_ammesse(payload, ammesse=UPDATE_KEYS_ORDINE, function_name=f"{_FN}.aggiorna_ordine")
    if "billing_account_id" in data:
        # Un id non numerico e' un 400 col campo, non un 500 dal driver.
        data["billing_account_id"] = _V.optional_positive_int(
            data, "billing_account_id", function_name=f"{_FN}.aggiorna_ordine",
        )
    _V.require_campi_da_aggiornare(
        data,
        function_name=f"{_FN}.aggiorna_ordine",
    )
    with _db_errors("aggiorna_ordine"):
        repo.update_ordine(ordine_id, **data)
    return {"ordine_id": ordine_id, "updated": True}


# ══════════════════════════════════════════════════════════
#  CONVERSIONE UPSTREAM — preventivo/offerta → ordine (§7.4)
# ══════════════════════════════════════════════════════════

# Nessuna whitelist Python degli stati d'origine: lo stato ammesso lo dicono i
# verbi DB, `fn_push_preventivo_a_ordine` (con «nessuna riga merce», modello
# split) e `fn_genera_ordine_da_offerta`.


# Scopo: Smistamento MERCE → ordine da un preventivo ACCETTATO (modello split,
#        brief-preventivi-ordini.md D8). NON più copia-tutto 1:1: delega alla
#        primitiva DB vendite.fn_push_preventivo_a_ordine (via
#        PreventiviRepository.push_a_ordine), che:
#          - copia SOLO le righe con natura destinazione_tipo='ORDINE_VENDITA' (i servizi
#            una-tantum vanno a commessa via push_a_commessa; il ricorrente è
#            bloccato a monte, D9);
#          - mantiene lo snapshot prezzi + componenti BoM;
#          - SCRIVE il link di riga ordini_righe.preventivo_riga_id → idempotenza
#            di riga (la stessa merce non finisce su due ordini: niente più
#            doppio-ordine del vecchio copia-tutto).
#        Stato ammesso e "nessuna riga merce residua" sono validati dalla fn DB
#        (E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO /
#        E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE) → nessun guard duplicato qui.
#        p_pratica_id=NULL: uso standalone (fuori-pratica); sul percorso pratica
#        lo smistamento è orchestrato da CONFERMA_VENDITA. `righe_ids` opzionale:
#        None = tutte le righe merce residue (D2 "preseleziona tutte"); un
#        sottoinsieme abilita lo smistamento selettivo (Pannello Smistamento).
def crea_ordine_da_preventivo(
    preventivo_id: int, righe_ids: list[int] | None = None,
) -> dict[str, Any]:
    # Import locale: evita accoppiamento a livello di modulo tra i due domini
    # (entrambi in apps.vendite) e qualunque rischio di import circolare.
    from apps.vendite.db.preventivi_repository import PreventiviRepository

    prev_repo = PreventiviRepository()
    # Fix analisi-fix-transazioni #10 (Classe A): la fn madre estesa
    # vendite.fn_push_preventivo_a_ordine crea l'ordine E transita il preventivo a
    # EVASO — se nessun residuo ordine/commessa, stessa condizione del vecchio gate
    # Python — in UN'UNICA statement atomica. Prima la transizione EVASO era una
    # chiamata separata best-effort (swallow_db_error): su errore l'ordine restava
    # creato ma il preventivo ACCETTATO (stato parziale, merce gia' su ordine). Ora
    # e' tutto-o-niente: niente piu' transiziona_a_evaso_se_smistato qui (il gate
    # bi-ramo vive dentro la fn). Dal 2026-10-12 la regola ha una sede sola, il
    # BB DB `vendite.fn_preventivo_proietta_stato_smistamento`, letto anche
    # dall'invio in commessa: l'helper Python e' ritirato.
    # Il verbo e il default nella stessa transazione: la cascata DB copia gli
    # indirizzi del preventivo, e il default riempie lo slot SOLO se e'
    # rimasto vuoto (la sorgente vince). `_db_errors` fuori dall'atomic, come
    # `crea_ddt_da_ordine`: i guard della fn (stato, nessuna riga merce) e gli
    # errori del default arrivano al client col loro codice, non come 500.
    with _db_errors("crea_ordine_da_preventivo"), transaction.atomic():
        ordine_id = prev_repo.push_a_ordine(
            preventivo_id, righe_ids=righe_ids, pratica_id=None,
        )
        OrdiniRepository().riempi_indirizzo_default(int(ordine_id))

    # Numero ordine per il messaggio FE (lettura leggera post-creazione).
    testata = OrdiniRepository().get_ordine(ordine_id)
    numero = testata.get("numero") if testata else None
    return {
        "ordine_id": ordine_id,
        "numero": numero,
        "documento_origine": {"tipo": SORGENTE_PREVENTIVO, "id": int(preventivo_id)},
    }


# Scopo: Genera un ordine DRAFT da un'offerta ACCETTATA. Lo fa il DB, in UNA
#        transazione: il verbo `vendite.fn_genera_ordine_da_offerta` (gemello
#        del push al contratto) blocca l'offerta, verifica lo stato e i
#        documenti vivi, giudica le righe con la stessa check che spegne
#        «Genera ordine» nella capability, scrive testata e provenienza, riempie
#        l'indirizzo di default e copia le righe espanse coi prezzi negoziati
#        (componenti compresi). Ritorna l'id dell'ordine.
#        ⛔ Fino al 2026-10-21 (brief-db-offerta-emissione-ed-erogazione I-D2)
#        l'orchestrazione era qui, in Python: stato, documenti vivi, testata,
#        provenienza e copia delle righe erano specchi di regole del DB, e le
#        righe dell'ordine non le giudicava nessuno prima di scrivere. I rifiuti
#        arrivano ora col codice del verbo (`E_OFFERTA_NON_TROVATA`,
#        `E_ORD_ORIGINE_NON_CONVERTIBILE`, `E_ORD_OFFERTA_GIA_CONVERTITA`,
#        `E_OFFERTA_CONTRATTO_GIA_GENERATO` col bersaglio,
#        `E_DOC_RIGA_NON_AMMESSA` col campo `articolo_id`).
def crea_ordine_da_offerta(offerta_id: int) -> dict[str, Any]:
    from apps.vendite.db.offerte_repository import OfferteRepository

    # `_db_errors` fuori dall'atomic, come `crea_ordine_da_preventivo`: i
    # rifiuti del verbo arrivano al client col loro codice, non come 500.
    with _db_errors("crea_ordine_da_offerta"), transaction.atomic():
        ordine_id = OfferteRepository().genera_ordine(offerta_id)

    # Numero ordine per il messaggio FE (lettura leggera post-creazione).
    testata = OrdiniRepository().get_ordine(ordine_id)
    numero = testata.get("numero") if testata else None
    return {
        "ordine_id": ordine_id,
        "numero": numero,
        "documento_origine": {"tipo": SORGENTE_OFFERTA_COMMERCIALE, "id": int(offerta_id)},
    }


# Scopo: Hard-delete ordine BOZZA ORFANO (solo supporto al pattern "abbandono
#        bozza" del drawer: create auto-salva una BOZZA per abilitare le righe;
#        se l'operatore esce senza inserirne, la bozza vuota viene rimossa).
#        NON e' un'azione di cancellazione di ordini reali: un ordine con righe
#        o non in bozza NON si cancella, si ANNULLA (cambia_stato → ANNULLATO).
#        Allineato a `elimina_preventivo` (niente hard-delete di dati reali).
# Guard di dominio (defense-in-depth: il FE filtra gia' su righe_count=0):
#  - ordine esistente, stato BOZZA (DRAFT), zero righe.
def elimina_ordine(ordine_id: int) -> dict[str, Any]:
    repo = OrdiniRepository()
    _assert_stato(repo, ordine_id, _STATI_MODIFICABILI, op="elimina_ordine")
    righe_count = repo.count_righe(ordine_id)
    ErrorManager.require(
        righe_count == 0,
        code="E_ORD_STATO_TRANSIZIONE",
        message=(
            "Impossibile eliminare un ordine con righe: annullare l'ordine "
            "(cambio stato → ANNULLATO) invece di cancellarlo."
        ),
        detail=f"righe_count={righe_count}",
        function_name=f"{_FN}.elimina_ordine",
    )
    with _db_errors("elimina_ordine"):
        deleted = repo.delete_ordine(ordine_id)
    return {"ordine_id": ordine_id, "deleted": deleted}


# Scopo: Conferma ordine (DRAFT → CONFERMATO). La transizione e' validata dal
#        trigger DB; qui si applica solo il guard di stato + righe presenti.
def conferma(ordine_id: int, *, user: str | None = None) -> dict[str, Any]:
    repo = OrdiniRepository()
    stato = _assert_stato(repo, ordine_id, _STATI_MODIFICABILI, op="conferma")
    # Fail-fast allineato al guard DB (trgfn_ordini_guard_transizione, Regola
    # 2 rev 2026-07-16): contano solo le righe ATTIVE — un ordine con sole
    # righe disattivate non e' confermabile. Il guard autorevole resta il
    # trigger (E_ORDINE_CONFERMA_SENZA_RIGHE); qui si evita solo il round-trip.
    ErrorManager.require(
        repo.count_righe(ordine_id) > 0,
        code="E_ORD_NESSUNA_RIGA",
        message="Impossibile confermare un ordine senza righe attive.",
        detail=f"ordine_id={ordine_id}",
        function_name=f"{_FN}.conferma",
    )
    stato_conf_id = repo.get_stato_id_by_codice(_STATO_CONFERMATO)
    ErrorManager.require(
        stato_conf_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="Stato CONFERMATO non configurato in config.stati_doc_ordini.",
        function_name=f"{_FN}.conferma",
    )
    assert stato_conf_id is not None
    # Atomico: conferma ordine + completamento dello step CONFERMA_ORDINE del
    # percorso pratica sono un'unita' di lavoro (o entrambi o nessuno).
    with _db_errors("conferma"), transaction.atomic():
        repo.update_stato(ordine_id, int(stato_conf_id))
        # Percorso pratica: la conferma dell'ordine E' il successo dello step
        # CONFERMA_ORDINE → lo completa POSITIVO (sblocca INVIO_COMMESSA). No-op
        # se l'ordine non nasce da una pratica o lo step e' gia' chiuso.
        _completa_flusso_ordine_pratica(
            ordine_id, codice_flusso=_CODICE_CONFERMA_ORDINE, user=user,
        )
    return {"ordine_id": ordine_id, "stato_precedente": stato, "stato": _STATO_CONFERMATO}


# Scopo: Esegue una transizione di stato data-driven dell'ordine (es. annulla
#        DRAFT->ANNULLATO). Generico: lo stato destinazione arriva dal codice
#        interno (`available_actions[].target_state` della fn capabilities).
#        L'ammissibilita' della transizione e' validata dal trigger DB
#        `trgfn_ordini_guard_transizione` (matrice config.transizioni_stati_ordini):
#        il service non duplica il grafo. La conferma (DRAFT->CONFERMATO) ha un
#        endpoint dedicato (`conferma`) per le sue precondizioni; questa copre le
#        altre transizioni manuali esposte.
#        ⭐ ANNULLATO passa SEMPRE dal verbo `vendite.fn_annulla_ordine`
#        (brief-db-annullo-documento-con-legami): con legami il DB rifiuta
#        (E_DOC_ANNULLO_CON_LEGAMI, `confirm_and_retry`) finche' la richiesta
#        non dichiara `legami_confermati`, il numero letto da `get_legami`.
def cambia_stato(
    ordine_id: int, stato_codice: str | None, *, legami_confermati: Any = None,
) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="cambia_stato")
    stato_prec = testata.get("stato_codice_interno")
    # Un valore non testuale (un numero nel JSON) e' «stato mancante», un 400:
    # fino al 2026-10-09 `.strip()` su un int era un 500.
    target = stato_codice.strip() if isinstance(stato_codice, str) else ""
    ErrorManager.require(
        bool(target),
        code="E_ORD_VALIDAZIONE",
        message="stato_codice obbligatorio per il cambio stato.",
        function_name=f"{_FN}.cambia_stato",
    )
    # ⛔ Lo stato di emissione (CONFERMATO) NO (M-2, che revoca l'opzione (i)
    #    del 2026-06-05): l'ordine si emette da «Emetti» (`/emetti/`), che
    #    produce numero e PDF nella stessa transazione. Quale stato sia
    #    l'emissione lo dice il vocabolario (BB `rifiuta_stato_di_emissione`,
    #    brief-modello-documento-vendita §8.7 punto 4).
    rifiuta_stato_di_emissione(
        TESTATA_ORDINI, target, campo="stato_codice",
        validation_code="E_ORD_VALIDAZIONE", function_name=f"{_FN}.cambia_stato",
    )
    stato_id = repo.get_stato_id_by_codice(target)
    ErrorManager.require(
        stato_id is not None,
        code="E_ORD_VALIDAZIONE",
        message=f"Stato '{target}' non configurato in config.stati_doc_ordini.",
        function_name=f"{_FN}.cambia_stato",
    )
    assert stato_id is not None
    if target == STATO_ANNULLATO:
        confermati = dichiarazione_legami(
            legami_confermati, validation_code="E_ORD_VALIDAZIONE",
            function_name=f"{_FN}.cambia_stato",
        )
        with _db_errors("cambia_stato"):
            repo.annulla(ordine_id, confermati)
        return {"ordine_id": ordine_id, "stato_precedente": stato_prec, "stato": target}
    # La transizione (stato_prec -> target) e' validata dal trigger guard DB;
    # eventuale errore tradotto da _db_errors (E_ORDINE_TRANSIZIONE_NON_AMMESSA).
    with _db_errors("cambia_stato"):
        repo.update_stato(ordine_id, int(stato_id))
    return {"ordine_id": ordine_id, "stato_precedente": stato_prec, "stato": target}


# Scopo: I legami dell'ordine per la finestra di conferma dell'annullo (BB
#        `legami_del_documento`): righe di preventivo, offerta d'origine, righe
#        di commessa da emettere. Prima la testata: il lettore del DB non
#        applica il perimetro.
def get_legami(ordine_id: int) -> dict[str, Any]:
    repo = OrdiniRepository()
    _get_testata_or_raise(repo, ordine_id, op="get_legami", getter=repo.get_stato_codice)
    return legami_del_documento(SORGENTE_ORDINE_VENDITA, ordine_id)


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Righe (ricalcolo totali via trigger DB)
# ══════════════════════════════════════════════════════════

# Scopo: Aggiunge una riga all'ordine (solo DRAFT). Pricing stile preventivo:
#        se il prezzo non e' passato e l'articolo NON e' composito, lo risolve
#        via PricingService (BB condiviso). Per articolo composito il prezzo
#        padre e' 0 e i componenti BoM sono inizializzati via fn DB.
def gestisci_riga(
    ordine_id: int, payload: dict[str, Any], *, auth_user_id: int | None = None,
) -> dict[str, Any]:
    # ⛔ Una chiave fuori whitelist e' un 400, prima di qualunque lettura
    #    (2026-10-20; prima veniva scartata in silenzio). Come il gemello DDT:
    #    il dict tiene le sole colonne, la mappa dei componenti si legge a parte.
    data = _V.solo_chiavi_ammesse(
        payload, ammesse=CREATE_PAYLOAD_RIGA, colonne=CREATE_KEYS_RIGA,
        function_name=f"{_FN}.gestisci_riga",
    )
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="gestisci_riga")
    richiedi_righe_in_bozza(
        testata, documento=SORGENTE_ORDINE_VENDITA, documento_id=ordine_id, verbo="aggiungere",
        function_name=f"{_FN}.gestisci_riga",
    )

    # Override prezzi componenti BoM (dialog pre-save, simmetria preventivi).
    # Gate L1: l'override manuale richiede il permesso dedicato. Poi normalizza
    # la mappa {componente_id: prezzo} (None se assente). Applicata solo per
    # articolo composito (vedi init componenti sotto).
    validate_componenti_overrides_authorization(
        payload, auth_user_id, function_name=f"{_FN}.gestisci_riga",
    )
    componenti_overrides = normalize_componenti_overrides(
        payload.get("componenti_overrides"),
        function_name=f"{_FN}.gestisci_riga",
        error_code="E_ORD_VALIDAZIONE",
    )

    _parse_date_riga(data, function_name=f"{_FN}.gestisci_riga")
    articolo_id = data.get("articolo_id")
    ErrorManager.require(
        articolo_id is not None and str(articolo_id).strip() != "",
        code="E_ORD_VALIDAZIONE",
        message="articolo_id obbligatorio.",
        function_name=f"{_FN}.gestisci_riga",
    )
    assert articolo_id is not None

    is_composito = repo.is_articolo_composito(str(articolo_id))
    prezzo_unitario = data.get("prezzo_unitario")

    # Pricing auto-fill (solo articolo NON composito, prezzo non passato).
    if not is_composito and prezzo_unitario is None:
        prezzo_unitario = _resolve_prezzo_riga(
            repo, testata, articolo_id=str(articolo_id),
            uom_id=data.get("uom_operativa_id"),
        )
    elif is_composito:
        # Padre composito: prezzo = SUM(figli), ricalcolato dal trigger DB dopo
        # init componenti. Si inserisce con 0 per soddisfare l'eventuale guard.
        prezzo_unitario = prezzo_unitario if prezzo_unitario is not None else "0"

    # ⭐ L'IVA DI RIGA VIENE DALLA SEDE UNICA (I3, 2026-08-31): non piu' copiata
    # dall'articolo dal frontend, che era una seconda risposta alla stessa
    # domanda e ignorava uso della fornitura e titoli del cliente.
    # ⚠️ Il payload VINCE finche' `I6` non chiude la casella (opzione B): qui
    # si registra soltanto cosa avrebbe detto il risolutore.
    iva_id_riga, iva_meta = _risolvi_iva_riga(
        # ⛔ `payload_iva_id=None`, e non e' pigrizia: da `I6` la riga NON
        #    porta piu' un'IVA scelta a mano, quindi la risoluzione e'
        #    AUTORITATIVA e i suoi errori PASSANO. Meglio fermarsi che scrivere
        #    un'aliquota inventata su un documento che diventera' fiscale.
        testata, articolo_id=str(articolo_id), payload_iva_id=None,
    )
    meta_riga = data.get("meta") if isinstance(data.get("meta"), dict) else None
    if iva_meta:
        meta_riga = {**(meta_riga or {}), **iva_meta}

    with _db_errors("gestisci_riga"), transaction.atomic():
        riga_nr = repo.next_riga_nr(ordine_id)
        created = repo.create_riga(
            ordine_id=ordine_id,
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
            data_consegna_richiesta_cliente=data.get("data_consegna_richiesta_cliente"),
            data_consegna_confermata=data.get("data_consegna_confermata"),
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

    return {"ordine_id": ordine_id, "riga_id": riga_id, "is_composito": is_composito}


# Scopo: Aggiorna una riga ordine esistente (solo DRAFT).
def aggiorna_riga(
    ordine_id: int, riga_id: int, payload: dict[str, Any],
    *, auth_user_id: int | None = None,
) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="aggiorna_riga")
    richiedi_righe_in_bozza(
        testata, documento=SORGENTE_ORDINE_VENDITA, documento_id=ordine_id, verbo="modificare",
        function_name=f"{_FN}.aggiorna_riga",
    )
    _get_riga_or_raise(repo, ordine_id, riga_id, op="aggiorna_riga")
    # Il contratto: una chiave fuori whitelist e' un 400, mai uno scarto muto.
    data = _V.solo_chiavi_ammesse(payload, ammesse=UPDATE_KEYS_RIGA, function_name=f"{_FN}.aggiorna_riga")
    _V.require_campi_da_aggiornare(
        data,
        message="Nessun campo aggiornabile nel payload riga.",
        function_name=f"{_FN}.aggiorna_riga",
    )
    _parse_date_riga(data, function_name=f"{_FN}.aggiorna_riga")
    with _db_errors("aggiorna_riga"):
        repo.update_riga(riga_id, **data)
    return {"ordine_id": ordine_id, "riga_id": riga_id, "updated": True}


# Scopo: Cambia la data di consegna confermata di UNA riga, anche dopo la
#        conferma dell'ordine (brief-db-testata-dopo-emissione, fase 1, R-BE-1).
#
# Scrive la SOLA colonna `data_consegna_confermata` (`null` toglie la promessa:
# la colonna e' nullable). ⛔ Nessun pre-check di stato qui: in quali stati la
# data si cambia lo dice il lock delle righe (`trgfn_doc_righe_lock_fuori_bozza`,
# argomenti [4]/[5] del montaggio), e il 409 `E_RIGA_DOC_NON_BOZZA` passa com'e'.
# Il motivo per spegnere l'azione prima arriva dalla capability
# `can_edit_data_consegna_confermata`, che legge lo stesso montaggio.
# `aggiorna_riga` resta «solo in bozza» per tutte le colonne.
def cambia_data_consegna_confermata(
    ordine_id: int, riga_id: int, payload: dict[str, Any],
) -> dict[str, Any]:
    fn = f"{_FN}.cambia_data_consegna_confermata"
    repo = OrdiniRepository()
    _get_testata_or_raise(repo, ordine_id, op="cambia_data_consegna_confermata")
    _get_riga_or_raise(repo, ordine_id, riga_id, op="cambia_data_consegna_confermata")
    estranee = sorted(set(payload) - {_DATA_CONSEGNA_CONFERMATA})
    ErrorManager.require(
        not estranee,
        code="E_ORD_VALIDAZIONE",
        message="Il verbo cambia solo la data di consegna confermata.",
        detail=f"chiavi non ammesse: {estranee}",
        function_name=fn,
    )
    ErrorManager.require(
        _DATA_CONSEGNA_CONFERMATA in payload,
        code="E_ORD_VALIDAZIONE",
        message="Data di consegna confermata obbligatoria (null per toglierla).",
        context={"field": _DATA_CONSEGNA_CONFERMATA},
        function_name=fn,
    )
    data = {_DATA_CONSEGNA_CONFERMATA: empty_to_none(payload[_DATA_CONSEGNA_CONFERMATA])}
    _parse_date_riga(data, function_name=fn)
    # ⭐ La stessa scrittura dell'utility in blocco (BB `scrivi_data_consegna`,
    #    regola del 2), ristretta a questa riga: qui non si salta nulla, e una
    #    riga gia' spedita e' un 409 `E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA` del
    #    guard di riga (brief-db-date-consegna-righe-in-blocco, D-7).
    with _db_errors("cambia_data_consegna_confermata"):
        repo.scrivi_data_consegna(
            ordine_id, _DATA_CONSEGNA_CONFERMATA, data[_DATA_CONSEGNA_CONFERMATA],
            riga_id=riga_id,
        )
    return {
        "ordine_id": ordine_id,
        "riga_id": riga_id,
        _DATA_CONSEGNA_CONFERMATA: data[_DATA_CONSEGNA_CONFERMATA],
    }


# Scopo: «Aggiorna date di consegna» dell'ordine: una data su piu' righe, per
#        la richiesta dal cliente o per la confermata, in modalita' TUTTE o
#        SOLO_VUOTE (brief-db-date-consegna-righe-in-blocco, D-2). Le righe gia'
#        spedite si saltano e si contano. Regola e forma nel BB
#        `_date_consegna_righe`; qui solo la testata e il codice del dominio.
def aggiorna_date_consegna(ordine_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = OrdiniRepository()
    _get_testata_or_raise(
        repo, ordine_id, op="aggiorna_date_consegna", getter=repo.get_stato_codice,
    )
    with _db_errors("aggiorna_date_consegna"):
        return aggiorna_date_consegna_righe(
            repo, ordine_id, payload,
            error_code="E_ORD_VALIDAZIONE",
            function_name=f"{_FN}.aggiorna_date_consegna",
        )


# Scopo: Elimina riga ordine (HARD DELETE, solo DRAFT). I componenti BoM hanno
#        ON DELETE CASCADE; il trigger DB blocca se la riga e' collegata a DDT.
def elimina_riga(ordine_id: int, riga_id: int) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="elimina_riga")
    richiedi_righe_in_bozza(
        testata, documento=SORGENTE_ORDINE_VENDITA, documento_id=ordine_id, verbo="togliere",
        function_name=f"{_FN}.elimina_riga",
    )
    _get_riga_or_raise(repo, ordine_id, riga_id, op="elimina_riga")
    with _db_errors("elimina_riga"):
        deleted = repo.delete_riga(riga_id)
    return {"ordine_id": ordine_id, "riga_id": riga_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  Componenti riga (BoM CASO A)
# ══════════════════════════════════════════════════════════

# Scopo: Preview read-only componenti BoM per il drawer riga (pre-save).
def preview_componenti_riga(
    ordine_id: int, *, articolo_id: str, uom_operativa_id: int | None,
    quantita: Any, auth_user_id: int | None = None,
) -> list[dict[str, Any]]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="preview_componenti_riga")
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


# Scopo: Lista componenti persistiti di una riga. Guard di esistenza come
#        `aggiorna_riga`: la riga deve esistere ED appartenere all'ordine
#        richiesto (fuori perimetro o id incrociato → E_ORD_NOT_FOUND, 404).
def list_componenti_riga(
    ordine_id: int, riga_id: int, *, solo_attivi: bool = True,
) -> list[dict[str, Any]]:
    repo = OrdiniRepository()
    _get_riga_or_raise(repo, ordine_id, riga_id, op="list_componenti_riga")
    return repo.list_componenti_riga(riga_id, solo_attivi=solo_attivi)


# Scopo: Aggiorna un componente BoM (solo DRAFT, scope componente→riga→ordine).
def update_componente(
    ordine_id: int, riga_id: int, componente_id: int, payload: dict[str, Any],
    *, auth_user_id: int | None = None,
) -> dict[str, Any]:
    repo = OrdiniRepository()
    scope = repo.load_componente_with_scope(componente_id)
    ErrorManager.require(
        scope is not None and scope["ordine_id"] == ordine_id
        and scope["riga_ordine_id"] == riga_id,
        code="E_ORD_NOT_FOUND",
        message="Componente non trovato in questo ordine/riga.",
        function_name=f"{_FN}.update_componente",
    )
    assert scope is not None
    richiedi_righe_in_bozza(
        scope, documento=SORGENTE_ORDINE_VENDITA, documento_id=ordine_id, verbo="modificare",
        function_name=f"{_FN}.update_componente",
    )
    # Contratto dell'operatore unico per i cinque documenti (BB): chiavi
    # estranee -> 400, `origine_prezzo` derivata dal prezzo. ⚠️ Fino al
    # 2026-09-26 qui c'era un filtro locale che SCARTAVA in silenzio le chiavi
    # estranee, compresa l'`origine_prezzo` mandata dal pannello: l'origine
    # manuale non veniva mai scritta.
    data = dati_patch_componente(
        payload, auth_user_id=auth_user_id, function_name=f"{_FN}.update_componente",
        error_code="E_ORD_VALIDAZIONE",
    )
    with _db_errors("update_componente"):
        repo.update_componente(componente_id, **data)
    return {"componente_id": componente_id, "updated": True}


# Scopo: Elimina (soft, attivo=FALSE via mixin) un componente BoM (solo DRAFT).
def delete_componente(
    ordine_id: int, riga_id: int, componente_id: int,
) -> dict[str, Any]:
    repo = OrdiniRepository()
    scope = repo.load_componente_with_scope(componente_id)
    ErrorManager.require(
        scope is not None and scope["ordine_id"] == ordine_id
        and scope["riga_ordine_id"] == riga_id,
        code="E_ORD_NOT_FOUND",
        message="Componente non trovato in questo ordine/riga.",
        function_name=f"{_FN}.delete_componente",
    )
    assert scope is not None
    richiedi_righe_in_bozza(
        scope, documento=SORGENTE_ORDINE_VENDITA, documento_id=ordine_id, verbo="togliere",
        function_name=f"{_FN}.delete_componente",
    )
    with _db_errors("delete_componente"):
        deleted = repo.delete_componente(componente_id)
    return {"componente_id": componente_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  INTEGRAZIONE — Push singolo a commessa (chiusura giro)
# ══════════════════════════════════════════════════════════

# Scopo: Push singolo dell'ordine a commessa (chiusura giro). Riusa
#        l'orchestratore commesse esistente con sorgente ORDINE_VENDITA →
#        attivita_fatturabili → pipeline lotto → fattura. Pattern push singolo
#        gemello preventivi/offerte (decisione §8.3). Ammesso da CONFERMATO e
#        — fix orfano 2026-07-10 — anche da PARZIALMENTE_EVASO/EVASO (per
#        trigger CONFERMATO l'evasione in DDT non consuma la fatturazione).
def push_a_commessa(ordine_id: int, *, user: str | None = None) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="push_a_commessa")
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_PUSHABILI,
        code="E_ORD_STATO_TRANSIZIONE",
        message=(
            "Ordine non inviabile a commessa in questo stato (ammessi: "
            "confermato o evaso in attesa di fatturazione)."
        ),
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.push_a_commessa",
    )
    righe_count = repo.count_righe_pushable(ordine_id)
    ErrorManager.require(
        righe_count > 0,
        code="E_ORD_NESSUNA_RIGA",
        message="Nessuna riga eleggibile per il push a commessa.",
        detail=f"ordine_id={ordine_id}",
        function_name=f"{_FN}.push_a_commessa",
    )
    # Import locale per evitare cicli.
    from apps.vendite.services.commesse_service import pr_run_commesse_push_one

    # Fix analisi-fix-transazioni #4 (Classe B): push + chiusura step pratica in
    # UN solo transaction.atomic(). Prima erano scritture autocommit separate: se
    # `_completa_flusso_ordine_pratica` falliva DOPO il push, le commesse (+ ponte
    # emittibilita') restavano committate ma la pratica non riconciliata
    # (orfano). Ora un fallimento della chiusura-step rolla TUTTO il push, che e'
    # idempotente/ri-eseguibile (advisory lock + dedup segment_key → retry
    # sicuro). L'atomic interno di `pr_run_commesse_push_one` diventa un
    # savepoint annidato.
    # ⛔ L'invio in commessa NON cambia lo stato dell'ordine (D-6 di
    #    brief-db-annullo-a-valle-riapre-a-monte, 2026-10-12): «Evaso» vuol dire
    #    «la merce e' partita», e lo dicono solo le bolle
    #    (`vendite.fn_ordine_proietta_stato_evasione`). Fino a quel giorno qui
    #    l'ordine passava a EVASO «best-effort», e un PARZIALMENTE_EVASO mandato
    #    in commessa diventava EVASO con meta' merce in magazzino. Che l'ordine
    #    sia gia' in commessa lo dicono la lista «da mandare» e le capability.
    with transaction.atomic():
        report = pr_run_commesse_push_one(
            sorgente_codice=SORGENTE_ORDINE_VENDITA,
            sorgente_uid=ordine_id,
        )

        if report["stato"] == "COMPLETATO":
            # Percorso pratica: il push a commessa E' il successo dello step
            # INVIO_COMMESSA → lo completa POSITIVO. E' lo step TERMINALE del ramo
            # merce: completandolo (nessun altro flusso aperto, obbligatori fatti)
            # la pratica si chiude (auto-chiusura data-driven del motore). No-op se
            # l'ordine non nasce da una pratica. NON best-effort: un fallimento qui
            # rolla l'intero push (vedi atomic sopra).
            _completa_flusso_ordine_pratica(
                ordine_id, codice_flusso=_CODICE_INVIO_COMMESSA, user=user,
            )

    return {
        "ordine_id": ordine_id,
        "stato": report["stato"],
        "push_log_id": report["push_log_id"],
        "durata_ms": report["durata_ms"],
        "handlers": report["handlers"],
        # Commesse toccate dal push (gia' rese emittibili dal ponte in
        # pr_run_commesse_push_one): il FE puo' navigare/ispezionare.
        "commesse_ids": report.get("commesse_ids", []),
        "righe_pushable": righe_count,
        "fatturazione_trigger": testata.get("fatturazione_trigger"),
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
    fallback_message="Violazione vincolo DB su ordine.",
    unique_constraints=_UNIQUE_CONSTRAINTS,
    fk_constraints=_FK_CONSTRAINTS,
    check_constraints=_CHECK_CONSTRAINTS,
)


# Scopo: Carica la testata ordine o solleva E_ORD_NOT_FOUND (BB core
#        `testata_o_not_found`: qui solo codice e messaggio del dominio).
# `getter` ammette il lettore leggero `get_stato_codice`, dove al chiamante
# basta sapere che il documento esiste (stessa forma di
# `offerte_service._get_offerta_or_raise`).
def _get_testata_or_raise(
    repo: OrdiniRepository, ordine_id: int, *, op: str,
    getter: Callable[[int], Any] | None = None,
) -> Any:
    return testata_o_not_found(
        getter or repo.get_ordine, ordine_id,
        code="E_ORD_NOT_FOUND", message="Ordine non trovato.",
        id_name="ordine_id", function_name=f"{_FN}.{op}",
    )


# Scopo: Carica la riga o solleva E_ORD_NOT_FOUND se non esiste o non e' di questo
#        documento (BB core `riga_del_padre_o_not_found`: qui solo codice e
#        messaggio del dominio).
def _get_riga_or_raise(
    repo: OrdiniRepository, ordine_id: int, riga_id: int, *, op: str,
) -> dict[str, Any]:
    return riga_del_padre_o_not_found(
        repo.get_riga, riga_id, padre_id=ordine_id, chiave_padre="ordine_id",
        code="E_ORD_NOT_FOUND", message="Riga non trovata per questo ordine.",
        function_name=f"{_FN}.{op}",
    )


def _assert_stato(
    repo: OrdiniRepository, ordine_id: int, ammessi: frozenset[str], *, op: str,
) -> str:
    # Stesso BB del guard di testata, col getter leggero (solo codice_interno).
    stato = testata_o_not_found(
        repo.get_stato_codice, ordine_id,
        code="E_ORD_NOT_FOUND", message="Ordine non trovato.",
        id_name="ordine_id", function_name=f"{_FN}.{op}",
    )
    ErrorManager.require(
        stato in ammessi,
        code="E_ORD_STATO_TRANSIZIONE",
        message=f"Operazione non ammessa nello stato {stato}.",
        detail=f"ammessi={sorted(ammessi)}",
        function_name=f"{_FN}.{op}",
    )
    return stato


def _resolve_emittente_sr_id(repo: OrdiniRepository, testata: dict[str, Any]) -> int:
    fiscale_id = testata.get("emittente_fiscale_id")
    ErrorManager.require(
        fiscale_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="Ordine senza emittente fiscale: impossibile risolvere i componenti.",
        function_name=f"{_FN}._resolve_emittente_sr_id",
    )
    assert fiscale_id is not None
    sr_id = repo.get_emittente_sr_id_by_fiscale_id(int(fiscale_id))
    ErrorManager.require(
        sr_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="Soggetto-ruolo emittente non risolvibile.",
        function_name=f"{_FN}._resolve_emittente_sr_id",
    )
    assert sr_id is not None
    return int(sr_id)


# Scopo: risolve il trattamento IVA di una riga ordine dal contesto della
#        testata, e ritorna `(iva_id, meta_patch)`.
# ⭐ Wrapper sottile sul BB `IvaResolverService.applica_riga_documento`: la
#    regola e' una sola per i tre domini, qui c'e' solo il passaggio dei campi
#    di testata.
# ⛔ `emittente_fiscale_id` e' la PK, NON il `soggetto_ruolo_id` del pricing.
# ⭐ Costruito da una FACTORY e non scritto qui: i tre domini avevano tre copie
#    identiche a meno del codice errore. Stesso stampo di
#    `make_db_errors_translator` — i parametri di dominio si fissano una volta,
#    la regola resta in un posto solo.
_risolvi_iva_riga = make_risolvi_iva_riga(
    error_code="E_ORD_VALIDAZIONE",
    function_name=f"{_FN}._risolvi_iva_riga",
)



def _data_riferimento(testata: dict[str, Any]) -> date:
    raw = testata.get("data")
    if isinstance(raw, date):
        return raw
    ErrorManager.require(
        raw is not None,
        code="E_ORD_VALIDAZIONE",
        message="Ordine senza data: impossibile risolvere prezzi/componenti.",
        function_name=f"{_FN}._data_riferimento",
    )
    return date.fromisoformat(str(raw))


# Scopo: Converte IN LOCO le date di consegna presenti in `data` (gia'
#        normalizzato con `empty_to_none`): stringa ISO -> `date`, `None`
#        invariato (assente o azzeramento). Malformata -> 400 col campo.
def _parse_date_riga(data: dict[str, Any], *, function_name: str) -> None:
    for chiave in _DATE_RIGA:
        if chiave in data:
            data[chiave] = _V.optional_date(
                data, chiave, function_name=function_name,
            )


# Scopo: Risolve il prezzo unitario riga via PricingService (BB condiviso,
#        mai query dirette su listini — memoria feedback_pricing_centralizzato).
def _resolve_prezzo_riga(
    repo: OrdiniRepository, testata: dict[str, Any], *,
    articolo_id: str, uom_id: int | None,
) -> str:
    from decimal import Decimal

    from apps.vendite.services.pricing_service import PricingService

    fn = f"{_FN}._resolve_prezzo_riga"
    ErrorManager.require(
        testata.get("billing_account_id") is not None,
        code="E_ORD_VALIDAZIONE",
        message="Ordine senza billing_account: impossibile risolvere il prezzo.",
        function_name=fn,
    )
    ErrorManager.require(
        testata.get("utility_id") is not None,
        code="E_ORD_VALIDAZIONE",
        message="Ordine senza utility: impossibile risolvere il prezzo.",
        function_name=fn,
    )
    ErrorManager.require(
        uom_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="uom_operativa_id obbligatorio per risolvere il prezzo.",
        function_name=fn,
    )
    emittente_sr_id = _resolve_emittente_sr_id(repo, testata)
    assert uom_id is not None
    result = PricingService().resolve_prezzo(
        articolo_id=articolo_id,
        uom_id=int(uom_id),
        data_riferimento=_data_riferimento(testata),
        ba_id=int(testata["billing_account_id"]),
        utility_id=int(testata["utility_id"]),
        emittente_soggetto_ruolo_id=emittente_sr_id,
    )
    prezzo = result.get("prezzo_finale")
    if isinstance(prezzo, Decimal):
        return str(prezzo)
    return str(prezzo) if prezzo is not None else "0"
