# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Override delle view SimpleJWT per agganciare il logging
#        delle sessioni utente (login e refresh) nella tabella
#        dbops.sessioni_utente tramite session_audit_service.
# ------------------------------------------------------------

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.services import session_audit_service


class AuditTokenObtainPairView(TokenObtainPairView):
    """Override di TokenObtainPairView: dopo login con successo registra evento LOGIN."""

    # Scopo: Esegue il login JWT e registra l'evento LOGIN in dbops.sessioni_utente.
    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user_id, jti = self._extract_claims(response)
            session_audit_service.record_login(
                user_id=user_id,
                request=request._request,
                jti=jti,
            )
        return response

    @staticmethod
    # Scopo: Estrae user_id e sid dal refresh token nella response (no query DB extra).
    def _extract_claims(response: Response) -> tuple[int, str | None]:
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh_str = response.data.get("refresh", "")
        if not refresh_str:
            return 0, None
        try:
            token = RefreshToken(refresh_str)
            return int(token.get("user_id", 0)), str(token.get("sid", ""))
        except Exception:
            return 0, None


class AuditTokenRefreshView(TokenRefreshView):
    """Override di TokenRefreshView: dopo refresh con successo registra evento REFRESH."""

    # Scopo: Esegue il refresh JWT e registra l'evento REFRESH in dbops.sessioni_utente.
    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user_id, jti = self._extract_claims(request)
            session_audit_service.record_refresh(
                user_id=user_id,
                request=request._request,
                jti=jti,
            )
        return response

    @staticmethod
    # Scopo: Estrae user_id e sid dal refresh token nel body della request.
    def _extract_claims(request: Request) -> tuple[int, str | None]:
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh_str = request.data.get("refresh", "")
        if not refresh_str:
            return 0, None
        try:
            token = RefreshToken(refresh_str)
            return int(token.get("user_id", 0)), str(token.get("sid", ""))
        except Exception:
            return 0, None
