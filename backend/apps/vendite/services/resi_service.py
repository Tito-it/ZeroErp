# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per resi di vendita (CRUD, conferma/annullo,
#        generazione DDT di ri-consegna, code da-accreditare/da-riconsegnare).
# ------------------------------------------------------------

# Orchestrazione resi di vendita: validazione, guard su stato, delega al
# repository e alle funzioni madri DB (`fn_conferma_reso`, `fn_annulla_reso`,
# `fn_genera_ddt_riconsegna`). Clone strutturale ridotto di `ddt_service`
# (modulo di funzioni libere): niente prezzi/componenti/push/PDF/note.
#
# Punti di modello (brief brief-be-fe-resi-vendita.md):
# - Il reso nasce SOLO da un DDT in CONSEGNATO (sorgente data-driven
#   DDT_VENDITA risolta per codice): guard applicativo qui — il DB non ha un
#   guard di stato sorgente sull'INSERT (trgfn_resi_normalize eredita e basta).
# - Le righe sono SNAPSHOT delle righe del DDT sorgente (articolo/descrizione/
#   UoM/factor/ordine_riga_id copiati qui: nessun trigger di copia a DB); il
#   chiamante passa solo ddt_riga_id + tipo_reso_id + quantita' + motivo.
# - NIENTE cambia_stato generico: conferma e annullo hanno entrambi effetti
#   (riapertura/storno residuo, proiezione stato ordine, flip DDT) -> sempre
#   le fn madri DB, mai UPDATE nudo dello stato.
# - Righe editabili solo con testata DRAFT: enforcement BE (il DB non ha il
#   trigger di editabilita', item 14c del brief DB — parita' DDT).

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any

from django.db import DatabaseError, IntegrityError, transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import map_integrity_error
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.resi_repository import ResiRepository

logger = logging.getLogger(__name__)

# Codici errore vendite (registrati in error_policies.py) usati come fallback
# nella traduzione errori DB. I codici trigger/fn E_RESO_* / E_STATO_RESO_*
# sollevati dai guard DB sono estratti via regex dal MESSAGE del RAISE.
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_FK = "E_VENDITE_FK"
_DB_ERROR_CODE_RE = re.compile(r"\b(E_[A-Z][A-Z0-9_]+)\b")

# Mappe vincolo DB -> (codice, messaggio) per map_integrity_error (frammento
# nome vincolo). `vendite.resi`/`resi_righe` non hanno UNIQUE di dominio
# scrivibili dal BE (uq_resi_anno_numero e' del trigger numerazione) -> solo FK.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {}
_FK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "fk_resi_billing_account": (E_VENDITE_FK, "Cliente (billing account) non valido."),
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

# ── Costanti di dominio ──
_FN = "vendite.resi_service"
_STATO_BOZZA = "DRAFT"
_STATI_MODIFICABILI: frozenset[str] = frozenset({"DRAFT"})
_STATI_RIGHE_MODIFICABILI: frozenset[str] = frozenset({"DRAFT"})
# Stato richiesto al DDT sorgente per aprire un reso (non si rende cio' che
# non e' stato consegnato — brief DB §3).
_STATO_DDT_SORGENTE = "CONSEGNATO"
# Sorgente data-driven (config.sorgenti, riuso riga esistente — mai id
# hardcoded, memoria feedback_no_hardcoded_ids).
_SORGENTE_DDT = "DDT_VENDITA"

# Whitelist campi testata accettati in create/update (null_vs_empty -> None).
# Il resto (BA/destinatario/utility/valuta/emittente) e' EREDITATO dal DDT
# sorgente via trgfn_resi_normalize e immutabile (non_editable_fields).
_CREATE_KEYS_RESO: frozenset[str] = frozenset({"ddt_id", "data", "meta", "righe"})
_UPDATE_KEYS_RESO: frozenset[str] = frozenset({"data", "meta"})
_CREATE_KEYS_RIGA: frozenset[str] = frozenset({
    "ddt_riga_id", "tipo_reso_id", "quantita", "qta_operativa", "motivo", "meta",
})
_UPDATE_KEYS_RIGA: frozenset[str] = frozenset({
    "tipo_reso_id", "quantita", "qta_operativa", "motivo", "meta",
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
) -> tuple[list[Any], int]:
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
    )


