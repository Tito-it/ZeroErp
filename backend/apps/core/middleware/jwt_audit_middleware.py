# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Middleware Django per le request `/api/*`. Tre responsabilita:
#        1) Pre-load cache permessi Redis L2 sulla request
#        2) Rifiuto early DISABILITATO con 403
#        3) Reset simmetrico delle GUC PG settate da
#           JwtAuditAuthentication (apps/core/api/jwt_audit_authentication.py).
#
#        NOTA: la propagazione delle GUC `app.jwt_user` /
#        `app.current_user_id` non avviene PIU' in questo middleware
#        ma nella DRF auth class JwtAuditAuthentication. Vedi guida:
#        docs/it/guide/risorse-umane-e-accessi.md sezione
#        "Propagazione identita utente al database (GUC)".
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.services.auth_constants import RUOLO_APPLICATIVO_DISABILITATO
from apps.core.services.permissions_cache import load_user_cache
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.request_context import get_idempotency_key, get_request_id

logger = logging.getLogger(__name__)


class JwtAuditMiddleware(MiddlewareMixin):
    """Pre-load cache permessi, rifiuto DISABILITATO, reset GUC.

    Per le richieste ``/api/`` di utenti autenticati:

    1. Pre-carica la cache permessi da Redis L2 su
       ``request._zeroerp_perms_cache``, riusata da
       ``ZeroERPPermission._get_cache()`` senza query aggiuntive.
    2. Rifiuta immediatamente gli utenti con ``ruolo_applicativo = DISABILITATO``
       restituendo 403, prima che la request raggiunga la view.

    Per tutte le request:

    3. ``process_response`` resetta le GUC PG ``app.jwt_user`` e
       ``app.current_user_id`` SE la auth class le ha settate (marker
       ``request._zeroerp_jwt_guc_set``). Cleanup simmetrico, defensive
       contro futuri scenari ``CONN_MAX_AGE > 0`` o pgbouncer
       transaction-mode dove le GUC potrebbero leak fra request sulla
       stessa connessione.

    **Le GUC NON vengono settate qui**: la propagazione e' fatta da
    ``apps.core.api.jwt_audit_authentication.JwtAuditAuthentication``
    durante ``authenticate()`` del flusso DRF, perche' a ``process_view``
    time ``request.user`` e' AnonymousUser per le request JWT (DRF
    authentication gira nel view dispatch dopo i Django middleware).
    Vedi guida ``risorse-umane-e-accessi.md`` sezione "Propagazione
    identita utente al database (GUC)".
    """

    def process_view(
        self,
        request: HttpRequest,
        view_func: object,
        view_args: tuple,
        view_kwargs: dict,
    ) -> HttpResponse | None:
        del view_func, view_args, view_kwargs
        # Solo per API: pre-load cache permessi e check DISABILITATO.
        if not request.path.startswith("/api/"):
            return None
        user = getattr(request, "user", None)
        if not (user and getattr(user, "is_authenticated", False)):
            return None

        # Scopo: Pre-carica cache permessi da Redis L2 (riusata da
        # ZeroERPPermission._get_cache senza query aggiuntive).
        if not hasattr(request, "_zeroerp_perms_cache"):
            redis_data = load_user_cache(user.id)
            request._zeroerp_perms_cache = redis_data or {}  # type: ignore[attr-defined]
            request._zeroerp_perms_cache_loaded_from_redis = redis_data is not None  # type: ignore[attr-defined]

        # Scopo: Rifiuto early DISABILITATO con 403 strutturato.
        # Check diretto su ruolo_applicativo (GUC-first, vedi
        # PermissionResolver.get_ruolo_applicativo).
        ruolo_app = PermissionResolver.get_ruolo_applicativo(
            user, cache=request._zeroerp_perms_cache  # type: ignore[attr-defined]
        )
        if ruolo_app != RUOLO_APPLICATIVO_DISABILITATO:
            return None

        logger.warning(
            "security.user_disabilitato user_id=%s path=%s",
            user.id, request.path,
        )
        payload: dict = {
            "error": {
                "code": "E_USER_DISABILITATO",
                "message": "Utente disabilitato.",
            }
        }
        meta: dict[str, str] = {}
        request_id = get_request_id()
        if request_id:
            meta["request_id"] = request_id
        idempotency_key = get_idempotency_key()
        if idempotency_key:
            meta["idempotency_key"] = idempotency_key
        if meta:
            payload["meta"] = meta
        return JsonResponse(payload, status=403)

    # Scopo: Reset simmetrico delle GUC PG settate da
    # JwtAuditAuthentication. Resetta solo se la auth class ha
    # impostato il marker `_zeroerp_jwt_guc_set` sulla request.
    # Defense-in-depth contro leak fra request in scenari futuri
    # con CONN_MAX_AGE > 0 o connection pooling esterno.
    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        if not getattr(request, "_zeroerp_jwt_guc_set", False):
            return response
        try:
            with connection.cursor() as cursor:
                # Scopo: Reset simmetrico dei 5 GUC settati da
                # set_jwt_gucs — mantenere l'elenco allineato.
                cursor.execute(
                    "SELECT set_config('app.jwt_user',            '', false), "
                    "       set_config('app.current_user_id',     '', false), "
                    "       set_config('app.current_identita_id', '', false), "
                    "       set_config('app.ruolo_applicativo',   '', false), "
                    "       set_config('app.soggetto_ruolo_id',   '', false)"
                )
        except DatabaseError:
            # Cleanup best-effort: DB irraggiungibile non deve rompere
            # la response (la connessione si chiude comunque, GUC perse).
            logger.warning(
                "jwt_audit_middleware.guc_reset_failed", exc_info=True
            )
        return response
