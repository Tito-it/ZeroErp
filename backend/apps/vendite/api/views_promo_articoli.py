# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per vendite.promo_articoli.
#        CRUD governato dal permesso area 'vendite' con possibilita' di
#        override per model 'promo_articolo' (pattern v2 permessi). STADIO 0
#        del resolver prezzi v5: (articolo, uom) in un periodo valido vince
#        su listino e matrice categoria.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.payload_validators import (
    corpo_oggetto,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_str,
)
from apps.core.api.request_parsers import parse_iso_date
from apps.core.api.success_responses import success_response
from apps.vendite.services.promo_articoli_service import PromoArticoliService


# =================================================================
# Lista + creazione
# =================================================================


class PromoArticoliView(DomainAPIView):
    """GET lista paginata, POST crea promo.

    Permesso area 'vendite' con override per model 'promo_articolo':
    admin puo' concedere/restringere l'accesso alle promo senza toccare
    il resto dell'area (pattern v2 permessi).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "promo_articolo")
    is_search_endpoint = True
    lista_codice = "vendite.promo_articoli"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, required=False),
            OpenApiParameter(name="articolo_id", type=str, required=False,
                             description="UUID articolo."),
            OpenApiParameter(name="uom_id", type=int, required=False),
            OpenApiParameter(name="tipo_variazione", type=str, required=False,
                             description="PERCENTUALE | VALORE_FISSO | PREZZO_FISSO"),
            OpenApiParameter(name="valid_at", type=str, required=False,
                             description="Data ISO YYYY-MM-DD: filtra righe la cui validita contiene la data."),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="codice | descrizione | articolo_codice | articolo_descrizione | "
                                         "uom_codice | valido_dal | valido_al | attivo | data_insert | data_update"),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditePromoArticoliListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata promo con filtri dimensionali.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="valido_dal")
        valid_at_raw = request.query_params.get("valid_at")
        valid_at: date | None = (
            parse_iso_date(valid_at_raw) if valid_at_raw else None
        )
        svc = PromoArticoliService()
        results, total = svc.list_promo(
            search=p["search"],
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            articolo_id=qp_str(request.query_params.get("articolo_id")),
            uom_id=qp_int_optional(request.query_params.get("uom_id"), "uom_id"),
            tipo_variazione=qp_str(request.query_params.get("tipo_variazione")),
            valid_at=valid_at,
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(
            name="VenditePromoArticoliCreateReq",
            fields={
                "codice": serializers.CharField(),
                "descrizione": serializers.CharField(),
                "articolo_id": serializers.UUIDField(),
                "uom_id": serializers.IntegerField(),
                "tipo_variazione": serializers.CharField(),
                "valore_variazione": serializers.DecimalField(
                    max_digits=10, decimal_places=4,
                ),
                "valido_dal": serializers.DateField(),
                "valido_al": serializers.DateField(),
                "meta": serializers.JSONField(required=False, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="VenditePromoArticoliCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea una nuova promo (STADIO 0 resolver v5).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=PromoArticoliService().create_promo,
        )


# =================================================================
# Dettaglio + patch
# =================================================================


class PromoArticoliDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna (codice/articolo/uom immutabili).

    Permesso area 'vendite' con override per model 'promo_articolo'.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "promo_articolo")

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditePromoArticoliDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio singola promo.
    def get(self, request: Request, record_id: int) -> JsonResponse:
        del request
        svc = PromoArticoliService()
        return success_response(svc.get_promo(record_id))

    @extend_schema(
        request=inline_serializer(
            name="VenditePromoArticoliPatchReq",
            fields={
                "descrizione": serializers.CharField(required=False),
                "tipo_variazione": serializers.CharField(required=False),
                "valore_variazione": serializers.DecimalField(
                    max_digits=10, decimal_places=4, required=False,
                ),
                "valido_dal": serializers.DateField(required=False),
                "valido_al": serializers.DateField(required=False),
                "meta": serializers.JSONField(required=False, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="VenditePromoArticoliPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna una promo (codice, articolo_id, uom_id immutabili).
    def patch(self, request: Request, record_id: int) -> JsonResponse:
        svc = PromoArticoliService()
        return success_response(svc.update_promo(record_id, corpo_oggetto(request)))
