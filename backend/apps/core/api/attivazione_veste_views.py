# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le due view pubbliche dell'attivazione di una veste — verifica del
#        token e conferma — scritte UNA volta per tutte le porte (building
#        block `invito_veste`, L-3). Le view di operatore, portale e shop
#        sono sottoclassi che dichiarano la porta e i messaggi: prima erano
#        tre copie (portale e shop all'80%, l'operatore senza il flusso con
#        un clic e senza accendere la veste).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import password_digitata
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import ConfermaTokenRateThrottle
from apps.core.services.invito_veste import (
    PortaInvito,
    attiva_veste,
    richiede_password,
    risolvi_token,
)
from apps.core.services.request_context import get_client_ip, richiesta_django

_VALIDATE_RESP = inline_serializer(
    name="AttivazioneVesteValidateResp",
    fields={
        "data": inline_serializer(
            name="AttivazioneVesteValidateData",
            fields={
                "valid": serializers.BooleanField(),
                "token_type": serializers.CharField(required=False),
                "requires_password": serializers.BooleanField(required=False),
                "message": serializers.CharField(required=False),
            },
        ),
    },
)
_ATTIVA_REQ = inline_serializer(
    name="AttivazioneVesteReq",
    fields={
        "token": serializers.CharField(),
        # Obbligatori solo quando la validazione dice `requires_password`.
        "new_password": serializers.CharField(required=False),
        "new_password_confirm": serializers.CharField(required=False),
    },
)
_ATTIVA_RESP = inline_serializer(
    name="AttivazioneVesteResp",
    fields={
        "data": inline_serializer(
            name="AttivazioneVesteData",
            fields={
                "message": serializers.CharField(),
                "token_type": serializers.CharField(),
            },
        ),
    },
)


class AttivazioneVesteValidateView(APIView):
    """GET: il token della porta vale ancora? (senza consumarlo). Dice alla
    pagina quale forma mostrare: scelta della password o conferma con un clic.
    Base astratta: le sottoclassi fissano `porta`."""

    permission_classes = [AllowAny]
    authentication_classes = []
    porta: PortaInvito | None = None

    @extend_schema(summary="Verifica il token di attivazione di una veste", responses={200: _VALIDATE_RESP})
    # Scopo: `requires_password` lo decide la credenziale ADESSO
    # (`richiede_password`), la stessa domanda che fara' la conferma.
    def get(self, request: Request, token: str) -> JsonResponse:
        porta = self.porta
        if porta is None:
            raise RuntimeError("AttivazioneVesteValidateView e' astratta: fissare `porta`")
        risolto = risolvi_token(porta, token)
        if risolto is None:
            return success_response({
                "valid": False,
                "message": "Token non valido, scaduto o gia' utilizzato.",
            })
        auth_user_id, _, token_type = risolto
        return success_response({
            "valid": True,
            "token_type": token_type,
            "requires_password": richiede_password(porta, token_type, auth_user_id),
        })


class AttivazioneVesteView(APIView):
    """POST: attiva la veste dell'invito (consuma il token, accende la veste,
    e nel flusso con password la imposta). Base astratta: le sottoclassi
    fissano `porta` e i due messaggi di esito."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ConfermaTokenRateThrottle]
    porta: PortaInvito | None = None
    messaggio_con_password: str = "Accesso attivato. Effettua il login con la nuova password."  # noqa: S105 — testo del messaggio, non una password
    messaggio_cross: str = "Accesso attivato. Effettua il login con le tue credenziali esistenti."

    @extend_schema(summary="Attivazione di una veste (con password o con un clic)", request=_ATTIVA_REQ, responses={200: _ATTIVA_RESP})
    def post(self, request: Request) -> JsonResponse:
        porta = self.porta
        if porta is None:
            raise RuntimeError("AttivazioneVesteView e' astratta: fissare `porta`")

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            esito = attiva_veste(
                porta,
                token=(payload.get("token") or "").strip(),
                new_password=password_digitata(payload, "new_password"),
                new_password_confirm=password_digitata(payload, "new_password_confirm"),
                ip=get_client_ip(richiesta_django(request)),
            )
            return {
                "message": self.messaggio_cross if esito.is_cross else self.messaggio_con_password,
                "token_type": esito.token_type,
            }

        return handle_post_json(request, handler=_handler)