# Scopo: Dettaglio testata reso + capability data-driven (righe a parte via
#        /righe/). Mirror get_ddt.
def get_reso(reso_id: int) -> dict[str, object]:
    repo = ResiRepository()
    testata = repo.get_reso(reso_id)
    ErrorManager.require(
        testata is not None,
        code="E_RESO_NOT_FOUND",
        message="Reso non trovato.",
        detail=f"reso_id={reso_id}",
        function_name=f"{_FN}.get_reso",
    )
    assert testata is not None
    # Capability da script.fn_available_actions_reso (matrice
    # config.transizioni_stati_reso): available_actions (conferma/annulla),
    # can_change_state, can_edit_testata/righe, non_editable_fields,
    # stato_codice. Mirror ridotto DDT (no push, no pdf).
    capabilities = repo.get_capabilities(reso_id)
    return {
        **testata,
        **capabilities,
        "righe_count": repo.count_righe(reso_id),
    }


# Scopo: Lista righe di un reso (con copertura ri-consegna derivata).
def list_righe(reso_id: int) -> list[dict[str, Any]]:
    return ResiRepository().list_righe(reso_id)


# Scopo: Righe del DDT sorgente con gia'-reso/residuo rendibile (pannello FE
#        "crea reso da DDT" nel drawer DDT). Solo lettura: il guard over-return
#        resta il trigger DB a20 (E_RESO_QTA_SUPERA_CONSEGNATO).
def list_righe_ddt_per_reso(ddt_id: int) -> list[dict[str, Any]]:
    repo = ResiRepository()
    ddt = repo.get_ddt_sorgente(ddt_id)
    ErrorManager.require(
        ddt is not None,
        code="E_DDT_NOT_FOUND",
        message="DDT non trovato.",
        detail=f"ddt_id={ddt_id}",
        function_name=f"{_FN}.list_righe_ddt_per_reso",
    )
    return repo.list_righe_ddt_per_reso(ddt_id)


# Scopo: Coda "da accreditare" (righe reso CONFERMATE a credito, vista
#        vw_resi_da_accreditare). Predisposizione slice nota di credito.
def list_da_accreditare(
    *,
    billing_account_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    auth_user_id: int | None = None,
    limit: int,
    offset: int,
) -> tuple[list[Any], int]:
    return ResiRepository().list_da_accreditare(
        billing_account_id=billing_account_id,
        data_da=data_da,
        data_al=data_al,
        auth_user_id=auth_user_id,
        limit=limit,
        offset=offset,
    )


