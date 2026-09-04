# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint POST /api/v1/auth/change-password/ — cambio password
#        con validazione (vecchia password + 4 validators Django).
#        Resetta flag deve_cambiare_password, blacklista token precedenti,
#        genera nuova coppia JWT.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.db.auth_repository import AuthRepository
from apps.core.services import session_audit_service
from apps.core.services.auth_constants import JWT_CLAIM_SID
from apps.core.services.auth_helpers import (
    apply_new_password,
    extract_identita_id_from_request,
)
from apps.core.services.error_manager import ErrorManager

logger = logging.getLogger("security")

E_CHANGE_PW = "E_CHANGE_PASSWORD"
_auth_repo = AuthRepository()


class ChangePasswordView(DomainAPIView):
    """Cambio password: valida vecchia, applica nuova, resetta flag, rigenera token."""

    skip_area_check = True

    @extend_schema(summary="Cambio password", responses={200: dict})
    # Scopo: Cambio password con validazione completa. Obiettivo: permettere
    #        all'operatore di cambiare la propria password (sia volontario
    #        che obbligatorio al primo accesso). Resetta flag, invalida
    #        sessioni precedenti, ritorna nuovi token JWT in envelope standard.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            user = request.user

            old_password = (payload.get("old_password") or "").strip()
            new_password = (payload.get("new_password") or "").strip()
            new_password_confirm = (payload.get("new_password_confirm") or "").strip()

            # Validazioni input
            ErrorManager.require(bool(old_password), code=E_CHANGE_PW, message="Password attuale obbligatoria.")
            ErrorManager.require(bool(new_password), code=E_CHANGE_PW, message="Nuova password obbligatoria.")
            ErrorManager.require(
                new_password == new_password_confirm,
                code=E_CHANGE_PW, message="La nuova password e la conferma non coincidono.",
            )
            ErrorManager.require(
                new_password != old_password,
                code=E_CHANGE_PW, message="La nuova password deve essere diversa dalla precedente.",
            )

            # Verifica password attuale
            ErrorManager.require(
                user.check_password(old_password),
                code=E_CHANGE_PW, message="Password attuale non corretta.",
            )

            # Validazione Django (4 validators: lunghezza, complessita', ecc.)
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as exc:
                ErrorManager.require(False, code=E_CHANGE_PW, message=" ".join(exc.messages))

            # Reset flag deve_cambiare_password puntato sulla veste del
            # JWT corrente (§8.3.2+§8.4.1). None solo con token pre-refactor
            # → fallback globale accettabile (blacklist invalida comunque).
            identita_id = extract_identita_id_from_request(request)

            # Operazioni atomiche: password + flag + blacklist
            apply_new_password(
                user,
                new_password,
                identita_id=identita_id,
                blacklist_tokens=True,
                auth_repo=_auth_repo,
            )

            # Genera nuova coppia JWT (fuori dalla transazione — non critico)
            refresh = RefreshToken.for_user(user)

            # Audit
            session_audit_service.record_login(
                user_id=user.id,
                request=request._request if hasattr(request, "_request") else request,
                jti=str(refresh.get(JWT_CLAIM_SID, refresh.get("jti", ""))),
            )
            logger.info("security.password_changed user_id=%s", user.id)

            return {"access": str(refresh.access_token), "refresh": str(refresh)}

        return handle_post_json(request, handler=_handler)
