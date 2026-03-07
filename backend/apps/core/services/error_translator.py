# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Traduzione errori applicativi.
# ------------------------------------------------------------


from dataclasses import asdict, dataclass
from typing import Any

from django.conf import settings
from django.db import DatabaseError

from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.request_context import get_request_id
from apps.core.services.service_errors import ServiceError

# Translator centralizzato: converte errori Python/DB in payload API uniforme.


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    detail: str | None = None
    technical_message: str | None = None
    hint: str | None = None
    tx_id: str | None = None
    retryable: bool = False
    ui_action: str | None = None

    # Scopo: Converte ServiceError in struttura dict serializzabile per envelope API.
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


class ErrorTranslator:
    """Traduce eccezioni applicative/DB in un envelope errore coerente per le API."""

    # Scopo: Traduce una eccezione in envelope API pubblico applicando policy e sanitizzazione dettagli.
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

        # Input non valido (query param malformati, parsing fallito): 400.
        if isinstance(exc, (ValueError, TypeError)):
            message = str(exc) or "Input non valido."
            return ErrorTranslator._apply_policy(ApiError(
                code="E_VALIDATION_INPUT",
                message=message,
                detail=message,
                retryable=False,
            ))

        # Errori DB: prova a estrarre dettaglio tecnico (DETAIL/HINT/sqlstate).
        if isinstance(exc, DatabaseError):
            return ErrorTranslator._apply_policy(ErrorTranslator._from_database_error(exc))

        message = str(exc) or "Errore non gestito."
        return ErrorTranslator._apply_policy(ApiError(
            code="E_GENERICO",
            message=message,
            detail=message,
            retryable=False,
        ))

    # Scopo: Risolve lo status HTTP finale da codice errore e policy applicate.
    @staticmethod
    def get_http_status(api_error: ApiError) -> int:
        return ErrorPolicyRegistry.resolve(api_error.code).http_status

    # Scopo: Applica policy error code -> status/retry/hint al payload errore.
    @staticmethod
    def _apply_policy(api_error: ApiError) -> ApiError:
        policy = ErrorPolicyRegistry.resolve(api_error.code)
        expose_technical = getattr(settings, "API_EXPOSE_TECHNICAL_DETAILS", False)
        is_technical = ErrorTranslator._is_technical_code(api_error.code)
        detail = ErrorTranslator._sanitize_public_detail(api_error)
        # `message` resta sempre business/safe per stabilita` client/UI.
        public_message = policy.user_message if is_technical else (api_error.message or policy.user_message)
        # In debug esponi il dettaglio tecnico reale, mantenendo `message` business.
        technical_message = (
            (api_error.detail or api_error.message)
            if is_technical and expose_technical
            else None
        )
        return ApiError(
            code=api_error.code,
            message=public_message,
            detail=detail,
            technical_message=technical_message,
            hint=api_error.hint,
            tx_id=api_error.tx_id,
            retryable=api_error.retryable,
            ui_action=policy.ui_action,
        )

    # Scopo: Sanitizza i dettagli tecnici non esponibili in risposta pubblica.
    @staticmethod
    def _sanitize_public_detail(api_error: ApiError) -> str | None:
        # Per errori tecnici non esporre stack SQL/PLpgSQL al client, anche in debug:
        # in debug il dettaglio tecnico va in `technical_message`.
        if ErrorTranslator._is_technical_code(api_error.code):
            request_id = get_request_id()
            if request_id:
                return f"Dettaglio tecnico non esposto. Usa request_id={request_id} per supporto."
            return "Dettaglio tecnico non esposto. Usa request_id per supporto."

        return api_error.detail

    # Scopo: Determina se il codice errore appartiene alla categoria tecnica/non funzionale.
    @staticmethod
    def _is_technical_code(code: str) -> bool:
        return code in {"E_PIPELINE", "E_DATABASE", "E_GENERICO"}

    # Scopo: Converte eccezioni DB in ServiceError coerente con il contratto errori core.
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
