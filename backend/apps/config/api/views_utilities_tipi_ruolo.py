# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views admin per la matrice config.utilities_tipi_ruolo.
#        Lista paginata + create, dettaglio + patch (solo flag attivo),
#        usage emittenti fiscali per la riga matrice. Riservato admin.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.config.services.utilities_tipi_ruolo_service import (
    UtilitiesTipiRuoloService,
)
from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.config.db.utilities_tipi_ruolo_repository import USAGE_ORDER_COLS
from apps.core.api.openapi_params import descrizione_order_by, param_ricerca_full


# =================================================================
# Lista + creazione
# =================================================================


class UtilitiesTipiRuoloView(AdminAPIView):
    """GET lista paginata, POST crea riga matrice (admin only)."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="tipo_ruolo_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="ConfigUtilitiesTipiRuoloListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata righe matrice utilities x tipi_ruolo.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="utility_descrizione")
        svc = UtilitiesTipiRuoloService()
        results, total = svc.list_matrice(
            search=p["search"],
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            utility_id=qp_int_optional(request.query_params.get("utility_id"), "utility_id"),
            tipo_ruolo_id=qp_int_optional(request.query_params.get("tipo_ruolo_id"), "tipo_ruolo_id"),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(
            name="ConfigUtilitiesTipiRuoloCreateReq",
            fields={
                "utility_id": serializers.IntegerField(),
                "tipo_ruolo_id": serializers.IntegerField(),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="ConfigUtilitiesTipiRuoloCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea una nuova riga di matrice utility/tipo_ruolo.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=UtilitiesTipiRuoloService().create_matrice,
        )


# =================================================================
# Dettaglio + patch
# =================================================================


class UtilitiesTipiRuoloDetailView(AdminAPIView):
    """GET dettaglio, PATCH aggiorna flag attivo (admin only)."""

    @extend_schema(
        responses={200: inline_serializer(
            name="ConfigUtilitiesTipiRuoloDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio singola riga matrice.
    def get(self, request: Request, record_id: int) -> JsonResponse:
        del request
        svc = UtilitiesTipiRuoloService()
        return success_response(svc.get_matrice(record_id))

    @extend_schema(
        request=inline_serializer(
            name="ConfigUtilitiesTipiRuoloPatchReq",
            fields={
                "attivo": serializers.BooleanField(),
            },
        ),
        responses={200: inline_serializer(
            name="ConfigUtilitiesTipiRuoloPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna il flag attivo di una riga matrice (FK immutabili).
    def patch(self, request: Request, record_id: int) -> JsonResponse:
        svc = UtilitiesTipiRuoloService()
        return success_response(svc.update_matrice(record_id, corpo_oggetto(request)))


# =================================================================
# Usage emittenti fiscali
# =================================================================


class UtilitiesTipiRuoloUsageView(AdminAPIView):
    """GET emittenti fiscali che usano la matrice (override esistente)."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(
                name="order_by", type=str, required=False,
                description=descrizione_order_by(
                    USAGE_ORDER_COLS, "Default: ragione sociale, poi codice.",
                ),
            ),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="ConfigUtilitiesTipiRuoloUsageResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: la lista `config.utilities_tipi_ruolo_usage` (lista 86): gli
    #        emittenti fiscali che usano la riga di matrice indicata. Solo
    #        letture, contratto di lista standard (ricerca, ordinamento sulla
    #        whitelist, pagina).
    # ⚠️ `order_by` si legge grezzo e non dal bundle: il `default_order` di
    #    `parse_list_params` («descrizione») non e' una colonna di questa
    #    lista, e l'ordine di partenza — a due criteri — lo decide il
    #    repository.
    # ⭐ Nessun cancello di perimetro, e non per dimenticanza: la vista e'
    #    `AdminAPIView` (il cancello vive su `DomainAPIView`) e la lista e'
    #    certificata `multi_emittente` — ogni riga E' un emittente, e lo dice.
    #    Registrata in `_ESENZIONI` di `test_perimetro_emittente_copertura`.
    def get(self, request: Request, record_id: int) -> JsonResponse:
        p = parse_list_params(request.query_params)
        svc = UtilitiesTipiRuoloService()
        results, total = svc.list_usage(
            record_id,
            search=p["search"],
            order_by=qp_str(request.query_params.get("order_by")),
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))
