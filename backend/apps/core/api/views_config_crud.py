# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views CRUD generico per tabelle config whitelisted.
#        Ref: docs/it/dev/api.md
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.services.config_crud_service import ConfigCrudService


class ConfigTablesListView(DomainAPIView):
    """GET lista tabelle disponibili."""
    area_funzionale = "config"

    @extend_schema(responses={200: inline_serializer(name="ConfigTablesListResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": ConfigCrudService().list_tables()})


class ConfigTableMetadataView(DomainAPIView):
    """GET metadata colonne di una tabella."""
    area_funzionale = "config"

    @extend_schema(
        parameters=[OpenApiParameter(name="rel", type=str, location="path", required=True)],
        responses={200: inline_serializer(name="ConfigTableMetadataResp", fields={"data": serializers.DictField()})},
    )
    def get(self, request: Request, rel: str) -> JsonResponse:
        return success_response({"columns": ConfigCrudService().get_metadata(rel)})


class ConfigTableRecordsView(DomainAPIView):
    """GET lista records, POST crea record."""
    area_funzionale = "config"
    is_search_endpoint = True

    @extend_schema(
        parameters=[OpenApiParameter(name="rel", type=str, location="path", required=True)],
        responses={200: inline_serializer(name="ConfigTableRecordsResp", fields={"data": serializers.DictField()})},
    )
    def get(self, request: Request, rel: str) -> JsonResponse:
        # Riusa il lookup esistente — redirect interno
        from apps.core.services.lookup_service import fn_list_lookup_codici
        from apps.core.api.payload_validators import qp_int
        qp = request.query_params
        data = fn_list_lookup_codici(
            rel=rel,
            search=(qp.get("search") or "").strip() or None,
            order_col=qp.get("order_col", "descrizione"),
            order_dir=qp.get("order_dir", "asc"),
            attivo_only=qp.get("attivo_only", "false").lower() not in ("0", "false", "no"),
            page=qp_int(qp.get("page"), 1),
            page_size=qp_int(qp.get("page_size"), 50),
        )
        return success_response(data)

    @extend_schema(
        parameters=[OpenApiParameter(name="rel", type=str, location="path", required=True)],
        responses={200: inline_serializer(name="ConfigTableCreateResp", fields={"data": serializers.DictField()})},
    )
    def post(self, request: Request, rel: str) -> JsonResponse:
        return handle_post_json(request, handler=lambda p: ConfigCrudService().create_record(rel, p))


class ConfigTableRecordDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna record."""
    area_funzionale = "config"

    @extend_schema(responses={200: inline_serializer(name="ConfigRecordDetailResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, rel: str, pk: int) -> JsonResponse:
        return success_response(ConfigCrudService().get_record(rel, pk))

    @extend_schema(responses={200: inline_serializer(name="ConfigRecordUpdateResp", fields={"data": serializers.DictField()})})
    def patch(self, request: Request, rel: str, pk: int) -> JsonResponse:
        return handle_post_json(request, handler=lambda p: ConfigCrudService().update_record(rel, pk, p))
