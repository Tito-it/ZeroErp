from dataclasses import asdict, dataclass
from typing import Any

from django.db import DatabaseError

from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.service_errors import ServiceError

# Translator centralizzato: converte errori Python/DB in payload API uniforme.


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    detail: str | None = None
    hint: str | None = None
    tx_id: str | None = None
    retryable: bool = False
    ui_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


class ErrorTranslator:
    """Traduce eccezioni applicative/DB in un envelope errore coerente per le API."""

    @staticmethod
    def to_api_error(exc: Exception) -> ApiError:
        # Errori applicativi standard: passa codice/messaggio senza perdere metadati.
        if isinstance(exc, ServiceError):
            return ErrorTranslator._apply_policy(
                ApiError(
                code=exc.code,
                message=exc.message,
                detail=exc.detail or str(exc),
                hint=exc.hint,
                tx_id=exc.tx_id,
                retryable=exc.retryable,
                )
            )

        # Errori DB: prova a estrarre dettaglio tecnico (DETAIL/HINT/sqlstate).
        if isinstance(exc, DatabaseError):
            return ErrorTranslator._apply_policy(ErrorTranslator._from_database_error(exc))

        return ErrorTranslator._apply_policy(ApiError(
            code="E_GENERICO",
            message="Errore non gestito.",
            detail=str(exc),
            retryable=False,
        ))

    @staticmethod
    def get_http_status(api_error: ApiError) -> int:
        return ErrorPolicyRegistry.resolve(api_error.code).http_status

    @staticmethod
    def _apply_policy(api_error: ApiError) -> ApiError:
        policy = ErrorPolicyRegistry.resolve(api_error.code)
        return ApiError(
            code=api_error.code,
            message=api_error.message or policy.user_message,
            detail=api_error.detail,
            hint=api_error.hint,
            tx_id=api_error.tx_id,
            retryable=api_error.retryable,
            ui_action=policy.ui_action,
        )

    @staticmethod
    def _from_database_error(exc: DatabaseError) -> ApiError:
        cause = getattr(exc, "__cause__", None)
        diag = getattr(cause, "diag", None)

        detail = getattr(diag, "message_detail", None)
        hint = getattr(diag, "message_hint", None)
        message = str(exc) or "Errore durante l'operazione database."
        sqlstate = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)

        # Heuristica retryable: serializzazione/deadlock possono essere ritentati.
        retryable = sqlstate in {"40001", "40P01"}
        code = "E_DATABASE_RETRYABLE" if retryable else "E_DATABASE"

        return ApiError(
            code=code,
            message=message,
            detail=detail,
            hint=hint,
            retryable=retryable,
        )
