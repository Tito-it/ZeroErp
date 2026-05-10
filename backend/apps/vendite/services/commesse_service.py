# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo commesse — entry-point per le API REST.
# ------------------------------------------------------------

"""
Funzioni esposte:
- pr_run_commesse_push      — lancia l'orchestratore push commesse batch (write)
- pr_run_commesse_push_one  — push singolo documento sorgente filtrato (write)
- fn_get_commesse_push_log  — dettaglio di un push log (read)
- fn_get_commessa_stato     — stato e contatori di una commessa (read)
- fn_list_commessa_attivita — lista paginata attività di una commessa (read)
"""

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.listini_repository import ListiniRepository
from apps.vendite.services.commesse_push_orchestrator import CommessaPushOrchestrator
from apps.vendite.services.commesse_source_handlers import (
    BaseSourceHandler,
    HandlerContratti,
    HandlerConsumi,
    HandlerDdt,
    HandlerOrdini,
    HandlerPreventivi,
)

# Registry: codice config.sorgenti → handler class.
# Permette costruzione dinamica basata sulle sorgenti attive in DB.
_HANDLER_REGISTRY: dict[str, type[BaseSourceHandler]] = {
    "PREVENTIVO": HandlerPreventivi,
    "ORDINE_VENDITA": HandlerOrdini,
    "CONTRATTO": HandlerContratti,
    "DDT_VENDITA": HandlerDdt,
    "ATTIVITA_CONSUMI": HandlerConsumi,
}


def _build_handlers(repo: CommesseRepository) -> list[BaseSourceHandler]:
    """Costruisce handler solo per le sorgenti attive in config.sorgenti.

    Ordine determinato da config.sorgenti.id (registrazione).
    Sorgenti attive in DB ma senza handler Python vengono silenziosamente
    ignorate (validate_sorgente_map le rileva come warning).
    """
    active_codes = repo.list_active_push_sources()
    return [
        _HANDLER_REGISTRY[codice](repo)
        for codice in active_codes
        if codice in _HANDLER_REGISTRY
    ]


