# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per resi di vendita (CRUD, conferma/annullo,
#        generazione DDT di ri-consegna, code da-accreditare/da-riconsegnare).
# ------------------------------------------------------------

# Orchestrazione resi di vendita: validazione, guard su stato, delega al
# repository e alle funzioni madri DB (`fn_conferma_reso`, `fn_annulla_reso`,
# `fn_genera_ddt_riconsegna`, `fn_accredita_riga_reso`). Clone strutturale ridotto di `ddt_service`
# (modulo di funzioni libere): niente prezzi/componenti/push/PDF/note.
#
# Punti di modello (brief brief-be-fe-resi-vendita.md):
# - Il reso nasce SOLO da un DDT in CONSEGNATO (sorgente data-driven
#   DDT_VENDITA risolta per codice): guard applicativo parlante qui +
#   guard DB `trgfn_resi_guard_ddt_consegnato` (a10 INSERT,
#   E_RESO_DDT_NON_CONSEGNATO — chiuso dal team DB il 2026-07-13).
# - Le righe sono SNAPSHOT delle righe del DDT sorgente (articolo/descrizione/
#   UoM/factor/ordine_riga_id copiati qui: nessun trigger di copia a DB); il
#   chiamante passa solo ddt_riga_id + tipo_reso_id + quantita' + motivo.
# - NIENTE cambia_stato generico: conferma e annullo hanno entrambi effetti
#   (riapertura/storno residuo, proiezione stato ordine, flip DDT) -> sempre
#   le fn madri DB, mai UPDATE nudo dello stato.
# - Righe editabili solo con testata DRAFT: lo decide il DB
#   (`trg_resi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt`, dal
#   `20260929-01`, 3-bis D-3b-h), con `E_RIGA_DOC_NON_BOZZA`; il pre-check del
#   BB `richiedi_righe_in_bozza` risponde con lo stesso codice (parita' DDT).

import logging
from dataclasses import dataclass, field
from datetime import date
from collections.abc import Callable
from typing import Any

from django.db import transaction

from apps.config.db.sorgenti_repository import SorgentiRepository
from apps.config.sorgenti import SORGENTE_DDT_VENDITA, SORGENTE_RESO_VENDITA
from apps.core.db._helpers import richiedi_codice_a_vocabolario
from apps.core.api.constants import MAX_LIMIT
from apps.core.services.error_manager import ErrorManager
from apps.vendite.services._cliente_dal_ba import FK_CLIENTE_DIVERSO_DA_BA
from apps.vendite.services._righe_bozza_guard import Verbo, richiedi_righe_in_bozza
from apps.core.services.fan_out import FanOutRunLogger, run_fan_out
from apps.core.services.list_helpers import validate_enum_param
from apps.core.services.payload_helpers import (
    PayloadValidator,
    make_db_errors_translator,
)
from apps.core.services.testata_guard import (
    pagina_dopo_testata,
    riga_del_padre_o_not_found,
    testata_o_not_found,
)
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.db.resi_repository import ResiRepository

logger = logging.getLogger(__name__)

# Validator condiviso per gli id del payload (BB core: rigore tipi, stringhe
# numeriche ammesse solo per id, errore parlante E_RESO_VALIDAZIONE).
_PAYLOAD = PayloadValidator(validation_code="E_RESO_VALIDAZIONE")

# Codici errore vendite (registrati in error_policies.py) usati come fallback
# nella traduzione errori DB (BB translate_db_errors: i codici E_RESO_* /
# E_STATO_RESO_* dei guard DB sono estratti dal testo del RAISE).
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"

# Mappe vincolo DB -> (codice, messaggio) per map_integrity_error (frammento
# nome vincolo). `vendite.resi`/`resi_righe` non hanno UNIQUE di dominio
# scrivibili dal BE (uq_resi_anno_numero e' del trigger numerazione) -> solo FK.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    # Lo stesso prelievo d'origine nella stessa ubicazione due volte sotto la
    # stessa riga: si aumenta la quantita' del rientro che c'e' (3-bis D-3b-b).
    "uq_resi_righe_rientri_posizione": (
        E_VENDITE_DUPLICATO,
        "Questa riga ha gia' un rientro da questo prelievo in questa posizione: aumentane la quantita'.",
    ),
}
_FK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "fk_resi_billing_account": (E_VENDITE_FK, "Cliente (billing account) non valido."),
    # Rete sotto l'eredita' dal DDT (`trgfn_resi_normalize` e il guard D-6
    # `trgfn_resi_guard_cliente_ddt`, che rispondono prima col loro codice).
    "fk_resi_ba_cliente": FK_CLIENTE_DIVERSO_DA_BA,
    "fk_resi_destinatario_ruolo": (E_VENDITE_FK, "Destinatario non valido."),
    "fk_resi_emittente_fiscale": (E_VENDITE_FK, "Emittente fiscale non valido."),
    "fk_resi_sorgente_tipo": (E_VENDITE_FK, "Sorgente reso non valida."),
    "fk_resi_stato": (E_VENDITE_FK, "Stato reso non valido."),
    "fk_resi_righe_articolo": (E_VENDITE_FK, "Articolo non valido."),
    "fk_resi_righe_ddt_riga": (E_VENDITE_FK, "Riga DDT sorgente non valida."),
    "fk_resi_righe_ordine_riga": (E_VENDITE_FK, "Riga ordine non valida."),
    "fk_resi_righe_testata": (E_VENDITE_FK, "Reso non valido."),
    "fk_resi_righe_tipo_reso": (E_VENDITE_FK, "Tipo reso non valido."),
    "fk_resi_righe_uom_operativa": (E_VENDITE_FK, "Unita' di misura non valida."),
}
# «BA e utility tutti e due o nessuno»: le eredita entrambe dal DDT.
_CHECK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "chk_resi_ba_utility_insieme": (
        E_VENDITE_VALIDATION,
        "La utility del reso e' quella del suo billing account: senza billing account non c'e'.",
        "billing_account_id",
    ),
    "chk_resi_righe_rientri_qta_positiva": (
        E_VENDITE_VALIDATION, "La quantita' che rientra deve essere maggiore di zero.", "qta",
    ),
    "chk_resi_righe_rientri_qta_finito": (
        E_VENDITE_VALIDATION, "La quantita' che rientra non e' un numero valido.", "qta",
    ),
}

# ── Costanti di dominio ──
_FN = "vendite.resi_service"
_STATO_BOZZA = "DRAFT"
# Il reso si ELIMINA solo in bozza (abbandono del drawer, `elimina_reso`). I
# campi della testata li governa il lock di testata del DB
# (`trg_resi_a05_lock_fuori_bozza_upd`: in bozza tutto, dopo la conferma le
# sole note); le RIGHE il lock delle righe (`E_RIGA_DOC_NON_BOZZA`, dal
# `20260929-01`), con lo stesso codice del pre-check `richiedi_righe_in_bozza`.
_STATI_MODIFICABILI: frozenset[str] = frozenset({_STATO_BOZZA})
# Stato richiesto al DDT sorgente per aprire un reso (non si rende cio' che
# non e' stato consegnato — brief DB §3).
_STATO_DDT_SORGENTE = "CONSEGNATO"

# Tetto della selezione massiva di accrediti. Non e' una regola fiscale: e' il
# confine oltre il quale «ho scelto queste righe» non vuol piu' dire niente, e
# un cap esplicito e' meglio di un illimitato silenzioso — ogni riga apre una
# transazione e produce righe di rettifica. Stesso criterio (e stesso valore)
# di `MAX_GRUPPI_EMISSIONE_MIRATA` per l'emissione mirata.
MAX_ACCREDITI_MASSIVI = 200


# Scopo: Carica la testata reso o solleva E_RESO_NOT_FOUND (BB core
#        `testata_o_not_found`, stesso nome del helper di ordini e DDT).
# `getter` ammette il lettore leggero `get_stato_codice`, dove al chiamante
# basta sapere che il documento esiste (stessa forma di
# `offerte_service._get_offerta_or_raise`).
def _get_testata_or_raise(
    repo: ResiRepository, reso_id: int, *, op: str,
    getter: Callable[[int], Any] | None = None,
) -> Any:
    return testata_o_not_found(
        getter or repo.get_reso, reso_id,
        code="E_RESO_NOT_FOUND", message="Reso non trovato.",
        id_name="reso_id", function_name=f"{_FN}.{op}",
    )


