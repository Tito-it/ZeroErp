# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestrazione reset tecnico lotto DRAFT.
# ------------------------------------------------------------


from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.types import ResetLottoDraftResult

# Servizio applicativo: espone il reset tecnico lotto DRAFT.


class LottoResetService:
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

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
