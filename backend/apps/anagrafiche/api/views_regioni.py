# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views regioni — view sottili, logica nel service.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.openapi_params import param_ricerca_full, parametri_ordinamento
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    parse_list_params,
    qp_int_optional,
)
from apps.core.api.success_responses import success_response
from apps.anagrafiche.services.geo_service import GeoService
from apps.core.services.list_helpers import pagina_con_totale


class RegioniView(DomainAPIView):
    """GET lista, POST crea."""

    lista_codice = "config.regioni"

    area_funzionale = "anagrafiche"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="stato_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            *parametri_ordinamento(),
        ],
        responses={200: inline_serializer(name="RegioniListResp", fields={"data": serializers.DictField()})},
    )
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="descrizione")
        stato_id = qp_int_optional(request.query_params.get("stato_id"), "stato_id", min_val=0)
        svc = GeoService()
        results, total = svc.list_regioni(
            search=p["search"], stato_id=stato_id,
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(pagina_con_totale(results, total))

    @extend_schema(
        request=inline_serializer(name="RegioniCreateReq", fields={
            "descrizione": serializers.CharField(),
            "stato_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="RegioniCreateResp", fields={"data": serializers.DictField()})},
    )
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=GeoService().create_regione)


class RegioniDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna."""
    area_funzionale = "anagrafiche"

    @extend_schema(responses={200: inline_serializer(name="RegioneDetailResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, pk: int) -> JsonResponse:
        return success_response(GeoService().get_regione(pk))

    @extend_schema(
        request=inline_serializer(name="RegioniUpdateReq", fields={
            "descrizione": serializers.CharField(required=False),
            "stato_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="RegioniUpdateResp", fields={"data": serializers.DictField()})},
    )
    def patch(self, request: Request, pk: int) -> JsonResponse:
        return success_response(GeoService().update_regione(pk, corpo_oggetto(request)))


class RegioniLookupView(DomainAPIView):
    """GET lista per dropdown."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        parameters=[OpenApiParameter(name="stato_id", type=int, required=False)],
        responses={200: inline_serializer(name="RegioniLookupResp", fields={"data": serializers.DictField()})},
    )
    def get(self, request: Request) -> JsonResponse:
        stato_id = qp_int_optional(request.query_params.get("stato_id"), "stato_id", min_val=0)
        return success_response({"results": GeoService().lookup_regioni(stato_id=stato_id)})
