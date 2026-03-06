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
            # Estrae user_id e jti dal token emesso
            user_id = self._extract_user_id(request)
            jti = response.data.get("access", "")
            # Il jti reale e' nel claim del token; per ora loggiamo senza decodifica
            session_audit_service.record_login(
                user_id=user_id,
                request=request._request,
                jti=None,
            )
        return response

    @staticmethod
    # Scopo: Estrae l'auth_user_id dalla request dopo autenticazione SimpleJWT.
    def _extract_user_id(request: Request) -> int:
        # Dopo il post() con successo, SimpleJWT valida le credenziali
        # e mette lo user nel serializer. Usiamo il campo username dal body.
        from django.contrib.auth import get_user_model
        User = get_user_model()
        username = request.data.get("username", "")
        try:
            return User.objects.values_list("id", flat=True).get(username=username)
        except User.DoesNotExist:
            return 0


class AuditTokenRefreshView(TokenRefreshView):
    """Override di TokenRefreshView: dopo refresh con successo registra evento REFRESH."""

    # Scopo: Esegue il refresh JWT e registra l'evento REFRESH in dbops.sessioni_utente.
    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Nel refresh non abbiamo lo user autenticato nella request;
            # decodifichiamo il refresh token per ottenere user_id.
            user_id = self._extract_user_id_from_refresh(request)
            session_audit_service.record_refresh(
                user_id=user_id,
                request=request._request,
                jti=None,
            )
        return response

    @staticmethod
    # Scopo: Estrae l'auth_user_id dal refresh token nel body della request.
    def _extract_user_id_from_refresh(request: Request) -> int:
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh_str = request.data.get("refresh", "")
        if not refresh_str:
            return 0
        try:
            token = RefreshToken(refresh_str)
            return int(token.get("user_id", 0))
        except Exception:
            return 0
