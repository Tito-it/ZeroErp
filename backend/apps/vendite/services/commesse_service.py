# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo commesse — entry-point per le API REST.
# ------------------------------------------------------------

"""
Funzioni esposte:
- pr_run_commesse_push   — lancia l'orchestratore push commesse (write)
- fn_get_commesse_push_log — dettaglio di un push log (read)
- fn_get_commessa_stato  — stato e contatori di una commessa (read)
- fn_list_commessa_attivita — lista paginata attività di una commessa (read)
"""

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.services.commesse_push_orchestrator import CommessaPushOrchestrator
from apps.vendite.services.commesse_source_handlers import (
    HandlerContratti,
    HandlerConsumi,
    HandlerDdt,
    HandlerOrdini,
    HandlerPreventivi,
)


def _build_handlers(repo: CommesseRepository) -> list:
    """Costruisce la lista ordinata di handler sorgente per l'orchestratore."""
    return [
        HandlerPreventivi(repo),
        HandlerOrdini(repo),
        HandlerContratti(repo),
        HandlerDdt(repo),
        HandlerConsumi(repo),
    ]


# Scopo: Lancia l'orchestratore push commesse e restituisce il report serializzato.
def pr_run_commesse_push(
    *,
    source_types: list[str] | None = None,
    dry_run: bool = False,
    user_run: str | None = None,
) -> dict:
    """Entrypoint servizio Python: esegue il push commesse da sorgenti esterne."""
    repo = CommesseRepository()
    handlers = _build_handlers(repo)
    orch = CommessaPushOrchestrator(repo, handlers)
    report = orch.run(source_types=source_types, dry_run=dry_run, user_run=user_run)
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
