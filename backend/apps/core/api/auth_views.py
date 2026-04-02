# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Override delle view SimpleJWT per agganciare:
#   - Logging sessioni utente (login/refresh) in dbops.sessioni_utente
#   - Throttling login per IP (LoginRateThrottle)
#   - Blocco per utente dopo tentativi falliti (fn_check_blocco_login,
#     fn_registra_tentativo_login)
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.api.throttling import LoginRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.services import session_audit_service

logger = logging.getLogger("security")
_auth_repo = AuthRepository()


class AuditTokenObtainPairView(TokenObtainPairView):
    """Override di TokenObtainPairView con:
    - Throttle per IP (5 tentativi / 5 minuti)
    - Blocco per utente (DB: tentativi_falliti + bloccato_fino_a)
    - Audit login in dbops.sessioni_utente
    """

    throttle_classes = [LoginRateThrottle]

    @extend_schema(summary="Login JWT con audit e blocco utente", responses={200: dict})
    # Scopo: Esegue il login JWT con check blocco utente e registrazione tentativi.
    # Flusso: check blocco → verifica credenziali → registra esito → audit sessione.
    def post(self, request: Request, *args, **kwargs) -> Response:
        username = request.data.get("username", "")
        user = self._find_user(username)

        # 1. Se utente esiste, verifica blocco (lancia errore DB se bloccato)
        if user:
            try:
                _auth_repo.check_blocco_login(user.id)
            except Exception as exc:
                # L'errore DB viene propagato al middleware che lo converte in JSON
                logger.warning("security.login_blocked user=%s", username)
                raise

        # 2. Tenta login (SimpleJWT)
        try:
            response = super().post(request, *args, **kwargs)
        except (AuthenticationFailed, InvalidToken):
            # Login fallito: registra tentativo
            if user:
                result = _auth_repo.registra_tentativo_login(user.id, successo=False)
                if result.get("bloccato"):
                    logger.warning(
                        "security.login_locked user=%s tentativi=%s blocco_minuti=%s",
                        username, result.get("tentativi"), result.get("minuti_rimanenti"),
                    )
            raise

        # 3. Login OK: reset contatore + audit sessione + check cambio password
        if response.status_code == 200:
            if user:
                _auth_repo.registra_tentativo_login(user.id, successo=True)

                # Check flag deve_cambiare_password
                if _auth_repo.get_deve_cambiare_password(user.id):
                    response.data["password_change_required"] = True

            user_id, jti = self._extract_claims(response)
            session_audit_service.record_login(
                user_id=user_id,
                request=request._request if hasattr(request, "_request") else request,
                jti=jti,
            )

        return response

    @staticmethod
    # Scopo: Trova user Django per username (best-effort, non lancia errore).
    def _find_user(username: str) -> User | None:
        if not username:
            return None
        try:
            return User.objects.filter(username=username).first()
        except Exception:
            return None

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

    @extend_schema(summary="Refresh JWT con audit sessione", responses={200: dict})
    # Scopo: Esegue il refresh JWT e registra l'evento REFRESH in dbops.sessioni_utente.
    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user_id, jti = self._extract_claims(request)
            session_audit_service.record_refresh(
                user_id=user_id,
                request=request._request if hasattr(request, "_request") else request,
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
