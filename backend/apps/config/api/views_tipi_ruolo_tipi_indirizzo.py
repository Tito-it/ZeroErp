# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views admin per la matrice config.tipi_ruolo_tipi_indirizzo.
#        Lista paginata + create, dettaglio + patch. Riservato admin.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.config.services.tipi_ruolo_tipi_indirizzo_service import (
    TipiRuoloTipiIndirizzoService,
)
from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
)
from apps.core.api.success_responses import success_response
from apps.core.api.openapi_params import param_ricerca_full


class TipiRuoloTipiIndirizzoView(AdminAPIView):
    """GET lista paginata, POST crea riga matrice (admin only)."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, required=False),
            OpenApiParameter(name="tipo_ruolo_id", type=int, required=False),
            OpenApiParameter(name="tipo_indirizzo_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="ConfigTipiRuoloTipiIndirizzoListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata righe matrice tipi_ruolo x tipi_indirizzo.
    #        Envelope arricchito con `non_editable_fields` (Fase 4 — A9):
    #        il FE costruisce il drawer di edit usando la lista al livello
    #        envelope, no round-trip aggiuntivo.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="tipo_ruolo_descrizione")
        svc = TipiRuoloTipiIndirizzoService()
        results, total = svc.list_matrice(
            search=p["search"],
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            tipo_ruolo_id=qp_int_optional(request.query_params.get("tipo_ruolo_id"), "tipo_ruolo_id"),
            tipo_indirizzo_id=qp_int_optional(request.query_params.get("tipo_indirizzo_id"), "tipo_indirizzo_id"),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        envelope = paginated_envelope(results, total, p["page"], p["limit"])
        envelope["non_editable_fields"] = svc.get_non_editable_fields()
        return success_response(envelope)

    @extend_schema(
        request=inline_serializer(
            name="ConfigTipiRuoloTipiIndirizzoCreateReq",
            fields={
                "tipo_ruolo_id": serializers.IntegerField(),
                "tipo_indirizzo_id": serializers.IntegerField(),
                "obbligatorio": serializers.BooleanField(required=False),
                "fallback_tipo_indirizzo_id": serializers.IntegerField(required=False),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="ConfigTipiRuoloTipiIndirizzoCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea una nuova riga di matrice tipo_ruolo/tipo_indirizzo.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=TipiRuoloTipiIndirizzoService().create_matrice,
        )


class TipiRuoloTipiIndirizzoDetailView(AdminAPIView):
    """GET dettaglio, PATCH aggiorna campi modificabili (admin only)."""

    @extend_schema(
        responses={200: inline_serializer(
            name="ConfigTipiRuoloTipiIndirizzoDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio singola riga matrice.
    def get(self, request: Request, record_id: int) -> JsonResponse:
        del request
        svc = TipiRuoloTipiIndirizzoService()
        return success_response(svc.get_matrice(record_id))

    @extend_schema(
        request=inline_serializer(
            name="ConfigTipiRuoloTipiIndirizzoPatchReq",
            fields={
                "attivo": serializers.BooleanField(required=False),
                "obbligatorio": serializers.BooleanField(required=False),
                "fallback_tipo_indirizzo_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="ConfigTipiRuoloTipiIndirizzoPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna campi modificabili (attivo, obbligatorio, fallback). FK immutabili.
    def patch(self, request: Request, record_id: int) -> JsonResponse:
        svc = TipiRuoloTipiIndirizzoService()
        return success_response(svc.update_matrice(record_id, corpo_oggetto(request)))
