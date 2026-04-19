# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint namespace `/api/v1/portale/*` — flussi auth portale
#        (attivazione invito) + futuri endpoint MVP (me, billing-account,
#        fatture, scadenze, ordini-ricevuti, pagamenti). Gli endpoint
#        pubblici (attivazione-validate + attivazione) non richiedono JWT
#        e usano AllowAny. Gli endpoint autenticati usano PortaleAPIView.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import PasswordResetRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_helpers import (
    apply_new_password,
    validate_and_extract_token,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.request_context import get_client_ip
from apps.core.services.token_service import TokenService
from apps.portale.services.invito_portale_service import (
    INVITO_PORTALE_TOKEN_TIPO,
)

logger = logging.getLogger("security")

E_ATTIVAZIONE_PORTALE = "E_ATTIVAZIONE_PORTALE"

_auth_repo = AuthRepository()
_token_service = TokenService()


class AttivazionePortaleValidateView(APIView):
    """GET: verifica se un token invito portale e' ancora valido (no consume)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Verifica token invito portale",
        responses={200: inline_serializer(
            name="AttivazionePortaleValidateResp",
            fields={
                "data": inline_serializer(
                    name="AttivazionePortaleValidateData",
                    fields={
                        "valid": serializers.BooleanField(),
                        "message": serializers.CharField(required=False),
                    },
                ),
            },
        )},
    )
    # Scopo: Usato dal frontend per mostrare il form di attivazione o un
    #        messaggio di errore/scadenza prima di chiedere la password.
    def get(self, request: Request, token: str) -> JsonResponse:
        result = _token_service.validate(token, INVITO_PORTALE_TOKEN_TIPO)
        if result:
            return success_response({"valid": True})
        return success_response({
            "valid": False,
            "message": "Token non valido, scaduto o gia' utilizzato.",
        })


class AttivazionePortaleView(APIView):
    """POST: attivazione portale user con token invito + nuova password."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(
        summary="Attivazione portale cliente/fornitore",
        request=inline_serializer(
            name="AttivazionePortaleReq",
            fields={
                "token": serializers.CharField(),
                "new_password": serializers.CharField(),
                "new_password_confirm": serializers.CharField(),
            },
        ),
        responses={200: inline_serializer(
            name="AttivazionePortaleResp",
            fields={
                "data": inline_serializer(
                    name="AttivazionePortaleData",
                    fields={"message": serializers.CharField()},
                ),
            },
        )},
    )
    # Scopo: Consuma il token INVITO_PORTALE, imposta la password scelta,
    #        resetta il flag deve_cambiare_password sull'identita attiva.
    #        L'utente dovra' poi fare login esplicito.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            token = (payload.get("token") or "").strip()
            new_password = (payload.get("new_password") or "").strip()
            new_password_confirm = (payload.get("new_password_confirm") or "").strip()

            ErrorManager.require(
                bool(token),
                code=E_ATTIVAZIONE_PORTALE,
                message="Token obbligatorio.",
            )
            ErrorManager.require(
                bool(new_password),
                code=E_ATTIVAZIONE_PORTALE,
                message="Nuova password obbligatoria.",
            )
            ErrorManager.require(
                new_password == new_password_confirm,
                code=E_ATTIVAZIONE_PORTALE,
                message="La nuova password e la conferma non coincidono.",
            )

            # Valida token SENZA consumarlo (coerente con attivazione operatore).
            auth_user_id, _ = validate_and_extract_token(
                token,
                INVITO_PORTALE_TOKEN_TIPO,
                E_ATTIVAZIONE_PORTALE,
                _token_service,
            )

            user = User.objects.filter(id=auth_user_id).first()
            ErrorManager.require(
                user is not None,
                code=E_ATTIVAZIONE_PORTALE,
                message="Utente non trovato.",
            )
            assert user is not None

            # Valida password prima di consumare il token (altrimenti un
            # errore di policy renderebbe l'invito usa-e-getta in un colpo).
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as exc:
                ErrorManager.require(
                    False,
                    code=E_ATTIVAZIONE_PORTALE,
                    message=" ".join(exc.messages),
                )

            ip = get_client_ip(
                request._request if hasattr(request, "_request") else request
            )
            # Consume token + applica password + reset flag deve_cambiare.
            # blacklist_tokens=False: il portale user non ha ancora sessioni
            # attive da invalidare (primo accesso).
            with transaction.atomic():
                _token_service.consume(token, INVITO_PORTALE_TOKEN_TIPO, ip=ip)
                apply_new_password(
                    user,
                    new_password,
                    blacklist_tokens=False,
                    auth_repo=_auth_repo,
                )

            logger.info(
                "security.portale_attivato user_id=%s", auth_user_id
            )
            return {
                "message": (
                    "Account portale attivato con successo. "
                    "Effettua il login con la nuova password."
                )
            }

        return handle_post_json(request, handler=_handler)
