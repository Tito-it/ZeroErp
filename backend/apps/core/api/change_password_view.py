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
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.db.auth_repository import AuthRepository
from apps.core.services import session_audit_service
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
    def post(self, request: Request) -> success_response:
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

            # Operazioni atomiche: password + flag + blacklist
            with transaction.atomic():
                user.set_password(new_password)
                user.save(update_fields=["password"])
                _auth_repo.set_deve_cambiare_password(user.id, False)

                # Blacklista refresh token precedenti
                for ot in OutstandingToken.objects.filter(user=user):
                    try:
                        RefreshToken(ot.token).blacklist()
                    except TokenError:
                        pass

            # Genera nuova coppia JWT (fuori dalla transazione — non critico)
            refresh = RefreshToken.for_user(user)

            # Audit
            session_audit_service.record_login(
                user_id=user.id,
                request=request._request,
                jti=str(refresh.get("sid", refresh.get("jti", ""))),
            )
            logger.info("security.password_changed user_id=%s", user.id)

            return {"access": str(refresh.access_token), "refresh": str(refresh)}

        return handle_post_json(request, handler=_handler)