# Scopo: Coda "da ri-consegnare" (righe reso CONFERMATE per ri-consegna con
#        copertura incompleta, vista vw_resi_da_riconsegnare).
def list_da_riconsegnare(
    *,
    billing_account_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    auth_user_id: int | None = None,
    limit: int,
    offset: int,
) -> tuple[list[Any], int]:
    return ResiRepository().list_da_riconsegnare(
        billing_account_id=billing_account_id,
        data_da=data_da,
        data_al=data_al,
        auth_user_id=auth_user_id,
        limit=limit,
        offset=offset,
    )


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
    data = {k: empty_to_none(v) for k, v in payload.items() if k in _CREATE_KEYS_RESO}

    raw_ddt_id = data.get("ddt_id")
    ErrorManager.require(
        raw_ddt_id is not None,
        code="E_RESO_VALIDAZIONE",
        message="ddt_id obbligatorio: il reso nasce da un DDT consegnato.",
        function_name=f"{_FN}.crea_reso",
    )
    assert raw_ddt_id is not None
    try:
        ddt_id = int(raw_ddt_id)
    except (TypeError, ValueError):
        ddt_id = 0
        ErrorManager.require(
            False,
            code="E_RESO_VALIDAZIONE",
            message="ddt_id non valido.",
            detail=f"ddt_id={raw_ddt_id!r}",
            function_name=f"{_FN}.crea_reso",
        )

    ddt = repo.get_ddt_sorgente(ddt_id)
    ErrorManager.require(
        ddt is not None,
        code="E_DDT_NOT_FOUND",
        message="DDT sorgente non trovato.",
        detail=f"ddt_id={ddt_id}",
        function_name=f"{_FN}.crea_reso",
    )
    assert ddt is not None
    ErrorManager.require(
        ddt["stato_codice_interno"] == _STATO_DDT_SORGENTE,
        code="E_RESO_VALIDAZIONE",
        message=(
            "Il reso e' ammesso solo su DDT in stato CONSEGNATO: non si rende "
            "cio' che non e' stato consegnato."
        ),
        detail=f"ddt_id={ddt_id} stato={ddt['stato_codice_interno']}",
        function_name=f"{_FN}.crea_reso",
    )

    sorgente_tipo_id = repo.get_sorgente_tipo_id_by_codice(_SORGENTE_DDT)
    ErrorManager.require(
        sorgente_tipo_id is not None,
        code="E_RESO_VALIDAZIONE",
        message="Sorgente DDT_VENDITA non configurata in config.sorgenti.",
        function_name=f"{_FN}.crea_reso",
    )
    assert sorgente_tipo_id is not None

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
            data=data.get("data"),
            meta=meta if isinstance(meta, dict) else None,
        )
        reso_id = int(creato["id"])
        righe_ids: list[int] = []
        for riga_payload in righe or []:
            ErrorManager.require(
                isinstance(riga_payload, dict),
                code="E_RESO_VALIDAZIONE",
                message="Ogni riga reso deve essere un oggetto.",
                function_name=f"{_FN}.crea_reso",
            )
            out = _crea_riga(repo, reso_id, ddt_id, dict(riga_payload))
            righe_ids.append(out["riga_id"])

    return {**creato, "righe_ids": righe_ids}


