# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing unificato errori pipeline attivita fatturabili.
# ------------------------------------------------------------


from typing import Any, Literal

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.attivita_pipeline_repository import AttivitaPipelineRepository

# Contratto unico errori applicativi pipeline attivita:
# - scope ATTIVITA_FATTURABILI/ATTIVITA
# - severity I/W/C
# - code stabile
# - context/meta strutturata

ErrorScope = Literal["ATTIVITA_FATTURABILI", "ATTIVITA"]
ErrorSeverity = Literal["I", "W", "C"]


class AttivitaPipelineErrorLogger:
    """Logger unificato per errori funzionali pipeline attivita fatturabili."""

    # Scopo: Inizializza la istanza.
    def __init__(self, repository: AttivitaPipelineRepository | None = None) -> None:
        self.repository = repository or AttivitaPipelineRepository()

    # Scopo: Gestisce log_error nel flusso applicativo pipeline attivita.
    def log_error(
        self,
        *,
        scope: ErrorScope,
        severity: ErrorSeverity,
        code: str,
        message: str,
        detail: str | None = None,
        lotto_id: int | None = None,
        context: dict[str, Any] | None = None,
        function_name: str = "vendite.attivita_pipeline_error_logger.log_error",
    ) -> None:
        # Non inferire dal testo: scope e severity sono espliciti.
        meta: dict[str, Any] = {
            "scope": scope,
            "severity": severity,
            "code": code,
            "detail": detail,
            "context": context or {},
            "function_name": function_name,
        }
        if lotto_id is not None:
            meta["lotto_id"] = lotto_id

        # Canale unico: log tecnico centralizzato (best effort).
        # La tabella log specifica per attivita non e` ancora definita in DB.
        ErrorManager.log_error_only(
            code=code,
            context=meta,
            area="backend",
            function_name=function_name,
        )
