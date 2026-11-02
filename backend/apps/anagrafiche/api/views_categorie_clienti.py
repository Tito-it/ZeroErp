# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views admin per anagrafiche.categorie_clienti.
#        Lista paginata + create, dettaglio + patch. Riservato admin.
#        Collegamento al resolver prezzi v5: la categoria determina il listino
#        via matrice categorie_clienti_listini (STADIO 2).
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.anagrafiche.services.categorie_clienti_service import (
    CategorieClientiService,
)
from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
)
from apps.core.api.success_responses import success_response
from apps.core.api.openapi_params import param_ricerca_full


# =================================================================
# Lista + creazione
# =================================================================


class CategorieClientiView(AdminAPIView):
    """GET lista paginata, POST crea categoria (admin only)."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, required=False),
            OpenApiParameter(name="partecipa_promo", type=bool, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="codice | descrizione | ordinamento | partecipa_promo | attivo | data_insert | data_update"),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="AnagCategorieClientiListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata categorie cliente.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="ordinamento")
        svc = CategorieClientiService()
        results, total = svc.list_categorie(
            search=p["search"],
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            partecipa_promo=qp_bool_optional(request.query_params.get("partecipa_promo"), "partecipa_promo"),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(
            name="AnagCategorieClientiCreateReq",
            fields={
                "codice": serializers.CharField(),
                "descrizione": serializers.CharField(),
                "partecipa_promo": serializers.BooleanField(required=False),
                "ordinamento": serializers.IntegerField(required=False),
                "meta": serializers.JSONField(required=False, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="AnagCategorieClientiCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea una nuova categoria cliente.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=CategorieClientiService().create_categoria,
        )


# =================================================================
# Dettaglio + patch
# =================================================================


class CategorieClientiDetailView(AdminAPIView):
    """GET dettaglio, PATCH aggiorna campi modificabili (codice immutabile)."""

    @extend_schema(
        responses={200: inline_serializer(
            name="AnagCategorieClientiDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio singola categoria cliente.
    def get(self, request: Request, record_id: int) -> JsonResponse:
        del request
        svc = CategorieClientiService()
        return success_response(svc.get_categoria(record_id))

    @extend_schema(
        request=inline_serializer(
            name="AnagCategorieClientiPatchReq",
            fields={
                "descrizione": serializers.CharField(required=False),
                "partecipa_promo": serializers.BooleanField(required=False),
                "ordinamento": serializers.IntegerField(required=False),
                "meta": serializers.JSONField(required=False, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="AnagCategorieClientiPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna una categoria cliente (codice immutabile).
    def patch(self, request: Request, record_id: int) -> JsonResponse:
        svc = CategorieClientiService()
        return success_response(svc.update_categoria(record_id, corpo_oggetto(request)))