# Scopo: Aggiorna testata reso (solo DRAFT; soli campi data/meta — il resto e'
#        ereditato dal DDT sorgente e immutabile).
def aggiorna_reso(reso_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = ResiRepository()
    _assert_stato(repo, reso_id, _STATI_MODIFICABILI, op="aggiorna_reso")
    data = {k: empty_to_none(v) for k, v in payload.items() if k in _UPDATE_KEYS_RESO}
    ErrorManager.require(
        len(data) > 0,
        code="E_RESO_VALIDAZIONE",
        message="Nessun campo aggiornabile nel payload.",
        function_name=f"{_FN}.aggiorna_reso",
    )
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

# Scopo: Conferma il reso (DRAFT -> CONFERMATO) via fn madre atomica
#        `fn_conferma_reso`: numero dal trigger, riapertura residuo ordine,
#        proiezione stato ordine, flip DDT->RESO se reso totale. Ritorno LIGHT
#        (parita' ddt_service.emetti): il FE ricarica il detail dopo.
def conferma_reso(reso_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    stato_prec = repo.get_stato_codice(reso_id)
    ErrorManager.require(
        stato_prec is not None,
        code="E_RESO_NOT_FOUND",
        message="Reso non trovato.",
        detail=f"reso_id={reso_id}",
        function_name=f"{_FN}.conferma_reso",
    )
    # Guard di merito (DRAFT, righe presenti) nella fn madre DB: errori
    # E_RESO_STATO_NON_CONFERMABILE / E_RESO_SENZA_RIGHE via _db_errors.
    with _db_errors("conferma_reso"):
        repo.conferma(reso_id)
    return {"reso_id": reso_id, "stato_precedente": stato_prec,
            "stato": "CONFERMATO"}


# Scopo: Annulla il reso (da DRAFT o CONFERMATO) via fn madre atomica
#        `fn_annulla_reso`: post-conferma storna gli effetti; bloccato se gia'
#        ri-spedito (E_RESO_ANNULLO_CON_RICONSEGNE).
def annulla_reso(reso_id: int) -> dict[str, Any]:
    repo = ResiRepository()
    stato_prec = repo.get_stato_codice(reso_id)
    ErrorManager.require(
        stato_prec is not None,
        code="E_RESO_NOT_FOUND",
        message="Reso non trovato.",
        detail=f"reso_id={reso_id}",
        function_name=f"{_FN}.annulla_reso",
    )
    with _db_errors("annulla_reso"):
        repo.annulla(reso_id)
    return {"reso_id": reso_id, "stato_precedente": stato_prec,
            "stato": "ANNULLATO"}


# Scopo: Genera il DDT di ri-consegna via fn madre atomica
#        `fn_genera_ddt_riconsegna`: nuovo DDT DRAFT + ponte
#        resi_righe_riconsegne (+fulfillment se order-backed).
#        `righe` = [{resi_riga_id, qta}] in UNITA' BASE (a differenza
#        dell'evasione ordine->DDT che viaggia in operativa); None = tutta la
#        copertura residua. Il DDT nasce in DRAFT: numero None (nessun re-read).
def genera_ddt_riconsegna(
    reso_id: int,
    righe: list[dict[str, Any]] | None = None,
    data: date | None = None,
) -> dict[str, Any]:
    repo = ResiRepository()
    # Guard di merito (CONFERMATO, copertura pendente, over-ri-spedizione)
    # nella fn madre / guard ponte DB: E_RESO_NON_CONFERMATO,
    # E_RESO_NESSUNA_RICONSEGNA_PENDENTE, E_RESO_RICONSEGNA_SUPERA_RESO.
    with _db_errors("genera_ddt_riconsegna"):
        ddt_id = repo.genera_ddt_riconsegna(int(reso_id), righe, data)
    return {"reso_id": int(reso_id), "ddt_id": ddt_id, "numero": None}


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
    reso = repo.get_reso(reso_id)
    ErrorManager.require(
        reso is not None,
        code="E_RESO_NOT_FOUND",
        message="Reso non trovato.",
        detail=f"reso_id={reso_id}",
        function_name=f"{_FN}.gestisci_riga",
    )
    assert reso is not None
    ErrorManager.require(
        reso["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_RESO_STATO_TRANSIZIONE",
        message="Righe modificabili solo su reso in bozza.",
        detail=f"stato={reso['stato_codice_interno']}",
        function_name=f"{_FN}.gestisci_riga",
    )
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
    _assert_stato(
        repo, reso_id, _STATI_RIGHE_MODIFICABILI, op="aggiorna_riga",
        message="Righe modificabili solo su reso in bozza.",
    )
    riga = repo.get_riga(riga_id)
    ErrorManager.require(
        riga is not None and riga["reso_id"] == reso_id,
        code="E_RESO_NOT_FOUND",
        message="Riga non trovata per questo reso.",
        function_name=f"{_FN}.aggiorna_riga",
    )
    assert riga is not None
    data = {k: empty_to_none(v) for k, v in payload.items() if k in _UPDATE_KEYS_RIGA}
    ErrorManager.require(
        len(data) > 0,
        code="E_RESO_VALIDAZIONE",
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
    _assert_stato(
        repo, reso_id, _STATI_RIGHE_MODIFICABILI, op="elimina_riga",
        message="Righe eliminabili solo su reso in bozza.",
    )
    riga = repo.get_riga(riga_id)
    ErrorManager.require(
        riga is not None and riga["reso_id"] == reso_id,
        code="E_RESO_NOT_FOUND",
        message="Riga non trovata per questo reso.",
        function_name=f"{_FN}.elimina_riga",
    )
    assert riga is not None
    with _db_errors("elimina_riga"):
        deleted = repo.delete_riga(riga_id)
    return {"reso_id": reso_id, "riga_id": riga_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  Helper privati
# ══════════════════════════════════════════════════════════

# Scopo: Crea una riga reso con snapshot dalla riga DDT (articolo/descrizione/
#        UoM/factor/ordine_riga_id). Guard: la riga DDT deve appartenere al DDT
#        sorgente del reso; tipo_reso_id e una quantita' (operativa o base)
#        obbligatori. Chiamato da crea_reso (dentro l'atomic) e gestisci_riga.
def _crea_riga(
    repo: ResiRepository, reso_id: int, ddt_id: int, payload: dict[str, Any],
) -> dict[str, Any]:
    data = {k: empty_to_none(v) for k, v in payload.items() if k in _CREATE_KEYS_RIGA}

    raw_ddt_riga_id = data.get("ddt_riga_id")
    ErrorManager.require(
        raw_ddt_riga_id is not None,
        code="E_RESO_VALIDAZIONE",
        message="ddt_riga_id obbligatorio: la riga reso nasce da una riga DDT.",
        function_name=f"{_FN}._crea_riga",
    )
    assert raw_ddt_riga_id is not None
    try:
        ddt_riga_id = int(raw_ddt_riga_id)
    except (TypeError, ValueError):
        ddt_riga_id = 0
        ErrorManager.require(
            False,
            code="E_RESO_VALIDAZIONE",
            message="ddt_riga_id non valido.",
            detail=f"ddt_riga_id={raw_ddt_riga_id!r}",
            function_name=f"{_FN}._crea_riga",
        )

    snapshot = repo.get_ddt_riga_snapshot(ddt_riga_id)
    ErrorManager.require(
        snapshot is not None and int(snapshot["ddt_id"]) == int(ddt_id),
        code="E_RESO_VALIDAZIONE",
        message="La riga DDT indicata non appartiene al DDT sorgente del reso.",
        detail=f"ddt_riga_id={ddt_riga_id} ddt_id={ddt_id}",
        function_name=f"{_FN}._crea_riga",
    )
    assert snapshot is not None

    tipo_reso_id = data.get("tipo_reso_id")
    ErrorManager.require(
        tipo_reso_id is not None,
        code="E_RESO_VALIDAZIONE",
        message="tipo_reso_id obbligatorio (a credito / per ri-consegna).",
        function_name=f"{_FN}._crea_riga",
    )
    assert tipo_reso_id is not None

    quantita = data.get("quantita")
    qta_operativa = data.get("qta_operativa")
    ErrorManager.require(
        quantita is not None or qta_operativa is not None,
        code="E_RESO_VALIDAZIONE",
        message="Quantita' resa obbligatoria (qta_operativa o quantita).",
        function_name=f"{_FN}._crea_riga",
    )

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
        tipo_reso_id=int(tipo_reso_id),
        quantita=quantita,
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


# Scopo: Context manager per normalizzare errori DB in ServiceError parlanti.
#        Gemello _db_errors di ddt_service: IntegrityError (fk) via
#        map_integrity_error + mappe vincolo; DatabaseError (RAISE P0001 delle
#        fn madri / trigger guard) via estrazione regex del codice E_* dal
#        MESSAGE, cosi' il FE fa routing UI specifico (policy famiglia E_RESO_*).
#        Fallback E_VENDITE_VALIDATION.
@contextmanager
def _db_errors(op: str) -> Iterator[None]:
    context = {"op": f"{_FN}.{op}"}
    try:
        yield
    except IntegrityError as exc:
        map_integrity_error(
            exc,
            unique_constraints=_UNIQUE_CONSTRAINTS,
            fk_constraints=_FK_CONSTRAINTS,
            fallback_code=E_VENDITE_VALIDATION,
            fallback_message="Violazione vincolo DB su reso.",
            context=context,
        )
    except DatabaseError as exc:
        exc_text = str(exc)
        match = _DB_ERROR_CODE_RE.search(exc_text)
        code = match.group(1) if match else E_VENDITE_VALIDATION
        ErrorManager.raise_error(
            code=code,
            message=exc_text.split("\n", maxsplit=1)[0].strip()
            or "Violazione vincolo DB su reso.",
            detail=exc_text,
            context=context,
        )


# Scopo: Guard di stato leggero (solo codice_interno): E_RESO_NOT_FOUND se il
#        reso non esiste, E_RESO_STATO_TRANSIZIONE se lo stato non e' ammesso.
def _assert_stato(
    repo: ResiRepository, reso_id: int, ammessi: frozenset[str], *, op: str,
    message: str | None = None,
) -> str:
    stato = repo.get_stato_codice(reso_id)
    ErrorManager.require(
        stato is not None,
        code="E_RESO_NOT_FOUND",
        message="Reso non trovato.",
        detail=f"reso_id={reso_id}",
        function_name=f"{_FN}.{op}",
    )
    assert stato is not None
    ErrorManager.require(
        stato in ammessi,
        code="E_RESO_STATO_TRANSIZIONE",
        message=message or f"Operazione non ammessa nello stato {stato}.",
        detail=f"ammessi={sorted(ammessi)}",
        function_name=f"{_FN}.{op}",
    )
    return stato
