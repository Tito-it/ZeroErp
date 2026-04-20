# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint admin-side per invitare al portale un cliente o un
#        fornitore. Vive in `apps/anagrafiche` per coerenza con il CRUD
#        dei rispettivi domini, ma delega al service `InvitoPortaleService`
#        dell'app portale (single source of truth).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.portale.services.invito_portale_service import InvitoPortaleService


class ClientiInvitaPortaleView(DomainAPIView):
    """POST admin: invita al portale il cliente (billing_account) indicato."""

    area_funzionale = "anagrafiche"

    @extend_schema(
        summary="Invita un cliente al portale",
        request=inline_serializer(
            name="ClienteInvitaPortaleReq",
            fields={
                "email": serializers.CharField(
                    help_text="Email destinatario. Il sistema crea "
                    "auth_user+identita se mancanti."
                ),
                "reinvio": serializers.BooleanField(
                    required=False,
                    help_text="Se true, invalida token precedenti prima di "
                    "generare il nuovo invito.",
                ),
            },
        ),
        responses={200: inline_serializer(
            name="ClienteInvitaPortaleResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Admin-only endpoint per invitare un cliente al portale.
    #        Input: email destinatario + flag reinvio. Delega al service.
    def post(self, request: Request, cliente_id: int) -> JsonResponse:
        service = InvitoPortaleService()

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            email = str(payload.get("email") or "")
            reinvio = bool(payload.get("reinvio") or False)
            fn = (
                service.reinvia_invito_cliente
                if reinvio
                else service.invia_invito_cliente
            )
            return fn(
                cliente_id=cliente_id,
                email=email,
                invitato_da_user_id=request.user.id,
            )

        return handle_post_json(request, handler=_handler)


class FornitoriInvitaPortaleView(DomainAPIView):
    """POST admin: invita al portale il fornitore indicato."""

    area_funzionale = "anagrafiche"

    @extend_schema(
        summary="Invita un fornitore al portale",
        request=inline_serializer(
            name="FornitoreInvitaPortaleReq",
            fields={
                "email": serializers.CharField(),
                "reinvio": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="FornitoreInvitaPortaleResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Admin-only endpoint per invitare un fornitore al portale.
    def post(self, request: Request, fornitore_id: int) -> JsonResponse:
        service = InvitoPortaleService()

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            email = str(payload.get("email") or "")
            reinvio = bool(payload.get("reinvio") or False)
            fn = (
                service.reinvia_invito_fornitore
                if reinvio
                else service.invia_invito_fornitore
            )
            return fn(
                fornitore_id=fornitore_id,
                email=email,
                invitato_da_user_id=request.user.id,
            )

        return handle_post_json(request, handler=_handler)
