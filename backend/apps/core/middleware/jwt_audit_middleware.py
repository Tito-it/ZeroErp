# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Propaga lo user JWT come GUC PostgreSQL per audit reale
#        e rifiuta immediatamente gli utenti DISABILITATO sulle API.
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.services.permissions_cache import load_user_cache
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.request_context import get_idempotency_key, get_request_id

logger = logging.getLogger(__name__)


class JwtAuditMiddleware(MiddlewareMixin):
    """Imposta le GUC ``app.jwt_user`` e ``app.current_user_id`` sulla
    connessione PostgreSQL.

    ``SET LOCAL`` ha scope transazione: si resetta automaticamente
    al COMMIT/ROLLBACK senza rischio di leak tra request.

    Il trigger ``script.trgfn_audit_data_user_generic`` legge
    ``app.jwt_user`` per popolare ``user_insert`` / ``user_update``
    con lo user JWT reale. ``app.current_user_id`` e' usato dai
    trigger defense-in-depth per verificare lo scope emittente.

    Per le richieste ``/api/``, rifiuta immediatamente gli utenti con
    ``ruolo_sistema = DISABILITATO`` restituendo 403.
    """

    def process_view(
        self,
        request: HttpRequest,
        view_func: object,
        view_args: tuple,
        view_kwargs: dict,
    ) -> HttpResponse | None:
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            username = str(user)
            user_id = str(user.id)
            with connection.cursor() as cursor:
                # Scopo: Propaga username e user_id come GUC PostgreSQL
                # per audit e defense-in-depth.
                cursor.execute("SET LOCAL app.jwt_user = %s", [username])
                cursor.execute(
                    "SELECT set_config('app.current_user_id', %s, true)",
                    [user_id],
                )

            # Scopo: Rifiuta immediatamente utenti DISABILITATO (early rejection).
            # Pre-carica cache permessi da Redis L2; sara' riusata
            # da ZeroERPPermission._get_cache() senza query aggiuntive.
            if request.path.startswith("/api/"):
                if not hasattr(request, "_zeroerp_perms_cache"):
                    redis_data = load_user_cache(user.id)
                    request._zeroerp_perms_cache = redis_data or {}  # type: ignore[attr-defined]
                    request._zeroerp_perms_cache_loaded_from_redis = redis_data is not None  # type: ignore[attr-defined]
                ruolo = PermissionResolver.get_ruolo_sistema(
                    user, cache=request._zeroerp_perms_cache  # type: ignore[attr-defined]
                )
                if ruolo == "DISABILITATO":
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

        return None
