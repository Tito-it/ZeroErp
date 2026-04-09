# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: View API per l'assistente AI.
#        Endpoint POST /api/v1/ai-assistant/query/ per query
#        in linguaggio naturale con function calling.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.core.api.base_views import DomainAPIView
from apps.core.api.jwt_audit_authentication import JwtAuditAuthentication
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager


class AIStatusView(APIView):
    """Health check per verificare se l'AI e' attiva e disponibile.

    Usa JWT semplice senza check area_funzionale: tutti gli utenti
    autenticati possono verificare se l'AI e' attiva.
    Il check permessi area avviene solo su /query/.
    """

    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="AIStatusResponse",
                fields={
                    "data": inline_serializer(
                        name="AIStatusData",
                        fields={
                            "enabled": serializers.BooleanField(),
                            "provider": serializers.CharField(),
                            "tools_available": serializers.IntegerField(),
                        },
                    ),
                },
            ),
        },
    )
    # Scopo: Restituisce lo stato dell'assistente AI.
    #        Health check leggero: nessuna query DB, solo config statica.
    def get(self, request: Request) -> JsonResponse:
        from apps.ai_assistant.services.tool_registry import get_all_tools

        return success_response({
            "enabled": getattr(settings, "AI_ENABLED", False),
            "provider": getattr(settings, "AI_PROVIDER", "mock"),
            "tools_available": len(get_all_tools()),
        })


class AIQueryView(DomainAPIView):
    """Endpoint principale per query AI in linguaggio naturale.

    Riceve un messaggio dall'utente, lo invia al provider AI con il
    catalogo strumenti, esegue le tool_call e restituisce la risposta.
    """

    area_funzionale = "ai_assistant"

    @extend_schema(
        request=inline_serializer(
            name="AIQueryRequest",
            fields={
                "message": serializers.CharField(help_text="Messaggio in linguaggio naturale"),
                "conversation_id": serializers.CharField(
                    required=False, help_text="UUID conversazione esistente (opzionale)"
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="AIQueryResponse",
                fields={
                    "data": inline_serializer(
                        name="AIQueryData",
                        fields={
                            "conversation_id": serializers.CharField(),
                            "response": serializers.CharField(),
                            "tools_used": serializers.ListField(child=serializers.CharField()),
                            "actions": serializers.ListField(child=serializers.DictField()),
                            "has_more": serializers.BooleanField(),
                        },
                    ),
                },
            ),
        },
    )
    # Scopo: Gestisce la query AI via POST.
    #        Verifica che l'AI sia attiva, poi delega al service.
    def post(self, request: Request) -> JsonResponse:
        # Guard: AI disattivata
        ErrorManager.require(
            getattr(settings, "AI_ENABLED", False),
            code="E_AI_DISABLED",
            message="Funzionalita' assistente AI non attiva.",
        )

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            from apps.ai_assistant.services import ai_assistant_service

            message = payload.get("message", "")
            conversation_id = payload.get("conversation_id")

            result = ai_assistant_service.query(
                user=request.user,
                request=request,
                message=str(message).strip(),
                conversation_id=conversation_id,
            )

            return dict(result)

        return handle_post_json(request, handler=_handler)
