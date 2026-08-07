# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gestione errori e validazioni centralizzate.
# ------------------------------------------------------------


import json
from typing import Any, NoReturn

from django.db import connection

from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.service_errors import ServiceError

# Helper unico errori: validazione, raise strutturato e logging opzionale su DB.


class ErrorManager:
    """Utility centralizzata per evitare logica errori duplicata nei servizi."""

    # Scopo: Costruisce e solleva un ServiceError uniforme, con logging DB opzionale.
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

    # Scopo: Valida una condizione e in caso negativo genera ServiceError coerente con policy core.
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

    # Scopo: Traduce una DatabaseError (tipicamente RAISE P0001 dal DB) in
    #        ServiceError preservando il codice originale. Il messaggio
    #        dell'eccezione viene confrontato con `known_markers`: la PRIMA
    #        voce i cui marker compaiono TUTTI nel messaggio vince; nessun
    #        match -> `fallback_code`. I marker restano dati di dominio del
    #        chiamante (ogni service dichiara i propri); qui vive solo il
    #        meccanismo di match+raise, prima duplicato in pricing_service,
    #        ui_service e dashboard_service.
    #        Nota fragilita' (review B4/F1 2026-04-15): il match su substring
    #        regge finche' il codice/template sopravvive nel MESSAGE_TEXT del
    #        RAISE; la soluzione strutturale (codice in DETAIL/HINT lato DB)
    #        e' rimandata — proteggersi con test di regressione sui marker.
    #
    #        Varianti per il caso NESSUN match:
    #        - `fallback_code=None` -> ri-solleva l'eccezione originale
    #          (la policy generica la mappa il middleware, es. E_DATABASE);
    #        - `fallback_message` -> messaggio utente alternativo quando si
    #          usa il fallback (default: stesso `message` del caso match).
    @staticmethod
    def raise_from_database_error(
        exc: Exception,
        *,
        known_markers: tuple[tuple[str, tuple[str, ...]], ...],
        fallback_code: str | None,
        message: str,
        fallback_message: str | None = None,
        context: dict[str, Any] | None = None,
        function_name: str = "django_service",
        log_to_db: bool = True,
    ) -> NoReturn:
        msg = str(exc)
        matched_code: str | None = None
        # Campo strutturato per primo, ma SOLO se il codice e' fra quelli che il
        # chiamante ha dichiarato di conoscere: `message` vs `fallback_message`
        # sotto dipendono da "riconosciuto o no", e un codice che il chiamante
        # non ha in lista non e' riconosciuto — accettarlo qui gli farebbe usare
        # il messaggio del caso riconosciuto per un errore che non aspettava.
        # L'insieme degli esiti resta identico: cambia solo che il match non
        # dipende piu' da come e' scritto il testo dell'eccezione.
        structured = structured_db_error_code(exc)
        if structured is not None and any(c == structured for c, _ in known_markers):
            matched_code = structured
        for code_candidate, markers in known_markers:
            if matched_code is not None:
                break
            if all(marker in msg for marker in markers):
                matched_code = code_candidate
                break
        if matched_code is None and fallback_code is None:
            raise exc
        ErrorManager.raise_error(
            code=matched_code or fallback_code,
            message=(
                message
                if matched_code is not None or fallback_message is None
                else fallback_message
            ),
            detail=msg,
            context=context,
            cause=exc,
            log_to_db=log_to_db,
            function_name=function_name,
        )
        raise AssertionError("unreachable: raise_error alza sempre")

    # Scopo: Registra un errore tecnico su DB in best-effort senza interrompere il flusso chiamante.
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
