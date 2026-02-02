from apps.core.services.service_errors import ServiceError


class PipelineError(ServiceError):
    """Eccezione base pipeline vendite derivata dal modello errori centralizzato."""

    def __init__(
        self,
        *,
        code: str = "E_PIPELINE",
        message: str = "Errore nella pipeline di fatturazione.",
        detail: str | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(code=code, message=message, detail=detail, hint=hint)


class PipelineValidationError(PipelineError):
    """Errore di validazione per input mancanti o non validi."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            code="E_PIPELINE_VALIDATION",
            message="Validazione pipeline fallita.",
            detail=detail,
        )


class PipelineTaskNotAllowedError(PipelineError):
    """Errore quando un task richiede una funzione fuori whitelist."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            code="E_TASK_NOT_ALLOWED",
            message="Task pipeline non autorizzato.",
            detail=detail,
        )


class PipelineTaskNotImplementedError(PipelineError):
    """Errore quando un task pipeline non e` ancora implementato in Django."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            code="E_TASK_NOT_IMPLEMENTED",
            message="Task pipeline non implementato.",
            detail=detail,
        )
