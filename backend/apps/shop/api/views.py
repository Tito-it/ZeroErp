# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint namespace `/api/v1/shop/*` — stub §8.4.4/§8.4.5.
#        Il flusso reale (catalogo pubblico, registrazione cliente,
#        attivazione account shop, checkout) arriva con PR-C. Per ora gli
#        endpoint rispondono 501 con codice dedicato cosi' FE e smoke
#        e2e possono gia' cablare le rotte.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.api.error_responses import exception_to_error_response
from apps.core.services.service_errors import ServiceError


# Scopo: Helper per stub residui shop (oggi: ShopRegisterCheckEmailView).
# Centralizza il codice errore + conversione in envelope. Eliminare quando
# il flusso self-register §5.6 sostituira' anche questo stub.
# Post B1 §13.7: ShopActivateView e ProfileActivateShopView non sono piu'
# stub (vedi `views_attivazione.py` e `apps/portale/api/views.py`).
def shop_not_available_response(message: str) -> JsonResponse:
    return exception_to_error_response(ServiceError(
        code="E_SHOP_NON_DISPONIBILE",
        message=message,
    ))


# Scopo: Schema response comune agli stub 501 — serializer inline
# centralizzato per non duplicarlo in ogni @extend_schema.
_STUB_RESPONSE_SCHEMA = inline_serializer(
    name="ShopStubResp",
    fields={
        "error": inline_serializer(
            name="ShopStubErr",
            fields={
                "code": serializers.CharField(),
                "message": serializers.CharField(),
            },
        ),
    },
)


class ShopRegisterCheckEmailView(APIView):
    """POST /api/v1/shop/register/check-email/ — §8.4.5 stub.

    Il flusso reale in PR-C prendera' un'email in input e distinguera' 3
    casi: email nuova (onboarding guest → creazione auth_user + identita
    SHOP_CUSTOMER), email gia' auth_user (CROSS shop), email esistente
    gia' SHOP_CUSTOMER (login). Per ora 501 — non parsiamo neanche il
    body perche' nessuna logica dipende dall'input.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Check email per registrazione shop (stub PR-C)",
        request=inline_serializer(
            name="ShopRegisterCheckEmailReq",
            fields={"email": serializers.EmailField()},
        ),
        responses={501: _STUB_RESPONSE_SCHEMA},
    )
    def post(self, request: Request) -> JsonResponse:
        return shop_not_available_response(
            "Registrazione shop non ancora disponibile. In arrivo con PR-C."
        )
