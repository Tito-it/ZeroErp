# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing unificato errori pipeline vendite (scope LOTTO/FATTURA).
# ------------------------------------------------------------


from typing import Any, Literal

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import VenditePipelineRepository

# Contratto unico errori applicativi pipeline:
# - scope LOTTO/FATTURA
# - severity I/W/C
# - code stabile
# - ids dominio + context/meta

ErrorScope = Literal["LOTTO", "FATTURA"]
ErrorSeverity = Literal["I", "W", "C"]


class PipelineErrorLogger:
    """Logger unificato per errori funzionali pipeline vendite."""

    # Scopo: Inizializza la istanza.
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    # Scopo: Gestisce `log_error` nel flusso applicativo del modulo.
    def log_error(
        self,
        *,
        scope: ErrorScope,
        severity: ErrorSeverity,
        code: str,
        message: str,
        detail: str | None = None,
        lotto_id: int | None = None,
        fattura_id: int | None = None,
        stato_doc_fiscale_id: int | None = None,
        context: dict[str, Any] | None = None,
        function_name: str = "vendite.pipeline_error_logger.log_error",
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
        if fattura_id is not None:
            meta["fattura_id"] = fattura_id
        if stato_doc_fiscale_id is not None:
            meta["stato_doc_fiscale_id"] = stato_doc_fiscale_id

        # Sempre log tecnico centralizzato (best effort).
        ErrorManager.log_error_only(
            code=code,
            context=meta,
            area="backend",
            function_name=function_name,
        )

        if scope == "LOTTO":
            if lotto_id is None:
                return
            self.repository.log_pipeline_fase(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                fase="Errore pipeline",
                status=severity,
                messaggio=message,
                meta=meta,
            )
            return

        if scope == "FATTURA":
            if fattura_id is None:
                return
            self.repository.log_fattura(
                fattura_id=fattura_id,
                status=severity,
                messaggio=message,
                critical=severity == "C",
                meta=meta,
            )
