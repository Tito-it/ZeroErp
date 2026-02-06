# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gestione errori e validazioni centralizzate.
# ------------------------------------------------------------


import json
from typing import Any

from django.db import connection

from apps.core.services.service_errors import ServiceError

# Helper unico errori: validazione, raise strutturato e logging opzionale su DB.


class ErrorManager:
    """Utility centralizzata per evitare logica errori duplicata nei servizi."""

    @staticmethod
    def raise_error(
        *,
        code: str,
        message: str,
        detail: str | None = None,
        hint: str | None = None,
        retryable: bool = False,
        context: dict[str, Any] | None = None,
        area: str = "backend",
        function_name: str = "django_service",
        log_to_db: bool = False,
        cause: Exception | None = None,
    ) -> None:
        if log_to_db:
            ErrorManager.log_error_only(
                code=code,
                context=context or {},
                area=area,
                function_name=function_name,
            )

        service_error = ServiceError(
            code=code,
            message=message,
            detail=detail,
            hint=hint,
            retryable=retryable,
            context=context,
        )
        if cause is not None:
            raise service_error from cause
        raise service_error

    @staticmethod
    def require(
        condition: bool,
        *,
        code: str,
        message: str,
        detail: str | None = None,
        hint: str | None = None,
        context: dict[str, Any] | None = None,
        area: str = "backend",
        function_name: str = "django_service",
        log_to_db: bool = False,
    ) -> None:
        if condition:
            return
        ErrorManager.raise_error(
            code=code,
            message=message,
            detail=detail,
            hint=hint,
            context=context,
            area=area,
            function_name=function_name,
            log_to_db=log_to_db,
        )

    @staticmethod
    def log_error_only(
        *,
        code: str,
        context: dict[str, Any] | None = None,
        area: str = "backend",
        function_name: str = "django_service",
    ) -> None:
        # Best-effort: non deve rompere il flusso applicativo.
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT script.fn_log_error_only(
                        %s, %s, %s, %s::jsonb, NULL::uuid, VARIADIC ARRAY[]::text[]
                    )
                    """,
                    [area, function_name, code, json.dumps(context or {})],
                )
        except Exception:
            return