# Scopo: Lancia l'orchestratore push commesse e restituisce il report serializzato.
def pr_run_commesse_push(
    *,
    source_types: list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Entrypoint servizio Python: esegue il push commesse da sorgenti esterne."""
    repo = CommesseRepository()
    handlers = _build_handlers(repo)

    if source_types is not None:
        valid_codes = {h.sorgente_codice for h in handlers}
        unknown = [s for s in source_types if s not in valid_codes]
        if unknown:
            ErrorManager.raise_error(
                code="E_COMMESSA_VALIDATION",
                message="Codici sorgente non validi.",
                detail=f"source_types non riconosciuti: {unknown}. Sorgenti attive: {sorted(valid_codes)}",
                context={"source_types": source_types, "unknown": unknown},
                function_name="vendite.commesse_service.pr_run_commesse_push",
            )

    orch = CommessaPushOrchestrator(repo, handlers)
    report = orch.run(source_types=source_types, dry_run=dry_run)
    return {
        "stato": report.stato,
        "dry_run": report.dry_run,
        "push_log_id": report.push_log_id,
        "durata_ms": report.durata_ms,
        "handlers": [r.as_dict() | {"handler_name": r.handler_name} for r in report.handlers],
    }


# Scopo: Variante puntuale del push commesse — esegue UN solo handler con
# filtro sulla riga sorgente identificata da `sorgente_uid`. Riusa
# orchestrator (lock + log su commesse_push_log + event_log): differisce
# dal batch solo per perimetro di processing (1 documento invece di N).
# Usato dal pulsante UI "Push commessa" del drawer preventivo (e in futuro
# dai pulsanti analoghi su ordini/DDT). Validazione stretta sul codice
# sorgente per evitare run vuoti silenziosi su typo durante refactor.
def pr_run_commesse_push_one(
    *,
    sorgente_codice: str,
    sorgente_uid: int,
    dry_run: bool = False,
) -> dict:
    """Entrypoint servizio Python: push commesse di un singolo documento sorgente."""
    repo = CommesseRepository()
    handlers = _build_handlers(repo)

    valid_codes = {h.sorgente_codice for h in handlers}
    ErrorManager.require(
        sorgente_codice in valid_codes,
        code="E_COMMESSA_VALIDATION",
        message="Codice sorgente non valido per push singolo.",
        detail=f"sorgente_codice={sorgente_codice} non in {sorted(valid_codes)}",
        context={"sorgente_codice": sorgente_codice, "valid_codes": sorted(valid_codes)},
        function_name="vendite.commesse_service.pr_run_commesse_push_one",
    )
    ErrorManager.require(
        bool(sorgente_uid and sorgente_uid > 0),
        code="E_COMMESSA_VALIDATION",
        message="Identificativo sorgente non valido.",
        detail=f"sorgente_uid={sorgente_uid} deve essere intero positivo",
        context={"sorgente_uid": sorgente_uid},
        function_name="vendite.commesse_service.pr_run_commesse_push_one",
    )

    orch = CommessaPushOrchestrator(repo, handlers)
    report = orch.run(
        source_types=[sorgente_codice],
        dry_run=dry_run,
        sorgente_uid=sorgente_uid,
    )
    return {
        "stato": report.stato,
        "dry_run": report.dry_run,
        "push_log_id": report.push_log_id,
        "durata_ms": report.durata_ms,
        "handlers": [r.as_dict() | {"handler_name": r.handler_name} for r in report.handlers],
    }


# Scopo: Restituisce il dettaglio di un push log per consultazione operativa.
def fn_get_commesse_push_log(*, push_log_id: int) -> dict:
    """Entrypoint servizio Python: dettaglio push log commesse."""
    ErrorManager.require(
        bool(push_log_id and push_log_id > 0),
        code="E_COMMESSA_VALIDATION",
        message="Parametri non validi.",
        detail="push_log_id obbligatorio e > 0",
        context={"push_log_id": push_log_id},
        function_name="vendite.commesse_service.fn_get_commesse_push_log",
        log_to_db=True,
    )
    repo = CommesseRepository()
    row = repo.get_push_log(push_log_id)
    if row is None:
        ErrorManager.raise_error(
            code="E_COMMESSA_PUSH_LOG_NOT_FOUND",
            message="Push log non trovato.",
            detail=f"Nessun push log con id={push_log_id}",
            context={"push_log_id": push_log_id},
            function_name="vendite.commesse_service.fn_get_commesse_push_log",
            log_to_db=True,
        )
    assert row is not None  # raise_error è NoReturn — aiuta il type checker
    return dict(row)


# Scopo: Restituisce stato e contatori di una commessa per consultazione operativa.
def fn_get_commessa_stato(*, commessa_id: int) -> dict:
    """Entrypoint servizio Python: stato commessa con contatori."""
    ErrorManager.require(
        bool(commessa_id and commessa_id > 0),
        code="E_COMMESSA_VALIDATION",
        message="Parametri non validi.",
        detail="commessa_id obbligatorio e > 0",
        context={"commessa_id": commessa_id},
        function_name="vendite.commesse_service.fn_get_commessa_stato",
        log_to_db=True,
    )
    repo = CommesseRepository()
    stato = repo.get_commessa_stato(commessa_id)
    if stato is None:
        ErrorManager.raise_error(
            code="E_COMMESSA_NOT_FOUND",
            message="Commessa non trovata.",
            detail=f"Nessuna commessa con id={commessa_id}",
            context={"commessa_id": commessa_id},
            function_name="vendite.commesse_service.fn_get_commessa_stato",
            log_to_db=True,
        )
    assert stato is not None  # raise_error è NoReturn — aiuta il type checker
    return {"commessa_id": commessa_id, **dict(stato)}


# Scopo: Restituisce la lista paginata delle attività di una commessa.
def fn_list_commessa_attivita(
    *,
    commessa_id: int,
    stato_emissione: str | None = None,
    stato_approvazione: str | None = None,
    competenza_mese: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Entrypoint servizio Python: lista attività commessa (paginata)."""
    ErrorManager.require(
        bool(commessa_id and commessa_id > 0),
        code="E_COMMESSA_VALIDATION",
        message="Parametri non validi.",
        detail="commessa_id obbligatorio e > 0",
        context={"commessa_id": commessa_id},
        function_name="vendite.commesse_service.fn_list_commessa_attivita",
        log_to_db=True,
    )
    ErrorManager.require(
        1 <= int(limit) <= 200,
        code="E_COMMESSA_VALIDATION",
        message="Parametri non validi.",
        detail="limit deve essere compreso tra 1 e 200",
        context={"commessa_id": commessa_id, "limit": limit},
        function_name="vendite.commesse_service.fn_list_commessa_attivita",
        log_to_db=True,
    )
    from apps.core.api.payload_validators import optional_iso_date as _parse_date

    competenza_mese_date = _parse_date({"competenza_mese": competenza_mese}, "competenza_mese") if competenza_mese else None

    repo = CommesseRepository()
    data = repo.list_commessa_attivita(
        commessa_id,
        stato_emissione=stato_emissione,
        stato_approvazione=stato_approvazione,
        competenza_mese=competenza_mese_date,
        limit=limit,
        offset=offset,
    )
    return {"commessa_id": commessa_id, **data}


# --- N5, N7, N7-sblocco: Pricing operations su commessa ---

_STATI_COMMESSA_MODIFICABILI: frozenset[str] = frozenset({"LIBERO", "CONFERMATO"})
_MOTIVO_MAX_LENGTH = 500


# Scopo: Normalizza il campo meta da stringa JSON o dict a dict. Gestisce None, str, dict.
def _parse_meta_json(meta_raw: Any) -> dict[str, Any]:
    if not meta_raw:
        return {}
    if isinstance(meta_raw, str):
        return json.loads(meta_raw)
    return meta_raw if isinstance(meta_raw, dict) else {}


# Scopo: Helper — carica attivita` con dati pricing e applica guard standard.
def _get_attivita_pricing_or_raise(
    commessa_id: int,
    attivita_id: int,
    *,
    function_name: str,
) -> dict[str, Any]:
    repo = CommesseRepository()
    att = repo.get_attivita_pricing(commessa_id, attivita_id)
    ErrorManager.require(
        att is not None,
        code="E_COMMESSA_ATTIVITA_NOT_FOUND",
        message="Attivita` commessa non trovata.",
        detail=f"Nessuna attivita` id={attivita_id} per commessa id={commessa_id}.",
        context={"commessa_id": commessa_id, "attivita_id": attivita_id},
        function_name=function_name,
        log_to_db=False,
    )
    assert att is not None
    return att


# Scopo: Helper — guard stato commessa modificabile (LIBERO o CONFERMATO).
def _assert_commessa_modificabile(
    att: dict[str, Any],
    *,
    function_name: str,
) -> None:
    stato = str(att["commessa_stato"])
    ErrorManager.require(
        stato in _STATI_COMMESSA_MODIFICABILI,
        code="E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA",
        message="Operazione non consentita sullo stato corrente della commessa.",
        detail=f"Commessa in stato {stato}. Ammesso solo: {', '.join(sorted(_STATI_COMMESSA_MODIFICABILI))}.",
        context={"commessa_stato": stato},
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Helper — guard riga non ancora fatturata.
def _assert_non_fatturata(
    att: dict[str, Any],
    *,
    function_name: str,
) -> None:
    ErrorManager.require(
        att.get("fattura_riga_id") is None,
        code="E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA",
        message="Operazione bloccata: riga gia` fatturata.",
        detail="La riga ha un fattura_riga_id valorizzato. Non e` possibile modificare il prezzo.",
        context={"fattura_riga_id": att.get("fattura_riga_id")},
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Helper — parsing prezzo dal payload.
def _parse_prezzo(payload: dict[str, Any], *, function_name: str) -> Decimal:
    raw = payload.get("prezzo")
    ErrorManager.require(
        raw is not None,
        code="E_COMMESSA_VALIDATION",
        message="Parametro obbligatorio mancante.",
        detail="prezzo e` obbligatorio.",
        context={"field": "prezzo"},
        function_name=function_name,
        log_to_db=True,
    )
    try:
        prezzo = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        ErrorManager.raise_error(
            code="E_COMMESSA_VALIDATION",
            message="Prezzo non valido.",
            detail=f"prezzo deve essere numerico, ricevuto: {raw!r}.",
            context={"field": "prezzo"},
            function_name=function_name,
            log_to_db=True,
        )
    assert isinstance(prezzo, Decimal)
    ErrorManager.require(
        prezzo > 0,
        code="E_COMMESSA_VALIDATION",
        message="Prezzo non valido.",
        detail="Il prezzo deve essere maggiore di zero.",
        context={"prezzo": str(prezzo)},
        function_name=function_name,
        log_to_db=True,
    )
    return prezzo


# Scopo: Helper — parsing motivo obbligatorio dal payload.
def _parse_motivo(payload: dict[str, Any], *, function_name: str) -> str:
    motivo = payload.get("motivo")
    ErrorManager.require(
        motivo and isinstance(motivo, str) and motivo.strip(),
        code="E_COMMESSA_VALIDATION",
        message="Motivo obbligatorio.",
        detail="Il campo motivo e` obbligatorio per questa operazione.",
        context={"field": "motivo"},
        function_name=function_name,
        log_to_db=True,
    )
    assert isinstance(motivo, str)
    motivo = motivo.strip()
    ErrorManager.require(
        len(motivo) <= _MOTIVO_MAX_LENGTH,
        code="E_COMMESSA_VALIDATION",
        message="Motivo troppo lungo.",
        detail=f"Massimo {_MOTIVO_MAX_LENGTH} caratteri.",
        context={"field": "motivo", "length": len(motivo)},
        function_name=function_name,
        log_to_db=False,
    )
    return motivo


# --- N5: Riallineamento prezzo ---

# Scopo: Ricalcola il prezzo da listino per un'attivita` non ancora fatturata
#        e non bloccata manualmente. Se la versione listino e` cambiata rispetto
#        allo snapshot originale, richiede conferma esplicita.
def fn_riallinea_prezzo(
    commessa_id: int,
    attivita_id: int,
    payload: dict[str, Any],
) -> dict[str, object]:
    function_name = "vendite.commesse_service.fn_riallinea_prezzo"

    att = _get_attivita_pricing_or_raise(commessa_id, attivita_id, function_name=function_name)
    _assert_commessa_modificabile(att, function_name=function_name)
    _assert_non_fatturata(att, function_name=function_name)

    ErrorManager.require(
        not att.get("prezzo_bloccato"),
        code="E_COMMESSA_VALIDATION",
        message="Riallineamento non ammesso su prezzo bloccato.",
        detail="Il prezzo e` bloccato (override manuale). Per riallinearlo prima sbloccarlo.",
        context={"prezzo_bloccato": att.get("prezzo_bloccato")},
        function_name=function_name,
        log_to_db=True,
    )

    # Risolve il prezzo attuale dal listino
    listini_repo = ListiniRepository()
    resolver_result = listini_repo.test_resolver(
        articolo_id=att["articolo_id"],
        uom_id=att["uom_id"],
        data_riferimento=att["data_attivita"],
        billing_account_id=att.get("billing_account_id"),
        utility_id=att.get("utility_id"),
        emittente_soggetto_ruolo_id=att.get("emittente_soggetto_ruolo_id"),
    )

    # Guard: versione cambiata
    versione_originale = att.get("listino_versione_id")
    versione_attuale = resolver_result.get("listino_versione_id")
    versione_cambiata = versione_originale is not None and versione_attuale != versione_originale

    if versione_cambiata and not payload.get("conferma_versione_diversa"):
        return {
            "versione_cambiata": True,
            "versione_originale_id": versione_originale,
            "versione_attuale_id": versione_attuale,
            "prezzo_attuale": str(att["prezzo_snapshot"]),
            "prezzo_ricalcolato": str(resolver_result["prezzo"]),
            "richiede_conferma": True,
        }

    nuovo_prezzo = str(resolver_result["prezzo"])
    repo = CommesseRepository()

    meta = _parse_meta_json(att.get("meta"))
    riallineamenti = list(meta.get("riallineamenti", []))
    riallineamenti.append({
        "data": datetime.now(timezone.utc).isoformat(),
        "prezzo_precedente": str(att["prezzo_snapshot"]),
        "prezzo_nuovo": nuovo_prezzo,
        "listino_versione_id_precedente": versione_originale,
        "listino_versione_id_nuovo": versione_attuale,
    })
    meta["riallineamenti"] = riallineamenti

    with transaction.atomic():
        repo.lock_attivita_for_update(attivita_id)
        repo.update_attivita_prezzo(
            attivita_id=attivita_id,
            prezzo=nuovo_prezzo,
            prezzo_bloccato=False,
            meta=meta,
        )

    return {
        "attivita_id": attivita_id,
        "prezzo_precedente": str(att["prezzo_snapshot"]),
        "prezzo_nuovo": nuovo_prezzo,
        "versione_cambiata": versione_cambiata,
    }


# --- N7: Variazione prezzo eccezionale ---

# Scopo: Override manuale del prezzo su un'attivita` di commessa LIBERA o CONFERMATA.
#        Imposta prezzo_bloccato=TRUE. Motivo obbligatorio.
def fn_variazione_prezzo_eccezionale(
    commessa_id: int,
    attivita_id: int,
    payload: dict[str, Any],
) -> dict[str, object]:
    function_name = "vendite.commesse_service.fn_variazione_prezzo_eccezionale"

    att = _get_attivita_pricing_or_raise(commessa_id, attivita_id, function_name=function_name)
    _assert_commessa_modificabile(att, function_name=function_name)
    _assert_non_fatturata(att, function_name=function_name)

    nuovo_prezzo = _parse_prezzo(payload, function_name=function_name)
    motivo = _parse_motivo(payload, function_name=function_name)

    repo = CommesseRepository()

    meta = _parse_meta_json(att.get("meta"))
    variazioni = list(meta.get("variazioni_eccezionali", []))
    variazioni.append({
        "data": datetime.now(timezone.utc).isoformat(),
        "prezzo_precedente": str(att["prezzo_snapshot"]),
        "prezzo_nuovo": str(nuovo_prezzo),
        "motivo": motivo,
        "stato_commessa": str(att["commessa_stato"]),
        "listino_versione_id_riferimento": att.get("listino_versione_id"),
    })
    meta["variazioni_eccezionali"] = variazioni

    with transaction.atomic():
        repo.lock_attivita_for_update(attivita_id)
        repo.update_attivita_prezzo(
            attivita_id=attivita_id,
            prezzo=str(nuovo_prezzo),
            prezzo_bloccato=True,
            meta=meta,
        )

    return {
        "attivita_id": attivita_id,
        "prezzo_precedente": str(att["prezzo_snapshot"]),
        "prezzo_nuovo": str(nuovo_prezzo),
        "prezzo_bloccato": True,
        "motivo": motivo,
    }


# --- N7 sblocco: Sblocca prezzo_bloccato ---

# Scopo: Sblocca un prezzo bloccato manualmente e ricalcola dal resolver.
def fn_sblocca_prezzo(
    commessa_id: int,
    attivita_id: int,
    payload: dict[str, Any],
) -> dict[str, object]:
    function_name = "vendite.commesse_service.fn_sblocca_prezzo"

    att = _get_attivita_pricing_or_raise(commessa_id, attivita_id, function_name=function_name)
    _assert_commessa_modificabile(att, function_name=function_name)
    _assert_non_fatturata(att, function_name=function_name)

    ErrorManager.require(
        att.get("prezzo_bloccato") is True,
        code="E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO",
        message="Sblocco non ammesso: il prezzo non e` bloccato.",
        detail="prezzo_bloccato e` FALSE. Nulla da sbloccare.",
        context={"prezzo_bloccato": att.get("prezzo_bloccato")},
        function_name=function_name,
        log_to_db=True,
    )

    motivo = _parse_motivo(payload, function_name=function_name)

    # Ricalcola dal resolver
    listini_repo = ListiniRepository()
    resolver_result = listini_repo.test_resolver(
        articolo_id=att["articolo_id"],
        uom_id=att["uom_id"],
        data_riferimento=att["data_attivita"],
        billing_account_id=att.get("billing_account_id"),
        utility_id=att.get("utility_id"),
        emittente_soggetto_ruolo_id=att.get("emittente_soggetto_ruolo_id"),
    )

    nuovo_prezzo = str(resolver_result["prezzo"])
    repo = CommesseRepository()

    meta = _parse_meta_json(att.get("meta"))
    sblocchi = list(meta.get("sblocchi_prezzo", []))
    sblocchi.append({
        "data": datetime.now(timezone.utc).isoformat(),
        "prezzo_bloccato_precedente": str(att["prezzo_snapshot"]),
        "prezzo_ricalcolato": nuovo_prezzo,
        "motivo": motivo,
    })
    meta["sblocchi_prezzo"] = sblocchi

    with transaction.atomic():
        repo.lock_attivita_for_update(attivita_id)
        repo.update_attivita_prezzo(
            attivita_id=attivita_id,
            prezzo=nuovo_prezzo,
            prezzo_bloccato=False,
            meta=meta,
        )

    return {
        "attivita_id": attivita_id,
        "prezzo_bloccato_precedente": str(att["prezzo_snapshot"]),
        "prezzo_ricalcolato": nuovo_prezzo,
        "prezzo_bloccato": False,
        "motivo": motivo,
    }
