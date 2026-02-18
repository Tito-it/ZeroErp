# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Policy errori per mapping HTTP/UI.
# ------------------------------------------------------------


from dataclasses import dataclass

# Registro centrale mapping errore -> comportamento API/UI.


@dataclass(frozen=True)
class ErrorPolicy:
    code: str
    http_status: int
    ui_action: str
    user_message: str


class ErrorPolicyRegistry:
    """Policy centralizzate per evitare mapping duplicato nei moduli API."""

    _POLICIES: dict[str, ErrorPolicy] = {
        "E_PIPELINE": ErrorPolicy(
            code="E_PIPELINE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore nella pipeline di fatturazione.",
        ),
        "E_PIPELINE_VALIDATION": ErrorPolicy(
            code="E_PIPELINE_VALIDATION",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Parametri pipeline non validi.",
        ),
        "E_IDEMPOTENCY_KEY_REQUIRED": ErrorPolicy(
            code="E_IDEMPOTENCY_KEY_REQUIRED",
            http_status=400,
            ui_action="highlight_form_fields",
            user_message="Idempotency-Key obbligatoria per questa operazione.",
        ),
        "E_IDEMPOTENCY_IN_PROGRESS": ErrorPolicy(
            code="E_IDEMPOTENCY_IN_PROGRESS",
            http_status=409,
            ui_action="show_retry_dialog",
            user_message="Operazione gia` in elaborazione con la stessa Idempotency-Key.",
        ),
        "E_PIPELINE_LOTTO_NOT_FOUND": ErrorPolicy(
            code="E_PIPELINE_LOTTO_NOT_FOUND",
            http_status=404,
            ui_action="show_empty_state",
            user_message="Lotto non trovato.",
        ),
        "E_PIPELINE_NOT_FOUND": ErrorPolicy(
            code="E_PIPELINE_NOT_FOUND",
            http_status=404,
            ui_action="show_error_banner",
            user_message="Configurazione pipeline non trovata.",
        ),
        "E_TASK_NOT_ALLOWED": ErrorPolicy(
            code="E_TASK_NOT_ALLOWED",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Task pipeline non autorizzato.",
        ),
        "E_TASK_NOT_IMPLEMENTED": ErrorPolicy(
            code="E_TASK_NOT_IMPLEMENTED",
            http_status=501,
            ui_action="show_error_banner",
            user_message="Task pipeline non implementato.",
        ),
        "E_DATABASE": ErrorPolicy(
            code="E_DATABASE",
            http_status=400,
            ui_action="show_error_banner",
            user_message="Errore durante l'operazione database.",
        ),
        "E_DATABASE_RETRYABLE": ErrorPolicy(
            code="E_DATABASE_RETRYABLE",
            http_status=409,
            ui_action="show_retry_dialog",
            user_message="Conflitto transazionale, riprovare l'operazione.",
        ),
        "E_GENERICO": ErrorPolicy(
            code="E_GENERICO",
            http_status=500,
            ui_action="show_error_banner",
            user_message="Errore non gestito.",
        ),
    }

    # Scopo: Gestisce `resolve` nel flusso applicativo del modulo.
    @classmethod
    def resolve(cls, code: str) -> ErrorPolicy:
        return cls._POLICIES.get(code, cls._POLICIES["E_GENERICO"])
