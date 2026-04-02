# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint attivazione account operatore invitato:
#        1. GET  /attivazione-validate/{token}/ — verifica token invito
#        2. POST /attivazione/ — consuma token, imposta password scelta
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import PasswordResetRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_helpers import apply_new_password, validate_and_extract_token
from apps.core.services.error_manager import ErrorManager
from apps.core.services.request_context import get_client_ip
from apps.core.services.token_service import TokenService

logger = logging.getLogger("security")

E_ATTIVAZIONE = "E_ATTIVAZIONE"
_INVITO_TOKEN_TIPO = "INVITO_OPERATORE"

_auth_repo = AuthRepository()
_token_service = TokenService()


class AttivazioneValidateView(APIView):
    """GET: verifica se un token invito operatore e' ancora valido (senza consumarlo)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(summary="Verifica token invito operatore", responses={200: dict})
    # Scopo: Verifica validita' token invito senza consumarlo. Usato dal frontend
    #        per mostrare il form di attivazione o un messaggio di errore/scadenza.
    def get(self, request: Request, token: str) -> JsonResponse:
        result = _token_service.validate(token, _INVITO_TOKEN_TIPO)
        if result:
            return success_response({"valid": True})
        return success_response({"valid": False, "message": "Token non valido, scaduto o gia' utilizzato."})


class AttivazioneView(APIView):
    """POST: attivazione account operatore con token invito + nuova password."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(summary="Attivazione account operatore", responses={200: dict})
    # Scopo: Consuma token invito, imposta password scelta dall'operatore,
    #        resetta flag deve_cambiare_password. L'operatore deve poi fare login.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            token = (payload.get("token") or "").strip()
            new_password = (payload.get("new_password") or "").strip()
            new_password_confirm = (payload.get("new_password_confirm") or "").strip()

            ErrorManager.require(bool(token), code=E_ATTIVAZIONE, message="Token obbligatorio.")
            ErrorManager.require(bool(new_password), code=E_ATTIVAZIONE, message="Nuova password obbligatoria.")
            ErrorManager.require(
                new_password == new_password_confirm,
                code=E_ATTIVAZIONE, message="La nuova password e la conferma non coincidono.",
            )

            # Valida token SENZA consumarlo
            auth_user_id, _ = validate_and_extract_token(
                token, _INVITO_TOKEN_TIPO, E_ATTIVAZIONE, _token_service,
            )

            # Trova utente
            user = User.objects.filter(id=auth_user_id).first()
            ErrorManager.require(user is not None, code=E_ATTIVAZIONE, message="Utente non trovato.")
            assert user is not None

            # Valida password PRIMA di consumare il token
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as exc:
                ErrorManager.require(False, code=E_ATTIVAZIONE, message=" ".join(exc.messages))

            # Consuma token + applica password + reset flag (atomico, senza blacklist)
            ip = get_client_ip(request._request if hasattr(request, "_request") else request)
            with transaction.atomic():
                _token_service.consume(token, _INVITO_TOKEN_TIPO, ip=ip)
                apply_new_password(user, new_password, blacklist_tokens=False, auth_repo=_auth_repo)

            logger.info("security.account_attivato user_id=%s", auth_user_id)
            return {"message": "Account attivato con successo. Effettua il login con la nuova password."}

        return handle_post_json(request, handler=_handler)