# Scopo: Carica la riga o solleva E_RESO_NOT_FOUND se non esiste o non e' di questo
#        documento (BB core `riga_del_padre_o_not_found`: qui solo codice e
#        messaggio del dominio).
def _get_riga_or_raise(
    repo: ResiRepository, reso_id: int, riga_id: int, *, op: str,
) -> dict[str, Any]:
    return riga_del_padre_o_not_found(
        repo.get_riga, riga_id, padre_id=reso_id, chiave_padre="reso_id",
        code="E_RESO_NOT_FOUND", message="Riga non trovata per questo reso.",
        function_name=f"{_FN}.{op}",
    )

# Whitelist campi testata accettati in create/update (null_vs_empty -> None).
# Il resto (BA/destinatario/utility/valuta/emittente) e' EREDITATO dal DDT
# sorgente via trgfn_resi_normalize e immutabile (non_editable_fields).
# `magazzino_id`: dove rientra la merce (3-bis D-3b-a). Senza, lo propone il DB
# dalla bolla d'origine (`trgfn_resi_default_magazzino`); stesso emittente e
# fermo fuori bozza sono guard DB.
CREATE_KEYS_RESO: frozenset[str] = frozenset({"ddt_id", "data", "meta", "righe", "magazzino_id"})
UPDATE_KEYS_RESO: frozenset[str] = frozenset({"data", "meta", "magazzino_id"})
# NB: `quantita` (base) NON e' accettata nel payload riga: il trigger DB
# `trgfn_qta_from_operativa` su INSERT la calcola SEMPRE da qta_operativa
# (E_QTA_MISSING se assente) e su UPDATE un set diretto della base senza
# input operativi creerebbe un'incoerenza silente base<->operativa.
CREATE_KEYS_RIGA: frozenset[str] = frozenset({
    "ddt_riga_id", "tipo_reso_id", "qta_operativa", "motivo", "meta",
})
UPDATE_KEYS_RIGA: frozenset[str] = frozenset({
    "tipo_reso_id", "qta_operativa", "motivo", "meta",
})


# ══════════════════════════════════════════════════════════
#  LETTURE — Lista + code
# ══════════════════════════════════════════════════════════

