# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views fornitori — view sottili, logica nel service.
#        Lista paginata, dettaglio, creazione e aggiornamento fornitore.
#        Pattern allineato a views_clienti.py (semplificato).
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
from apps.anagrafiche.services.fornitori_service import FornitoriService


# =================================================================
# Fornitori lista + crea
# =================================================================

class FornitoriView(DomainAPIView):
    """GET lista paginata, POST crea fornitore."""
    area_funzionale = "anagrafiche"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca su codice, ragione_sociale, P.IVA, C.F."),
            OpenApiParameter(name="stato_fornitore_id", type=int, required=False),
            OpenApiParameter(name="attivo", type=bool, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="FornitoriListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata fornitori con search e filtri stato/attivo.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="ragione_sociale_completa")
        stato_id = optional_int({"v": request.query_params.get("stato_fornitore_id")}, "v")
        # optional_bool ha default=False: non usabile per filtri opzionali.
        # Quando il parametro manca serve None (nessun filtro), non False.
        raw_attivo = request.query_params.get("attivo")
        attivo: bool | None = None
        if raw_attivo is not None:
            attivo = raw_attivo.strip().lower() in {"1", "true", "yes", "y", "on"}
        svc = FornitoriService()
        results, total = svc.list_fornitori(
            search=p["search"],
            stato_fornitore_id=stato_id,
            attivo=attivo,
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="FornitoreCreateReq", fields={
            "soggetto_id": serializers.UUIDField(),
            "valuta_id": serializers.IntegerField(required=False),
            "modalita_pagamento_id": serializers.IntegerField(required=False),
            "termine_pagamento_id": serializers.IntegerField(required=False),
            "giorni_pagamento": serializers.IntegerField(required=False),
            "fine_mese": serializers.BooleanField(required=False),
            "split_payment": serializers.BooleanField(required=False),
            "ritenuta_acconto": serializers.BooleanField(required=False),
            "ritenuta_aliquota": serializers.FloatField(required=False),
            "regime_fiscale": serializers.CharField(required=False),
            "bollo_esente": serializers.BooleanField(required=False),
            "canale_fe": serializers.CharField(required=False),
            "pec_email": serializers.CharField(required=False),
            "rating": serializers.IntegerField(required=False),
            "qualifica_scadenza": serializers.DateField(required=False),
            "note": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="FornitoreCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea fornitore completo (ruolo FO + insert in transazione atomica).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=FornitoriService().crea_fornitore)


# =================================================================
# Fornitore dettaglio
# =================================================================

class FornitoriDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna fornitore."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        responses={200: inline_serializer(name="FornitoreDetailResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Dettaglio completo di un fornitore.
    def get(self, request: Request, fornitore_id: int) -> JsonResponse:
        svc = FornitoriService()
        data = svc.get_fornitore(fornitore_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(name="FornitoreUpdateReq", fields={
            "stato_fornitore_id": serializers.IntegerField(required=False),
            "attivo": serializers.BooleanField(required=False),
            "valuta_id": serializers.IntegerField(required=False),
            "modalita_pagamento_id": serializers.IntegerField(required=False),
            "termine_pagamento_id": serializers.IntegerField(required=False),
            "giorni_pagamento": serializers.IntegerField(required=False),
            "fine_mese": serializers.BooleanField(required=False),
            "split_payment": serializers.BooleanField(required=False),
            "ritenuta_acconto": serializers.BooleanField(required=False),
            "ritenuta_aliquota": serializers.FloatField(required=False),
            "regime_fiscale": serializers.CharField(required=False),
            "bollo_esente": serializers.BooleanField(required=False),
            "canale_fe": serializers.CharField(required=False),
            "pec_email": serializers.CharField(required=False),
            "rating": serializers.IntegerField(required=False),
            "qualifica_scadenza": serializers.DateField(required=False),
            "note": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="FornitoreUpdateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Aggiorna campi editabili del fornitore (pagamento, fiscale, FE, rating, note).
    def patch(self, request: Request, fornitore_id: int) -> JsonResponse:
        svc = FornitoriService()
        result = svc.update_fornitore(fornitore_id, request.data)
        return success_response(result)
