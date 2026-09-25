# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Middleware che blocca la navigazione API se l'operatore
#        ha il flag deve_cambiare_password attivo.
#        Endpoint consentiti: change-password, logout, me.
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.db.auth_repository import AuthRepository
from apps.core.services.request_context import get_request_id

logger = logging.getLogger(__name__)

# Singleton repository (stateless)
_auth_repo = AuthRepository()

# Path consentiti anche quando deve_cambiare_password = true.
# Nota: §8.3.1 ha rinominato solo /api/v1/auth/token/ → /api/v1/admin/token/;
# gli altri endpoint auth (logout, change-password, password-reset-*) restano
# sotto /api/v1/auth/ finche' il piano PR-B non affronta anche il loro rename.
_ALLOWED_PATHS = frozenset({
    "/api/v1/auth/change-password/",
    "/api/v1/auth/logout/",
    "/api/v1/core/me/",
})


class PasswordChangeRequiredMiddleware(MiddlewareMixin):
    """Blocca tutte le API tranne change-password, logout e me
    se l'operatore deve cambiare password."""

    # Scopo: Intercetta request API e ritorna 403 se il flag e' attivo.
    def process_view(self, request: HttpRequest, callback, callback_args, callback_kwargs):
        path = request.path

        # Solo path /api/ (escludi admin, static, docs, schema)
        if not path.startswith("/api/v1/"):
            return None

        # Skip path consentiti
        if path in _ALLOWED_PATHS:
            return None

        # Solo utenti autenticati
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return None

        # Superuser bypassa
        if user.is_superuser:
            return None

        # Leggi flag dal DB: e' della credenziale (D-7), non della veste.
        # ⚠️ Col JWT questo punto oggi non viene raggiunto (A-8: a
        # process_view `request.user` e' ancora anonimo): lo sposta L-6.
        try:
            if _auth_repo.get_deve_cambiare_password(user.id):
                meta = {}
                request_id = get_request_id()
                if request_id:
                    meta["request_id"] = request_id
                return JsonResponse(
                    {
                        "error": {
                            "code": "E_CAMBIO_PASSWORD_RICHIESTO",
                            "message": "Devi cambiare la password prima di procedere.",
                        },
                        "meta": meta,
                    },
                    status=403,
                )
        except Exception:
            # Fail-closed: se il DB non risponde, blocca per sicurezza
            logger.exception("Errore check deve_cambiare_password per user_id=%s — blocco per sicurezza", user.id)
            return JsonResponse(
                {
                    "error": {
                        "code": "E_CAMBIO_PASSWORD_CHECK_FALLITO",
                        "message": "Impossibile verificare lo stato delle credenziali. Riprova.",
                    },
                },
                status=503,
            )

        return None
