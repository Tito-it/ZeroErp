# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views matrice indirizzi per ruolo.
#        Lista paginata con filtro ruolo, creazione, dettaglio, aggiornamento.
#        Pattern allineato a views_fornitori.py.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int, paginated_envelope, parse_list_params
from apps.core.api.success_responses import success_response
from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService


# =================================================================
# Matrice indirizzi lista + crea
# =================================================================

class MatriceIndirizziView(DomainAPIView):
    """GET lista paginata, POST crea regola matrice."""
    area_funzionale = "anagrafiche"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca su descrizione ruolo o tipo indirizzo"),
            OpenApiParameter(name="tipo_ruolo_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="MatriceIndirizziListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata matrice indirizzi per ruolo con filtro tipo_ruolo_id.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="tipo_ruolo_descrizione")
        tipo_ruolo_id = optional_int({"v": request.query_params.get("tipo_ruolo_id")}, "v")
        svc = MatriceIndirizziService()
        results, total = svc.list_regole(
            search=p["search"],
            tipo_ruolo_id=tipo_ruolo_id,
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="MatriceIndirizziCreateReq", fields={
            "tipo_ruolo_id": serializers.IntegerField(),
            "tipo_indirizzo_id": serializers.IntegerField(),
            "obbligatorio": serializers.BooleanField(required=False),
            "fallback_tipo_indirizzo_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="MatriceIndirizziCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea regola matrice (valido_dal = oggi, attivo = true).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=MatriceIndirizziService().crea_regola)


# =================================================================
# Matrice indirizzi dettaglio
# =================================================================

class MatriceIndirizziDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna regola."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        responses={200: inline_serializer(name="MatriceIndirizziDetailResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Dettaglio regola matrice.
    def get(self, request: Request, regola_id: int) -> JsonResponse:
        svc = MatriceIndirizziService()
        data = svc.get_regola(regola_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(name="MatriceIndirizziUpdateReq", fields={
            "obbligatorio": serializers.BooleanField(required=False),
            "fallback_tipo_indirizzo_id": serializers.IntegerField(required=False, allow_null=True),
            "attivo": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(name="MatriceIndirizziUpdateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Aggiorna regola matrice (obbligatorio, fallback, attivo).
    def patch(self, request: Request, regola_id: int) -> JsonResponse:
        svc = MatriceIndirizziService()
        result = svc.update_regola(regola_id, request.data)
        return success_response(result)
