# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestrazione reset tecnico lotto DRAFT.
# ------------------------------------------------------------


from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.types import ResetLottoDraftResult, ResetLottoFatturaDraftResult

# Servizio applicativo: espone il reset tecnico lotto DRAFT.


class LottoResetService:
    # Scopo: Inizializza la istanza.
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    # Scopo: Gestisce `reset_lotto_draft` nel flusso applicativo del modulo.
    def reset_lotto_draft(self, lotto_id: int) -> ResetLottoDraftResult:
        ErrorManager.require(
            lotto_id is not None and lotto_id > 0,
            code="E_RESET_LOTTO_VALIDATION",
            message="Parametro lotto non valido.",
            detail="lotto_id obbligatorio e > 0",
            context={"lotto_id": lotto_id},
            function_name="vendite.lotto_reset_service.reset_lotto_draft",
            log_to_db=True,
        )
        assert lotto_id is not None
        assert lotto_id > 0
        return self.repository.reset_lotto_draft(lotto_id)

    # Scopo: Gestisce `reset_lotto_fattura_draft` nel flusso applicativo del modulo.
    def reset_lotto_fattura_draft(
        self,
        lotto_id: int,
        fattura_id: int,
    ) -> ResetLottoFatturaDraftResult:
        ErrorManager.require(
            lotto_id is not None and lotto_id > 0 and fattura_id is not None and fattura_id > 0,
            code="E_RESET_LOTTO_FATTURA_VALIDATION",
            message="Parametri reset fattura non validi.",
            detail="lotto_id e fattura_id obbligatori e > 0",
            context={"lotto_id": lotto_id, "fattura_id": fattura_id},
            function_name="vendite.lotto_reset_service.reset_lotto_fattura_draft",
            log_to_db=True,
        )
        assert lotto_id is not None
        assert lotto_id > 0
        assert fattura_id is not None
        assert fattura_id > 0
        return self.repository.reset_lotto_fattura_draft(lotto_id, fattura_id)