# Scopo: Letture grezze (righe + totale) della lista resi. Condivisa tra lista
#        paginata (envelope) ed export futuro — regola del 2.
def list_resi_rows(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
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
        "config.stati_doc_reso", "codice_interno", stato_codice,
        codice_errore="E_RESO_VALIDAZIONE", parametro="stato_codice_interno",
    )
    repo = ResiRepository()
    return repo.list_resi(
        stato_codice=stato_codice,
        billing_account_id=billing_account_id,
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
#        export della lista resi (DEF-1). La lista ha lo stato (a differenza
#        delle code), niente utility. Gemello ddt_service.resolve_filtri_export_label.
def resolve_filtri_export_label(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if stato_codice:
        out["Stato"] = stato_codice
    if billing_account_id is not None:
        out["Cliente BA (id)"] = billing_account_id
    if data_da is not None:
        out["Dal"] = str(data_da)
    if data_al is not None:
        out["Al"] = str(data_al)
    return out


# Scopo: Dettaglio testata reso + capability data-driven (righe a parte via
#        /righe/). Mirror get_ddt.
def get_reso(reso_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    testata = _get_testata_or_raise(repo, reso_id, op="get_reso")
    # Capability da script.fn_available_actions_reso (matrice
    # config.transizioni_stati_reso): available_actions (conferma/annulla),
    # can_change_state, can_edit_testata/righe, non_editable_fields,
    # stato_codice. Mirror ridotto DDT (no push, no pdf). Il blob viaggia
    # SOTTO `capabilities` (api.md §«Il blob sta SOTTO `capabilities`»).
    capabilities = repo.get_capabilities(reso_id)
    return {
        **testata,
        "capabilities": capabilities,
        "righe_count": repo.count_righe(reso_id),
    }


# Scopo: Lista righe di un reso (con copertura ri-consegna derivata). Legge
#        prima la testata: un reso fuori perimetro (o inesistente) e' un 404,
#        non un pannello vuoto.
def list_righe(reso_id: int) -> list[dict[str, Any]]:
    repo = ResiRepository()
    _get_testata_or_raise(repo, reso_id, op="list_righe")
    return repo.list_righe(reso_id)


# Scopo: Una PAGINA delle righe del reso, per la lista configurabile
#        (`GET …/righe/lista/`): ricerca, ordinamento e pagina dal BB del
#        repository, dopo la testata (BB core `pagina_dopo_testata`).
#        Ritorna `(righe, totale)`.
def list_righe_pagina(reso_id: int, **opzioni: Any) -> tuple[list[dict[str, Any]], int]:
    repo = ResiRepository()
    return pagina_dopo_testata(
        lambda: _get_testata_or_raise(repo, reso_id, op="list_righe_pagina"),
        repo.list_righe_pagina, reso_id, **opzioni,
    )


# Scopo: Righe del DDT sorgente con gia'-reso/residuo rendibile (pannello FE
#        "crea reso da DDT" nel drawer DDT). Solo lettura: il guard over-return
#        resta il trigger DB a20 (E_RESO_QTA_SUPERA_CONSEGNATO).
def list_righe_ddt_per_reso(ddt_id: int) -> list[dict[str, Any]]:
    repo = ResiRepository()
    testata_o_not_found(
        repo.get_ddt_sorgente, ddt_id,
        code="E_DDT_NOT_FOUND", message="DDT non trovato.",
        id_name="ddt_id", function_name=f"{_FN}.list_righe_ddt_per_reso",
    )
    return repo.list_righe_ddt_per_reso(ddt_id)


# Scopo: Coda "da accreditare" (forma contatore: righe reso CONFERMATE con
#        accredito dovuto = fatturati - tenuti > 0, qualunque tipo; vista
#        vw_resi_da_accreditare). Predisposizione slice nota di credito.
# Scopo: I due id documento sono ALTERNATIVI, non componibili: una riga di coda
#        appartiene a un DDT e, tramite il fulfillment, a un ordine — chiedere
#        entrambi vorrebbe dire due domande in una, e la seconda restringerebbe
#        la prima in silenzio. Meglio un errore parlante che un elenco corto di
#        cui nessuno sa perche' e' corto.
def _valida_filtro_documento(
    *, ddt_id: int | None, ordine_id: int | None, function_name: str
) -> None:
    ErrorManager.require(
        ddt_id is None or ordine_id is None,
        code="E_RESO_VALIDAZIONE",
        message="Filtri documento incompatibili.",
        detail="ddt_id e ordine_id sono alternativi: indicarne uno solo",
        context={"parametro": "ordine_id"},
        function_name=function_name,
        log_to_db=True,
    )
    # 🔴 Guard sui valori, e non e' pedanteria: `?ddt_id=0` passa il parsing
    #    strict (0 e' un intero valido) e produce `WHERE v.ddt_id = 0`, cioe' una
    #    coda VUOTA. E una coda vuota si legge «non c'e' niente da fare», che e'
    #    il messaggio piu' sbagliato possibile su un elenco di accrediti dovuti.
    #    Disciplina AGENTS.md per gli ID: NULL o <= 0 -> errore parlante, mai
    #    normalizzazione silenziosa.
    for nome, valore in (("ddt_id", ddt_id), ("ordine_id", ordine_id)):
        ErrorManager.require(
            valore is None or valore > 0,
            code="E_RESO_VALIDAZIONE",
            message="Identificativo documento non valido.",
            detail=f"{nome} deve essere maggiore di zero (ricevuto: {valore})",
            context={"parametro": nome},
            function_name=function_name,
            log_to_db=True,
        )


def list_da_accreditare(
    *,
    billing_account_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    search: str | None = None,
    etichetta: str | None = None,
    ddt_id: int | None = None,
    ordine_id: int | None = None,
    auth_user_id: int | None = None,
    limit: int,
    offset: int,
    order_by: str = "data",
    order_dir: str = "desc",
    max_limit: int = MAX_LIMIT,
) -> tuple[list[Any], int]:
    _valida_filtro_documento(
        ddt_id=ddt_id,
        ordine_id=ordine_id,
        function_name="vendite.resi_service.list_da_accreditare",
    )
    # Filtro etichetta strict (DOVUTA = NC obbligatoria, a credito;
    # FACOLTATIVA = opzione dell'operatore su merce da ri-spedire, DL-26):
    # whitelist fail-fast, un valore ignoto e' un errore del chiamante,
    # non una lista vuota silenziosa.
    validate_enum_param(
        etichetta,
        allowed=("DOVUTA", "FACOLTATIVA"),
        param_name="etichetta",
        error_code="E_RESO_VALIDAZIONE",
        function_name="vendite.resi_service.list_da_accreditare",
        nullable=True,
    )
    return ResiRepository().list_da_accreditare(
        billing_account_id=billing_account_id,
        data_da=data_da,
        data_al=data_al,
        search=search,
        etichetta=etichetta,
        ddt_id=ddt_id,
        ordine_id=ordine_id,
        auth_user_id=auth_user_id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
        max_limit=max_limit,
    )


# Scopo: Coda "da ri-consegnare" (righe reso CONFERMATE per ri-consegna con
#        copertura incompleta, vista vw_resi_da_riconsegnare).
def list_da_riconsegnare(
    *,
    billing_account_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    search: str | None = None,
    ddt_id: int | None = None,
    ordine_id: int | None = None,
    auth_user_id: int | None = None,
    limit: int,
    offset: int,
    order_by: str = "data",
    order_dir: str = "desc",
    max_limit: int = MAX_LIMIT,
) -> tuple[list[Any], int]:
    _valida_filtro_documento(
        ddt_id=ddt_id,
        ordine_id=ordine_id,
        function_name="vendite.resi_service.list_da_riconsegnare",
    )
    return ResiRepository().list_da_riconsegnare(
        billing_account_id=billing_account_id,
        data_da=data_da,
        data_al=data_al,
        search=search,
        ddt_id=ddt_id,
        ordine_id=ordine_id,
        auth_user_id=auth_user_id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
        max_limit=max_limit,
    )


# Scopo: Etichette leggibili dei filtri applicati per il metadato del file
#        export delle code (DEF-1). Variante ridotta di
#        ddt_service.resolve_filtri_export_label: le code non hanno stato
#        (auto-limitate a CONFERMATO dalla vista) ne' utility.
def resolve_filtri_coda_export_label(
    *,
    billing_account_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    etichetta: str | None = None,
    ddt_id: int | None = None,
    ordine_id: int | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if billing_account_id is not None:
        out["Cliente BA (id)"] = billing_account_id
    if data_da is not None:
        out["Dal"] = str(data_da)
    if data_al is not None:
        out["Al"] = str(data_al)
    if etichetta is not None:
        # Senza questa riga l'export filtrato DOVUTA/FACOLTATIVA verrebbe
        # letto come coda completa (il file non dichiarerebbe il filtro).
        out["Etichetta NC"] = etichetta
    # Stessa ragione dell'etichetta: un export lanciato dalla coda filtrata su
    # un documento contiene le sole righe di quel documento, e senza questa
    # riga il file si leggerebbe come la coda intera.
    if ddt_id is not None:
        out["DDT (id)"] = ddt_id
    if ordine_id is not None:
        out["Ordine (id)"] = ordine_id
    return out


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Testata
# ══════════════════════════════════════════════════════════

# Scopo: Crea un nuovo reso da DDT in stato DRAFT. Payload minimo:
#        {ddt_id, data?, meta?, righe?}. La sorgente e' risolta per codice
#        (DDT_VENDITA) e il DDT deve essere in CONSEGNATO (guard applicativo:
#        non si rende cio' che non e' stato consegnato). BA/destinatario/
#        utility/valuta/emittente li eredita il trigger normalize dal DDT.
#        Se `righe` presenti (pannello FE): testata + N righe in UNA
#        transazione (compone 2+ scritture — guardrail atomicita' api.md).
def crea_reso(payload: dict[str, Any]) -> dict[str, Any]:
    repo = ResiRepository()
    # Il contratto: una chiave fuori whitelist e' un 400, mai uno scarto muto.
    data = _PAYLOAD.solo_chiavi_ammesse(payload, ammesse=CREATE_KEYS_RESO, function_name=f"{_FN}.crea_reso")

    ddt_id = _PAYLOAD.require_positive_int(
        data, "ddt_id",
        message="ddt_id obbligatorio: il reso nasce da un DDT consegnato.",
        function_name=f"{_FN}.crea_reso",
    )

    ddt = testata_o_not_found(
        repo.get_ddt_sorgente, ddt_id,
        code="E_DDT_NOT_FOUND", message="DDT sorgente non trovato.",
        id_name="ddt_id", function_name=f"{_FN}.crea_reso",
    )
    # Guard gemello del trigger DB `trgfn_resi_guard_ddt_consegnato`: STESSO
    # codice del trigger (E_RESO_DDT_NON_CONSEGNATO, 409) cosi' il FE vede un
    # solo errore per questo caso a prescindere dal percorso (service o
    # race col trigger); qui il messaggio arriva prima dell'INSERT.
    ErrorManager.require(
        ddt["stato_codice_interno"] == _STATO_DDT_SORGENTE,
        code="E_RESO_DDT_NON_CONSEGNATO",
        message=(
            "Il reso e' ammesso solo su DDT in stato CONSEGNATO: non si rende "
            "cio' che non e' stato consegnato."
        ),
        detail=f"ddt_id={ddt_id} stato={ddt['stato_codice_interno']}",
        function_name=f"{_FN}.crea_reso",
    )

    sorgente = SorgentiRepository().get_sorgente_attiva(SORGENTE_DDT_VENDITA)
    ErrorManager.require(
        sorgente is not None,
        code="E_RESO_VALIDAZIONE",
        message="Sorgente DDT_VENDITA non configurata in config.sorgenti.",
        function_name=f"{_FN}.crea_reso",
    )
    assert sorgente is not None
    sorgente_tipo_id = sorgente["id"]

    stato_bozza_id = repo.get_stato_id_by_codice(_STATO_BOZZA)
    ErrorManager.require(
        stato_bozza_id is not None,
        code="E_RESO_VALIDAZIONE",
        message="Stato DRAFT non configurato in config.stati_doc_reso.",
        function_name=f"{_FN}.crea_reso",
    )
    assert stato_bozza_id is not None

    righe = data.get("righe")
    ErrorManager.require(
        righe is None or isinstance(righe, list),
        code="E_RESO_VALIDAZIONE",
        message="righe deve essere una lista di righe reso.",
        function_name=f"{_FN}.crea_reso",
    )

    meta = data.get("meta")
    with _db_errors("crea_reso"), transaction.atomic():
        # transaction.atomic anche senza righe: costo nullo, e col pannello FE
        # (testata + N righe) l'unita' e' atomica per costruzione.
        creato = repo.create_reso(
            sorgente_tipo_id=int(sorgente_tipo_id),
            sorgente_uid=str(ddt["uid"]),
            stato_doc_reso_id=int(stato_bozza_id),
            data=_parse_data_iso(data.get("data"), op="crea_reso"),
            meta=meta if isinstance(meta, dict) else None,
            magazzino_id=data.get("magazzino_id"),
        )
        reso_id = int(creato["id"])
        righe_ids: list[int] = []
        for idx, riga_payload in enumerate(righe or []):
            ErrorManager.require(
                isinstance(riga_payload, dict),
                code="E_RESO_VALIDAZIONE",
                message="Ogni riga reso deve essere un oggetto.",
                function_name=f"{_FN}.crea_reso",
            )
            # Testata appena creata (0 righe): riga_nr deterministico idx+1,
            # nessun round-trip next_riga_nr per riga (era N+1).
            out = _crea_riga(
                repo, reso_id, ddt_id, dict(riga_payload), riga_nr=idx + 1,
            )
            righe_ids.append(out["riga_id"])

    return {**creato, "righe_ids": righe_ids}


# Scopo: Aggiorna testata reso (data, note, magazzino di rientro — il resto e'
#        ereditato dal DDT sorgente e immutabile).
#
# Quali colonne si cambiano in quale stato lo dice il DB, colonna per colonna:
# il lock di testata `vendite.trgfn_doc_testata_lock_fuori_bozza` (in bozza
# tutto; dopo la conferma le sole note, ferme a reso annullato). Fino al
# 2026-10-10 qui c'era un «solo in DRAFT» che ne era la seconda copia
# (brief-db-testata-dopo-emissione, D-0 e R-BE-2): il 409 del lock passa com'e'.
def aggiorna_reso(reso_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = ResiRepository()
    # Prima la testata: fuori perimetro o inesistente e' un 404. Basta sapere
    # che esiste: il lettore leggero, non la testata intera.
    _get_testata_or_raise(repo, reso_id, op="aggiorna_reso", getter=repo.get_stato_codice)
    # Il contratto: una chiave fuori whitelist e' un 400, mai uno scarto muto.
    data = _PAYLOAD.solo_chiavi_ammesse(payload, ammesse=UPDATE_KEYS_RESO, function_name=f"{_FN}.aggiorna_reso")
    _PAYLOAD.require_campi_da_aggiornare(
        data,
        function_name=f"{_FN}.aggiorna_reso",
    )
    if "data" in data:
        data["data"] = _parse_data_iso(data["data"], op="aggiorna_reso")
    with _db_errors("aggiorna_reso"):
        repo.update_reso(reso_id, **data)
    return {"reso_id": reso_id, "updated": True}


# Scopo: Hard-delete reso BOZZA ORFANO (0 righe attive) — supporto al pattern
#        "abbandono bozza" del drawer. Un reso con righe non si cancella: si
#        ANNULLA (fn_annulla_reso, che da DRAFT non ha effetti da stornare).
def elimina_reso(reso_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    _assert_stato(repo, reso_id, _STATI_MODIFICABILI, op="elimina_reso")
    righe_count = repo.count_righe(reso_id)
    ErrorManager.require(
        righe_count == 0,
        code="E_RESO_STATO_TRANSIZIONE",
        message=(
            "Impossibile eliminare un reso con righe: annullare il reso "
            "invece di cancellarlo."
        ),
        detail=f"righe_count={righe_count}",
        function_name=f"{_FN}.elimina_reso",
    )
    with _db_errors("elimina_reso"):
        deleted = repo.delete_reso(reso_id)
    return {"reso_id": reso_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  AZIONI DI DOMINIO — fn madri DB (atomiche per costruzione:
#  NIENTE transaction.atomic extra, una sola SELECT fn_madre)
# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
#  RIENTRI — dove rientra la merce (3-bis R-1b, piano-be-fe-magazzino-lotto-3
#  B2). ⛔ Nessuna regola ricopiata: bozza, prelievo della riga di bolla
#  giusta (trigger) e, alla conferma, quadratura, tetto per prelievo e
#  ubicazione (`script.fn_check_reso_merce`) li giudica il DB.
# ══════════════════════════════════════════════════════════

# Il prelievo d'origine si sceglie alla creazione e non cambia (il DB rifiuta
# un rientro che cambia prelievo).
CREATE_KEYS_RIENTRO: frozenset[str] = frozenset({"ddt_riga_prelievo_id", "qta", "ubicazione_id"})
UPDATE_KEYS_RIENTRO: frozenset[str] = frozenset({"qta", "ubicazione_id"})


# Scopo: I rientri del reso per la griglia: la testata (fa rientrare merce?,
#        magazzino di rientro e se usa ubicazioni) e le VOCI (la riga o il
#        componente del kit com'era uscito), ognuna coi prelievi d'origine fra
#        cui scegliere e i suoi rientri. Prima la testata: fuori perimetro e' 404.
def get_rientri(reso_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    testata = _get_testata_or_raise(
        repo, reso_id, op="get_rientri", getter=repo.get_testata_rientri,
    )
    origini: dict[tuple[int, int | None], list[dict[str, Any]]] = {}
    for prelievo in repo.list_prelievi_origine(reso_id):
        chiave = (prelievo["resi_riga_id"], prelievo["ddt_riga_componente_id"])
        origini.setdefault(chiave, []).append(prelievo)
    rientri: dict[tuple[int, int | None], list[dict[str, Any]]] = {}
    for rientro in repo.list_rientri(reso_id):
        chiave = (rientro["resi_riga_id"], rientro["ddt_riga_componente_id"])
        rientri.setdefault(chiave, []).append(rientro)
    voci = []
    for voce in repo.list_merce_da_rientrare(reso_id):
        chiave = (voce["resi_riga_id"], voce["ddt_riga_componente_id"])
        voci.append({
            **voce,
            "prelievi_origine": origini.get(chiave, []),
            "rientri": rientri.get(chiave, []),
        })
    return {**testata, "voci": voci}


# Scopo: Normalizza il payload di un rientro: chiavi del contratto, vuoti a
#        None, id interi positivi, `qta` decimale.
def _payload_rientro(
    payload: dict[str, Any], chiavi: frozenset[str], *, op: str, in_creazione: bool,
) -> dict[str, Any]:
    # Il contratto: una chiave fuori whitelist e' un 400, mai uno scarto muto.
    data = _PAYLOAD.solo_chiavi_ammesse(payload, ammesse=chiavi, function_name=f"{_FN}.{op}")
    fn = f"{_FN}.{op}"
    if in_creazione:
        data["ddt_riga_prelievo_id"] = _PAYLOAD.require_positive_int(data, "ddt_riga_prelievo_id", function_name=fn)
    if "ubicazione_id" in data:
        data["ubicazione_id"] = _PAYLOAD.optional_positive_int(data, "ubicazione_id", function_name=fn)
    if in_creazione or "qta" in data:
        data["qta"] = _PAYLOAD.require_decimal(data, "qta", function_name=fn)
    return data


# Scopo: Il rientro, se e' di questa riga; altrimenti E_RESO_NOT_FOUND.
def _get_rientro_or_raise(
    repo: ResiRepository, riga_id: int, rientro_id: int, *, op: str,
) -> dict[str, Any]:
    return riga_del_padre_o_not_found(
        repo.get_rientro, rientro_id, padre_id=riga_id, chiave_padre="resi_riga_id",
        code="E_RESO_NOT_FOUND", message="Rientro non trovato per questa riga.",
        function_name=f"{_FN}.{op}",
    )


# Scopo: Nuovo rientro sotto una riga del reso.
def crea_rientro(reso_id: int, riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = ResiRepository()
    _get_testata_or_raise(repo, reso_id, op="crea_rientro", getter=repo.get_stato_codice)
    _get_riga_or_raise(repo, reso_id, riga_id, op="crea_rientro")
    data = _payload_rientro(payload, CREATE_KEYS_RIENTRO, op="crea_rientro", in_creazione=True)
    with _db_errors("crea_rientro"):
        creato = repo.create_rientro({**data, "resi_riga_id": riga_id})
    return {"reso_id": reso_id, "riga_id": riga_id, "rientro_id": int(creato["id"])}


# Scopo: Cambia quantita' o ubicazione di un rientro.
def aggiorna_rientro(
    reso_id: int, riga_id: int, rientro_id: int, payload: dict[str, Any],
) -> dict[str, Any]:
    repo = ResiRepository()
    _get_testata_or_raise(repo, reso_id, op="aggiorna_rientro", getter=repo.get_stato_codice)
    _get_riga_or_raise(repo, reso_id, riga_id, op="aggiorna_rientro")
    _get_rientro_or_raise(repo, riga_id, rientro_id, op="aggiorna_rientro")
    data = _payload_rientro(payload, UPDATE_KEYS_RIENTRO, op="aggiorna_rientro", in_creazione=False)
    _PAYLOAD.require_campi_da_aggiornare(
        data,
        function_name=f"{_FN}.aggiorna_rientro",
    )
    with _db_errors("aggiorna_rientro"):
        repo.update_rientro(rientro_id, **data)
    return {"reso_id": reso_id, "riga_id": riga_id, "rientro_id": rientro_id, "updated": True}


# Scopo: Toglie un rientro.
def elimina_rientro(reso_id: int, riga_id: int, rientro_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    _get_testata_or_raise(repo, reso_id, op="elimina_rientro", getter=repo.get_stato_codice)
    _get_riga_or_raise(repo, reso_id, riga_id, op="elimina_rientro")
    _get_rientro_or_raise(repo, riga_id, rientro_id, op="elimina_rientro")
    with _db_errors("elimina_rientro"):
        deleted = repo.delete_rientro(rientro_id)
    return {"reso_id": reso_id, "riga_id": riga_id, "rientro_id": rientro_id, "deleted": deleted}


# Scopo: Conferma il reso (DRAFT -> CONFERMATO) via fn madre atomica
#        `fn_conferma_reso`: numero dal trigger, riapertura residuo ordine,
#        proiezione stato ordine, flip DDT->RESO se reso totale. Ritorno LIGHT
#        (parita' ddt_service.emetti): il FE ricarica il detail dopo. I guard
#        (esistenza E_RESO_NOT_FOUND, stato E_RESO_STATO_NON_CONFERMABILE,
#        righe E_RESO_SENZA_RIGHE) sono nella fn madre — nessun pre-check
#        duplicato; lo stato di ritorno e' RILETTO dal DB, non asserito
#        hardcoded (la transizione target vive nella matrice DB).
def conferma_reso(reso_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    with _db_errors("conferma_reso"):
        repo.conferma(reso_id)
    return {"reso_id": reso_id, "stato": repo.get_stato_codice(reso_id)}


# Scopo: Annulla il reso (da DRAFT o CONFERMATO) via fn madre atomica
#        `fn_annulla_reso`: post-conferma storna gli effetti; bloccato se gia'
#        ri-spedito (E_RESO_ANNULLO_CON_RICONSEGNE). Guard nella fn madre
#        (incl. E_RESO_NOT_FOUND); stato di ritorno riletto dal DB.
def annulla_reso(reso_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    with _db_errors("annulla_reso"):
        repo.annulla(reso_id)
    return {"reso_id": reso_id, "stato": repo.get_stato_codice(reso_id)}


# Scopo: Genera il DDT di ri-consegna via fn madre atomica
#        `fn_genera_ddt_riconsegna`: nuovo DDT DRAFT + ponte
#        resi_righe_riconsegne (+fulfillment se order-backed).
#        `righe` = [{resi_riga_id, qta}] in UNITA' BASE (a differenza
#        dell'evasione ordine->DDT che viaggia in operativa); None = tutta la
#        copertura residua. Il DDT nasce in DRAFT: numero None (nessun re-read).
def genera_ddt_riconsegna(
    reso_id: int,
    righe_raw: Any = None,
    data: date | None = None,
) -> dict[str, Any]:
    repo = ResiRepository()
    # `righe_raw` arriva grezza dal body: la validazione e' QUI (non nella
    # view) e rifiuta lista vuota / elementi malformati — un body degenere
    # NON deve degradare in silenzio a None = "ri-spedisci TUTTA la
    # copertura residua" (mirror _parse_righe_evasione di views_ordini).
    righe = _parse_righe_riconsegna(righe_raw)
    # Guard di merito (CONFERMATO, copertura pendente, over-ri-spedizione)
    # nella fn madre / guard ponte DB: E_RESO_NON_CONFERMATO,
    # E_RESO_NESSUNA_RICONSEGNA_PENDENTE, E_RESO_RICONSEGNA_SUPERA_RESO.
    # Il verbo e il default nella stessa transazione, come il DDT da ordine:
    # la cascata copia gli indirizzi del DDT d'origine, e il default riempie
    # lo slot SOLO se e' rimasto vuoto (la sorgente vince;
    # brief-db-indirizzi-documento-seguono-il-cliente).
    with _db_errors("genera_ddt_riconsegna"), transaction.atomic():
        ddt_id = repo.genera_ddt_riconsegna(int(reso_id), righe, data)
        DdtRepository().riempi_indirizzo_default(int(ddt_id))
    return {"reso_id": int(reso_id), "ddt_id": ddt_id, "numero": None}


# Scopo: Chiude la ri-consegna via fn madre atomica
#        `fn_chiudi_riconsegna_reso`: dichiara definitiva una quota di merce
#        resa PER RI-CONSEGNA (non tornera' al cliente). Scrive
#        `resi_righe_rinunce` e ri-proietta lo stato ordine: il residuo si
#        chiude → EVASO, chiudendo il buco "PARZIALMENTE_EVASO a vita".
#        `righe` = [{resi_riga_id, qta}] in UNITA' BASE (stesso contratto della
#        ri-spedizione — le due uscite condividono la copertura); None = tutta
#        la copertura residua. `note` = motivo facoltativo della chiusura.
#        NON muove numeri: l'accredito in coda resta identico, cambia solo
#        l'etichetta FACOLTATIVA → DOVUTA (brief §3).
def chiudi_riconsegna(
    reso_id: int,
    righe_raw: Any = None,
    note: Any = None,
) -> dict[str, Any]:
    repo = ResiRepository()
    # Stessa validazione della ri-spedizione: un body degenere NON deve
    # degradare in silenzio a None = "rendi definitiva TUTTA la copertura
    # residua" — qui l'effetto silenzioso sarebbe anche peggiore che sulla
    # gemella (si rinuncerebbe a merce che l'operatore voleva ri-spedire).
    righe = _parse_righe_riconsegna(righe_raw)
    note_norm = _parse_motivo_testo(note, op="chiudi_riconsegna")
    # Guard di merito (CONFERMATO, copertura pendente, over-rinuncia) nella fn
    # madre / guard ponte DB: E_RESO_NON_CONFERMATO,
    # E_RESO_NESSUNA_RICONSEGNA_PENDENTE, E_RESO_RINUNCIA_SUPERA_RESO.
    with _db_errors("chiudi_riconsegna"):
        righe_chiuse = repo.chiudi_riconsegna(int(reso_id), righe, note_norm)
    return {"reso_id": int(reso_id), "righe_chiuse": righe_chiuse}


# Scopo: Riapre una chiusura via fn madre atomica
#        `fn_riapri_riconsegna_reso`: cancella le rinunce e ri-proietta lo
#        stato ordine (torna PARZIALMENTE_EVASO). La quota torna ri-spedibile e
#        l'accredito torna FACOLTATIVA — round-trip chiudi→riapri = stato
#        iniziale. `righe` = [{resi_riga_id, qta}], None = tutte le rinunce del
#        reso; lo scalo parte dalle rinunce piu' RECENTI (LIFO, deciso a DB).
#        Il gate "non riaprire dopo l'emissione della NC" e' gia' cablato a DB
#        (script.fn_check_rinuncia_reversibile, dormiente finche' non esiste il
#        ramo NC): qui nessuna logica da replicare.
def riapri_riconsegna(reso_id: int, righe_raw: Any = None) -> dict[str, Any]:
    repo = ResiRepository()
    righe = _parse_righe_riconsegna(righe_raw)
    with _db_errors("riapri_riconsegna"):
        righe_riaperte = repo.riapri_riconsegna(int(reso_id), righe)
    return {"reso_id": int(reso_id), "righe_riaperte": righe_riaperte}


# Scopo: Accredita una riga di reso via fn madre atomica
#        `fn_accredita_riga_reso`: dalla coda accrediti genera le righe di
#        RETTIFICA in commessa (quantita' negativa, prezzo/sconto/IVA copiati
#        dalla riga di fattura rettificata) e le registra sul ponte
#        `resi_righe_accrediti`. Ritorna UNA riga per rettifica creata: su un
#        kit ne nasce una per componente, e se l'accredito dovuto consuma piu'
#        righe di fattura a prezzi diversi ne nascono altrettante.
#        ⭐ Il DOCUMENTO non nasce qui: la nota di credito nasce al giro di
#        fatturazione successivo. E' la ragione per cui l'esito PARZIALE del
#        fan-out (endpoint massivo) non lascia mai mezzo documento fiscale —
#        lascia righe non lavorate, che restano in coda.
# ⚠️ NESSUN guard applicativo: «e' in coda» (e quanto vale l'accredito),
#    «l'attivita' e' finita in una riga di fattura», «non e' gia' accreditata»,
#    «la copertura e' PIENA», «il kit dichiara il suo articolo padre» sono
#    TUTTI nella madre — E_ACCREDITO_NON_IN_CODA,
#    E_ACCREDITO_ATTIVITA_NON_FATTURATA, E_ACCREDITO_GIA_ESEGUITO,
#    E_ACCREDITO_QUOTA_NON_COPERTA, E_ACCREDITO_KIT_SENZA_PADRE. Ripeterli qui
#    sarebbe la stessa regola in due posti: le due copie divergono, e la piu'
#    vecchia non fa rumore.
# ⚠️ Nessun `transaction.atomic()`: una sola `SELECT fn_()` e' atomica per
#    costruzione (api.md §Atomicita' — qui non c'e' orchestrazione Python).
def accredita_riga_reso(resi_riga_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    # Anche il guard sul parametro (NULL / <= 0 -> E_PARAMETRO_INVALIDO) e'
    # nella madre: qui un pre-check risponderebbe con un codice diverso da
    # quello che il DB solleva per lo stesso fatto.
    with _db_errors("accredita_riga_reso"):
        accrediti = repo.accredita_riga_reso(int(resi_riga_id))
    return {"resi_riga_id": int(resi_riga_id), "accrediti": accrediti}


# Scopo: Diario del fan-out degli accrediti — l'unica parte di dominio del
#        giro. Serve a tenere il CODICE di ogni riga fallita: `FanOutEsito`
#        porta il messaggio normalizzato, non il codice, e il codice e' cio' su
#        cui il frontend instrada («gia' accreditata» si mostra diverso da «non
#        piu' in coda»). Il BB sa QUANDO chiamare, questo sa COSA tenere.
@dataclass
class _AccreditiRunLogger(FanOutRunLogger):
    esiti: dict[int, tuple[str, str]] = field(default_factory=dict)

    # Scopo: Registra codice e messaggio della riga che non e' passata.
    def item_failed(self, *, item: Any, indice: int, exc: Exception) -> None:
        codice = getattr(exc, "code", None) or E_VENDITE_VALIDATION
        messaggio = getattr(exc, "message", None) or str(exc)
        self.esiti[int(item)] = (codice, messaggio)


# Scopo: Accredita N righe di reso in un giro solo (D-NC-7: massivo dal primo
#        giorno). Un endpoint SOLO, e la riga singola e' una lista di uno: due
#        superfici per lo stesso verbo divergerebbero su permessi, conferme e
#        forma dell'esito.
#        Isolamento per riga con il BB `run_fan_out` (savepoint per elemento,
#        log dello stack una volta per tutte, esito a tre stati): MAI un ciclo
#        scritto a mano.
# ⭐ La risposta e' un REPORT, e torna sempre 200 — anche quando tutte le righe
#    falliscono. Il verbo non e' l'atto fiscale: il documento nasce dopo, nel
#    giro di fatturazione, quindi un esito parziale non lascia mai mezzo
#    documento — lascia righe che restano in coda. E sollevare sul «tutte
#    fallite» darebbe al chiamante DUE forme da leggere (una lista di esiti
#    oppure un errore) per la stessa domanda: e' lo stesso argomento per cui
#    l'endpoint e' uno solo. I codici per-riga stanno in `falliti`.
def accredita_righe_reso(resi_riga_ids_raw: Any) -> dict[str, Any]:
    ids = _parse_resi_riga_ids(resi_riga_ids_raw)
    diario = _AccreditiRunLogger()
    # `isola_in_transazione` resta al default: ogni riga scrive, e il savepoint
    # per elemento e' esattamente cio' che impedisce a una riga rifiutata di
    # portarsi via le rettifiche di quelle passate prima.
    esito = run_fan_out(ids, accredita_riga_reso, run_logger=diario)
    accrediti = [
        {"resi_riga_id": r["resi_riga_id"], **riga}
        for r in esito.risultati
        for riga in r["accrediti"]
    ]
    # Un solo lookup per riga, con UN default: due `.get` con default diversi
    # sullo stesso item possono raccontare due storie (codice di ripiego e
    # messaggio vero, o viceversa) proprio nel caso in cui il diario non ha
    # visto l'errore — cioe' quando serve capirlo.
    falliti = [
        _riga_fallita(int(e.item), diario.esiti, e.messaggio)
        for e in esito.errori
    ]
    return {
        "esito": esito.esito,
        "totale": esito.totale,
        "ok": esito.ok,
        "accrediti": accrediti,
        "falliti": falliti,
    }


# Scopo: Annulla l'accredito di una riga di reso via fn madre atomica
#        `fn_annulla_accredito_riga_reso` (D-NC-11): porta le rettifiche ad
#        ANNULLATA, cancella le righe di ponte — ed e' quella cancellazione a
#        far RISALIRE l'accredito dovuto in coda — e traccia il motivo.
#        E' il caso «ho cliccato la riga sbagliata», e sta A MONTE del
#        documento.
# ⛔ Non e' l'annullo del DOCUMENTO: quello e' gia' la pipeline, ed e' lo stesso
#    delle fatture. ⚠️ E il reset di lotto NON annulla l'accredito: la nota di
#    credito viene RIGENERATA al giro dopo, perche' la merce resa non e'
#    cambiata. Le due strade sono distinte e devono restare distinte — il
#    messaggio del DB lo dice all'operatore, e per questo non si riscrive qui.
# ⚠️ Nessun guard applicativo sulle precondizioni: «tutte le rettifiche ancora
#    NON_EMESSA», «nessuna in un lotto vivo», «motivo obbligatorio» sono nella
#    madre, che decide sull'INSIEME (C-2 del team DB) — un guard per riga qui
#    darebbe una risposta diversa dalla sua.
def annulla_accredito_riga_reso(
    reso_id: int, riga_id: int, motivo: Any,
) -> dict[str, Any]:
    repo = ResiRepository()
    # Appartenenza della riga al reso: NON e' una regola di dominio ripetuta
    # (la madre non conosce il reso), e' la coerenza del PERCORSO — senza,
    # `/resi/999/righe/24/annulla-accredito/` annullerebbe l'accredito della
    # riga 24 di un altro reso. Stesso guard di `aggiorna_riga`.
    _get_riga_or_raise(repo, int(reso_id), int(riga_id), op="annulla_accredito_riga_reso")
    # Stringa vuota / soli spazi -> NULL: normalizzazione dell'input, non un
    # guard. Il rifiuto lo fa la madre (E_ACCREDITO_MOTIVO_OBBLIGATORIO), che
    # e' anche l'unica a sapere perche' il motivo serve — l'annullo cancella le
    # righe di ponte, quindi la traccia del PERCHE' resta solo nel log.
    # ⚠️ Stesso parser della nota di rinuncia, non una copia: quello RIFIUTA i
    #    tipi non stringa invece di passarli al driver, ed e' la meta' che una
    #    normalizzazione scritta al volo dimentica sempre.
    motivo_norm = _parse_motivo_testo(motivo, op="annulla_accredito_riga_reso")
    with _db_errors("annulla_accredito_riga_reso"):
        rimosse = repo.annulla_accredito_riga_reso(int(riga_id), motivo_norm)
    return {
        "reso_id": int(reso_id),
        "resi_riga_id": int(riga_id),
        "rimosse": rimosse,
    }


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Righe (snapshot dalla riga DDT; solo testata DRAFT)
# ══════════════════════════════════════════════════════════

# Scopo: Aggiunge una riga al reso (solo DRAFT). Payload:
#        {ddt_riga_id, tipo_reso_id, qta_operativa|quantita, motivo?, meta?}.
#        Articolo/descrizione/UoM/factor/ordine_riga_id copiati dalla riga DDT
#        (snapshot: il reso non inventa articoli). L'over-return e' bloccato
#        dal guard DB a20 (lock FOR UPDATE) — qui nessuna duplicazione.
def gestisci_riga(reso_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = ResiRepository()
    # Lettura LEGGERA (stato + id DDT origine): la testata piena della vista
    # lista (decodifiche destinatario/BA/emittente) qui non serve — il reso
    # non ha pricing/componenti che la richiedano (diverso dal gemello DDT).
    reso = _richiedi_righe_in_bozza(repo, reso_id, verbo="aggiungere", op="gestisci_riga")
    ddt_id = reso.get("ddt_origine_id")
    ErrorManager.require(
        ddt_id is not None,
        code="E_RESO_VALIDAZIONE",
        message="Reso senza DDT di origine risolvibile (testata anomala).",
        function_name=f"{_FN}.gestisci_riga",
    )
    assert ddt_id is not None
    with _db_errors("gestisci_riga"):
        out = _crea_riga(repo, reso_id, int(ddt_id), payload)
    return out


# Scopo: Aggiorna una riga reso esistente (solo DRAFT; qta/tipo/motivo/meta —
#        lo snapshot articolo/UoM e' immutabile: cambiare articolo = altra
#        riga DDT = nuova riga reso).
def aggiorna_riga(
    reso_id: int, riga_id: int, payload: dict[str, Any],
) -> dict[str, Any]:
    repo = ResiRepository()
    _richiedi_righe_in_bozza(repo, reso_id, verbo="modificare", op="aggiorna_riga")
    _get_riga_or_raise(repo, reso_id, riga_id, op="aggiorna_riga")
    # Il contratto: una chiave fuori whitelist e' un 400, mai uno scarto muto.
    data = _PAYLOAD.solo_chiavi_ammesse(payload, ammesse=UPDATE_KEYS_RIGA, function_name=f"{_FN}.aggiorna_riga")
    _PAYLOAD.require_campi_da_aggiornare(
        data,
        message="Nessun campo aggiornabile nel payload riga.",
        function_name=f"{_FN}.aggiorna_riga",
    )
    with _db_errors("aggiorna_riga"):
        repo.update_riga(riga_id, **data)
    return {"reso_id": reso_id, "riga_id": riga_id, "updated": True}


# Scopo: Elimina riga reso (HARD DELETE, solo DRAFT). Il ponte ri-consegna
#        esiste solo post-conferma: nessun collegamento da verificare qui.
def elimina_riga(reso_id: int, riga_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    _richiedi_righe_in_bozza(repo, reso_id, verbo="togliere", op="elimina_riga")
    _get_riga_or_raise(repo, reso_id, riga_id, op="elimina_riga")
    with _db_errors("elimina_riga"):
        deleted = repo.delete_riga(riga_id)
    return {"reso_id": reso_id, "riga_id": riga_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  Helper privati
# ══════════════════════════════════════════════════════════

# Scopo: Crea una riga reso con snapshot dalla riga DDT (articolo/descrizione/
#        UoM/factor/ordine_riga_id). Guard: la riga DDT deve appartenere al DDT
#        sorgente del reso; tipo_reso_id e qta_operativa obbligatori (la base
#        la calcola il trigger DB qta_from_operativa). `riga_nr` esplicito dal
#        batch di crea_reso (testata nuova, numerazione deterministica);
#        None = lookup next_riga_nr (add singolo da gestisci_riga).
def _crea_riga(
    repo: ResiRepository, reso_id: int, ddt_id: int, payload: dict[str, Any],
    *, riga_nr: int | None = None,
) -> dict[str, Any]:
    # Il contratto: una chiave fuori whitelist e' un 400, mai uno scarto muto.
    data = _PAYLOAD.solo_chiavi_ammesse(payload, ammesse=CREATE_KEYS_RIGA, function_name=f"{_FN}._crea_riga")
    fn = f"{_FN}._crea_riga"

    ddt_riga_id = _PAYLOAD.require_positive_int(
        data, "ddt_riga_id",
        message="ddt_riga_id obbligatorio: la riga reso nasce da una riga DDT.",
        function_name=fn,
    )

    snapshot = repo.get_ddt_riga_snapshot(ddt_riga_id)
    ErrorManager.require(
        snapshot is not None and int(snapshot["ddt_id"]) == int(ddt_id),
        code="E_RESO_VALIDAZIONE",
        message="La riga DDT indicata non appartiene al DDT sorgente del reso.",
        detail=f"ddt_riga_id={ddt_riga_id} ddt_id={ddt_id}",
        function_name=fn,
    )
    assert snapshot is not None
    # Difesa sul modello 1:1 riga-DDT<->riga-ordine assunto da resi_righe
    # (colonna singola ordine_riga_id): il fulfillment ammette in teoria 1..n
    # righe ordine per riga DDT — se mai accadesse, attribuire il reso a UNA
    # sola riga ordine riaprirebbe il residuo solo in parte, SILENZIOSAMENTE.
    # Meglio un errore parlante (caso oggi non generabile dalle fn madri).
    ErrorManager.require(
        int(snapshot.get("fulfillment_count") or 0) <= 1,
        code="E_RESO_VALIDAZIONE",
        message=(
            "Riga DDT collegata a piu' righe ordine (fulfillment multipli): "
            "reso non attribuibile a una singola riga ordine."
        ),
        detail=f"ddt_riga_id={ddt_riga_id}",
        function_name=fn,
    )

    tipo_reso_id = _PAYLOAD.require_positive_int(
        data, "tipo_reso_id",
        message="tipo_reso_id obbligatorio (a credito / per ri-consegna).",
        function_name=fn,
    )

    qta_operativa = data.get("qta_operativa")
    # Obbligatoria l'OPERATIVA: il trigger DB (qta_from_operativa) su INSERT
    # calcola sempre la base da qta_operativa (E_QTA_MISSING se assente) —
    # accettare una `quantita` base sola sarebbe un contratto non onorabile.
    ErrorManager.require(
        qta_operativa is not None,
        code="E_RESO_VALIDAZIONE",
        message="qta_operativa obbligatoria (quantita' resa in unita' operativa).",
        function_name=fn,
    )
    assert qta_operativa is not None

    if riga_nr is None:
        riga_nr = repo.next_riga_nr(reso_id)
    created = repo.create_riga(
        reso_id=reso_id,
        riga_nr=riga_nr,
        ddt_riga_id=ddt_riga_id,
        # ordine_riga_id dal fulfillment della riga DDT (NULL per standalone):
        # alimenta l'addendo residuo reso-aware senza JOIN a catena.
        ordine_riga_id=snapshot.get("ordine_riga_id"),
        articolo_id=str(snapshot["articolo_id"]),
        descrizione=str(snapshot["descrizione"]),
        tipo_reso_id=tipo_reso_id,
        qta_operativa=qta_operativa,
        uom_operativa_id=snapshot.get("uom_operativa_id"),
        factor_to_base=(
            str(snapshot["factor_to_base"])
            if snapshot.get("factor_to_base") is not None else None
        ),
        motivo=data.get("motivo"),
        meta=data.get("meta") if isinstance(data.get("meta"), dict) else None,
    )
    return {"reso_id": reso_id, "riga_id": int(created["id"])}


# Scopo: Normalizza il campo `data` del payload a date: None passa, date
#        passa, stringa DEVE essere ISO (YYYY-MM-DD) — un formato ambiguo
#        (es. 13/07/2026) non deve arrivare al DB dove verrebbe respinto con
#        errore non parlante o, peggio, interpretato con DateStyle sbagliato.
def _parse_data_iso(value: Any, *, op: str) -> date | None:
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        ErrorManager.raise_error(
            code="E_RESO_VALIDAZIONE",
            message="Campo 'data' non valido: atteso formato ISO YYYY-MM-DD.",
            detail=f"data={value!r}",
            context={"op": f"{_FN}.{op}"},
        )


# Scopo: Valida il body `righe` della ri-spedizione parziale. Contratto:
#        assente/None = tutta la copertura residua (None alla fn DB); se
#        presente DEVE essere una lista non vuota di {resi_riga_id, qta} —
#        lista vuota o elementi malformati sono errore, NON degradano a
#        "ri-spedisci tutto" (mirror _parse_righe_evasione di views_ordini).
# Scopo: normalizza il motivo facoltativo della chiusura ri-consegna. Testo
#        libero: whitespace/vuoto -> NULL, mai stringa vuota a DB
#        ([[feedback_null_vs_empty]]). Un tipo non stringa e' un body malformato
#        e va rifiutato QUI con un 400 parlante: lasciarlo passare lo farebbe
#        arrivare come parametro varchar a psycopg (adattamento imprevedibile o
#        errore DB nudo al posto di un messaggio all'operatore).
def _parse_motivo_testo(valore: Any, *, op: str) -> str | None:
    ErrorManager.require(
        valore is None or isinstance(valore, str),
        code="E_RESO_VALIDAZIONE",
        message="Il motivo deve essere un testo.",
        detail=f"valore={valore!r}",
        function_name=f"{_FN}.{op}",
    )
    if valore is None:
        return None
    return empty_to_none(valore.strip())


def _parse_righe_riconsegna(righe_raw: Any) -> list[dict[str, Any]] | None:
    fn = f"{_FN}._parse_righe_riconsegna"
    if righe_raw is None:
        return None
    ErrorManager.require(
        isinstance(righe_raw, list) and len(righe_raw) > 0,
        code="E_RESO_VALIDAZIONE",
        message=(
            "righe deve essere una lista non vuota di {resi_riga_id, qta}; "
            "ometterla per ri-spedire tutta la copertura residua."
        ),
        detail=f"righe={righe_raw!r}",
        function_name=fn,
    )
    parsed: list[dict[str, Any]] = []
    for elem in righe_raw:
        ErrorManager.require(
            isinstance(elem, dict),
            code="E_RESO_VALIDAZIONE",
            message="Ogni elemento di righe deve essere un oggetto "
                    "{resi_riga_id, qta}.",
            detail=f"elem={elem!r}",
            function_name=fn,
        )
        resi_riga_id = _PAYLOAD.require_positive_int(
            elem, "resi_riga_id",
            message="resi_riga_id obbligatorio in ogni riga di ri-spedizione.",
            function_name=fn,
        )
        qta = elem.get("qta")
        ErrorManager.require(
            qta is not None,
            code="E_RESO_VALIDAZIONE",
            message="qta obbligatoria in ogni riga di ri-spedizione "
                    "(unita' BASE).",
            function_name=fn,
        )
        parsed.append({"resi_riga_id": resi_riga_id, "qta": qta})
    return parsed


# Scopo: La forma di una riga non servita nel report del fan-out. Il codice
#        viene dal diario (il BB porta il messaggio, non il codice); se il
#        diario non l'ha visto — non dovrebbe accadere, ma il ripiego non deve
#        mentire — si dichiara il fallback e si tiene il messaggio del BB.
def _riga_fallita(
    resi_riga_id: int, esiti: dict[int, tuple[str, str]], messaggio_bb: str,
) -> dict[str, Any]:
    codice, messaggio = esiti.get(resi_riga_id, (E_VENDITE_VALIDATION, messaggio_bb))
    return {
        "resi_riga_id": resi_riga_id,
        "codice": codice,
        "messaggio": messaggio,
    }


# Scopo: Normalizza e valida la lista di righe di reso da accreditare.
#        Obiettivo: un perimetro sbagliato deve fallire con un 400 parlante,
#        mai degenerare in un perimetro vuoto o in id spazzatura.
#        Deduplica PRESERVANDO L'ORDINE: lo stesso id due volte nello stesso
#        body produrrebbe un `E_ACCREDITO_GIA_ESEGUITO` autoinflitto, che a
#        video sembra un difetto del sistema e invece e' il body.
# ⚠️ Lista VUOTA rifiutata, non trattata come «tutte»: e' lo stesso criterio di
#    `parse_gruppi` per l'emissione mirata — indovinare male qui significa
#    lavorare un perimetro che nessuno ha chiesto, su un documento fiscale.
# ⚠️ `bool` e' un `int` in Python: `[True]` passerebbe come riga 1 senza questo
#    controllo di tipo esplicito.
def _parse_resi_riga_ids(raw: Any) -> tuple[int, ...]:
    fn = f"{_FN}._parse_resi_riga_ids"
    ErrorManager.require(
        isinstance(raw, (list, tuple)),
        code="E_RESO_VALIDAZIONE",
        message="`resi_riga_ids` deve essere una lista di id riga di reso.",
        detail=f"tipo ricevuto: {type(raw).__name__}",
        function_name=fn,
    )
    ids: list[int] = []
    for elemento in raw:
        valido = (
            isinstance(elemento, int) and not isinstance(elemento, bool)
            and elemento > 0
        ) or (isinstance(elemento, str) and elemento.strip().isdigit()
              and int(elemento) > 0)
        ErrorManager.require(
            valido,
            code="E_RESO_VALIDAZIONE",
            message="`resi_riga_ids` contiene un id non valido (atteso intero > 0).",
            detail=repr(elemento),
            function_name=fn,
        )
        valore = int(elemento)
        if valore not in ids:
            ids.append(valore)
    ErrorManager.require(
        len(ids) > 0,
        code="E_RESO_VALIDAZIONE",
        message="`resi_riga_ids` non puo' essere una lista vuota.",
        detail="selezionare almeno una riga di reso da accreditare",
        function_name=fn,
    )
    ErrorManager.require(
        len(ids) <= MAX_ACCREDITI_MASSIVI,
        code="E_RESO_VALIDAZIONE",
        message=f"Troppe righe selezionate (max {MAX_ACCREDITI_MASSIVI}).",
        detail=f"ricevute: {len(ids)}",
        function_name=fn,
    )
    return tuple(ids)


# Traduzione errori DB -> ServiceError parlanti via BB condiviso
# `make_db_errors_translator` (core payload_helpers): IntegrityError (fk) con
# le mappe vincolo del dominio; DatabaseError (RAISE P0001 di trigger/fn
# madri) con estrazione del codice E_RESO_* per il routing UI del FE.
_db_errors = make_db_errors_translator(
    fn_prefix=_FN,
    fallback_code=E_VENDITE_VALIDATION,
    fallback_message="Violazione vincolo DB su reso.",
    unique_constraints=_UNIQUE_CONSTRAINTS,
    fk_constraints=_FK_CONSTRAINTS,
    check_constraints=_CHECK_CONSTRAINTS,
)


# Scopo: «Le righe si toccano solo in bozza» sul reso, col codice del DB
#        (`E_RIGA_DOC_NON_BOZZA`, BB `richiedi_righe_in_bozza`): legge la
#        testata col lettore leggero (stato, numero, DDT di origine) — reso
#        inesistente -> E_RESO_NOT_FOUND — e la restituisce al chiamante, che
#        di quella lettura puo' aver bisogno (il DDT di origine in `gestisci_riga`).
def _richiedi_righe_in_bozza(
    repo: ResiRepository, reso_id: int, *, verbo: Verbo, op: str,
) -> dict[str, Any]:
    reso = testata_o_not_found(
        repo.get_stato_e_ddt_origine, reso_id,
        code="E_RESO_NOT_FOUND", message="Reso non trovato.",
        id_name="reso_id", function_name=f"{_FN}.{op}",
    )
    richiedi_righe_in_bozza(
        reso, documento=SORGENTE_RESO_VENDITA, documento_id=reso_id, verbo=verbo,
        function_name=f"{_FN}.{op}",
    )
    return reso


# Scopo: Guard di stato leggero (solo codice_interno): E_RESO_NOT_FOUND se il
#        reso non esiste, E_RESO_STATO_TRANSIZIONE se lo stato non e' ammesso.
def _assert_stato(
    repo: ResiRepository, reso_id: int, ammessi: frozenset[str], *, op: str,
    message: str | None = None,
) -> str:
    # Stesso BB del guard di testata, col getter leggero (solo codice_interno).
    stato = testata_o_not_found(
        repo.get_stato_codice, reso_id,
        code="E_RESO_NOT_FOUND", message="Reso non trovato.",
        id_name="reso_id", function_name=f"{_FN}.{op}",
    )
    ErrorManager.require(
        stato in ammessi,
        code="E_RESO_STATO_TRANSIZIONE",
        message=message or f"Operazione non ammessa nello stato {stato}.",
        detail=f"ammessi={sorted(ammessi)}",
        function_name=f"{_FN}.{op}",
    )
    return stato
