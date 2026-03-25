# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views clienti — view sottili, logica nel service.
#        Lista paginata, dettaglio, creazione cliente.
#        Ref: docs/it/dev/work-in-progress/sviluppo-gestione-clienti.md
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
from apps.anagrafiche.services.clienti_service import ClientiService


# =================================================================
# Clienti lista + crea
# =================================================================

class ClientiView(DomainAPIView):
    """GET lista paginata, POST crea cliente."""
    area_funzionale = "anagrafiche"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca su ragione_sociale, codice_fiscale, codice BA"),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="stato_cliente_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="ClientiListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata clienti con search e filtri utility/stato.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="ragione_sociale_completa")
        utility_id = optional_int({"v": request.query_params.get("utility_id")}, "v")
        stato_id = optional_int({"v": request.query_params.get("stato_cliente_id")}, "v")
        svc = ClientiService()
        results, total = svc.list_clienti(
            search=p["search"],
            utility_id=utility_id,
            stato_cliente_id=stato_id,
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="ClienteCreateReq", fields={
            "soggetto_id": serializers.UUIDField(),
            "utility_id": serializers.IntegerField(),
            "istanza_utility_id": serializers.IntegerField(required=False),
            "billing_account_id": serializers.IntegerField(required=False),
            "indirizzo_dettaglio_id": serializers.IntegerField(required=False),
            "termine_pagamento_id": serializers.IntegerField(required=False),
            "modalita_pagamento_id": serializers.IntegerField(required=False),
            "iva_id": serializers.IntegerField(required=False),
            "ba_fatturazione_ordini": serializers.CharField(required=False),
            "ba_parent_account_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="ClienteCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea cliente completo (istanza + BA + cliente in transazione atomica).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=ClientiService().crea_cliente)


# =================================================================
# Cliente dettaglio
# =================================================================

class ClientiDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna cliente."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        responses={200: inline_serializer(name="ClienteDetailResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Dettaglio completo di un cliente.
    def get(self, request: Request, cliente_id: int) -> JsonResponse:
        svc = ClientiService()
        data = svc.get_cliente(cliente_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(name="ClienteUpdateReq", fields={
            "iva_id": serializers.IntegerField(required=False),
            "modalita_pagamento_id": serializers.IntegerField(required=False),
            "termine_pagamento_id": serializers.IntegerField(required=False),
            "tipo_gg_scadenza_ft": serializers.CharField(required=False),
            "nr_giorni_scadenza": serializers.IntegerField(required=False),
            "cliente_pa": serializers.CharField(required=False),
            "split_payment": serializers.CharField(required=False),
            "garanzia_tipo": serializers.CharField(required=False),
            "garanzia_importo": serializers.FloatField(required=False),
        }),
        responses={200: inline_serializer(name="ClienteUpdateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Aggiorna campi editabili del cliente (pagamento, PA, garanzia, servizio).
    def patch(self, request: Request, cliente_id: int) -> JsonResponse:
        svc = ClientiService()
        result = svc.update_cliente(cliente_id, request.data)
        return success_response(result)


# =================================================================
# Lookup utility ammesse per creazione manuale
# =================================================================

class UtilitiesManualLookupView(DomainAPIView):
    """GET utility con richiede_pdp=false per creazione manuale cliente."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        responses={200: inline_serializer(name="UtilitiesManualResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista utility ammesse per creazione manuale (richiede_pdp = false).
    def get(self, request: Request) -> JsonResponse:
        svc = ClientiService()
        results = svc.list_utilities_manuali()
        return success_response({"results": results})
