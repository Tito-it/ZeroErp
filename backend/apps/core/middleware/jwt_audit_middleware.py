# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Propaga lo user JWT come GUC PostgreSQL per audit reale.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin


class JwtAuditMiddleware(MiddlewareMixin):
    """Imposta la GUC ``app.jwt_user`` sulla connessione PostgreSQL.

    ``SET LOCAL`` ha scope transazione: si resetta automaticamente
    al COMMIT/ROLLBACK senza rischio di leak tra request.

    Il trigger ``script.trgfn_audit_data_user_generic`` legge questa
    variabile per popolare ``user_insert`` / ``user_update`` con lo
    user JWT reale. Fallback a ``CURRENT_USER`` se non impostata.
    """

    def process_view(
        self,
        request: HttpRequest,
        view_func: object,
        view_args: tuple,
        view_kwargs: dict,
    ) -> None:
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            username = str(user)
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.jwt_user = %s", [username])
        return None
