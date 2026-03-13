# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint POST /api/v1/auth/logout/ — blacklista il refresh token
#        corrente e registra evento LOGOUT in dbops.sessioni_utente.
# ------------------------------------------------------------

from __future__ import annotations

import jwt
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api.permissions import ZeroERPPermission
from apps.core.services import session_audit_service
from apps.core.services.service_errors import ServiceError


class LogoutView(APIView):
    """Logout utente: blacklist refresh token + evento LOGOUT."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    skip_area_check = True

    @extend_schema(summary="Logout utente", responses={204: None})
    # Scopo: Blacklista il refresh token corrente e registra evento LOGOUT.
    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            raise ServiceError(
                code="E_LOGOUT_NO_TOKEN",
                message="Refresh token richiesto per il logout.",
            )

        # Estrai sid dal payload senza validare scadenza/blacklist,
        # cosi' il logout viene sempre registrato.
        sid = ""
        try:
            payload = jwt.decode(
                refresh_token, options={"verify_exp": False, "verify_signature": False}
            )
            sid = payload.get("sid", "")
        except Exception:
            pass

        # Blacklista il token; se gia' scaduto/blacklistato, prosegui comunque.
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass

        # Registra sempre l'evento LOGOUT (anche se il token era scaduto).
        if sid:
            session_audit_service.record_logout(
                user_id=request.user.id,
                request=request._request,
                jti=sid,
            )
        return Response(status=204)
