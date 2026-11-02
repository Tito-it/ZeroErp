# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views province — view sottili, logica nel service.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import corpo_oggetto, optional_int, paginated_envelope, parse_list_params
from apps.core.api.success_responses import success_response
from apps.anagrafiche.services.geo_service import GeoService


class ProvinceView(DomainAPIView):
    """GET lista, POST crea."""
    area_funzionale = "anagrafiche"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="regione_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="ProvinceListResp", fields={"data": serializers.DictField()})},
    )
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="descrizione")
        regione_id = optional_int({"v": request.query_params.get("regione_id")}, "v")
        svc = GeoService()
        results, total = svc.list_province(
            search=p["search"], regione_id=regione_id,
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="ProvinceCreateReq", fields={
            "descrizione": serializers.CharField(),
            "sigla": serializers.CharField(),
            "regione_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="ProvinceCreateResp", fields={"data": serializers.DictField()})},
    )
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=GeoService().create_provincia)


class ProvinceDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna."""
    area_funzionale = "anagrafiche"

    @extend_schema(responses={200: inline_serializer(name="ProvinceDetailResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, pk: int) -> JsonResponse:
        return success_response(GeoService().get_provincia(pk))

    @extend_schema(
        request=inline_serializer(name="ProvinceUpdateReq", fields={
            "descrizione": serializers.CharField(required=False),
            "sigla": serializers.CharField(required=False),
            "regione_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="ProvinceUpdateResp", fields={"data": serializers.DictField()})},
    )
    def patch(self, request: Request, pk: int) -> JsonResponse:
        return success_response(GeoService().update_provincia(pk, corpo_oggetto(request)))


class ProvinceLookupView(DomainAPIView):
    """GET lista per dropdown."""
    area_funzionale = "anagrafiche"

    @extend_schema(responses={200: inline_serializer(name="ProvinceLookupResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": GeoService().lookup_province()})
