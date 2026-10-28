# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views indirizzi dettaglio e codici postali — view sottili, logica nel service.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import corpo_oggetto, optional_int, paginated_envelope, parse_list_params
from apps.core.api.success_responses import success_response
from apps.anagrafiche.services.geo_service import GeoService
from apps.core.api.openapi_params import param_ricerca_full


class IndirizziView(DomainAPIView):
    """GET lista, POST crea indirizzo dettaglio."""
    area_funzionale = "anagrafiche"
    is_search_endpoint = True
    lista_codice = "anagrafiche.indirizzi"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="comune_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="IndirizziListResp", fields={"data": serializers.DictField()})},
    )
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="indirizzo_normalizzato")
        comune_id = optional_int({"v": request.query_params.get("comune_id")}, "v")
        svc = GeoService()
        results, total = svc.list_indirizzi(
            search=p["search"], comune_id=comune_id,
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="IndirizziCreateReq", fields={
            "stradario_id": serializers.IntegerField(required=False),
            "toponomastica_id": serializers.IntegerField(required=False),
            "descrizione_via": serializers.CharField(required=False),
            "comune_id": serializers.IntegerField(required=False),
            "codice_postale_id": serializers.IntegerField(required=False),
            "civico": serializers.IntegerField(required=False),
            "estensione_civico": serializers.CharField(required=False),
            "palazzina": serializers.CharField(required=False),
            "scala": serializers.CharField(required=False),
            "piano": serializers.CharField(required=False),
            "interno": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="IndirizziCreateResp", fields={"data": serializers.DictField()})},
    )
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=GeoService().create_indirizzo)


class IndirizziDetailView(DomainAPIView):
    """GET dettaglio, PATCH aggiorna."""
    area_funzionale = "anagrafiche"

    @extend_schema(responses={200: inline_serializer(name="IndirizzoDetailResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, pk: int) -> JsonResponse:
        return success_response(GeoService().get_indirizzo(pk))

    @extend_schema(
        request=inline_serializer(name="IndirizzoUpdateReq", fields={
            "civico": serializers.IntegerField(required=False),
            "estensione_civico": serializers.CharField(required=False),
            "palazzina": serializers.CharField(required=False),
            "scala": serializers.CharField(required=False),
            "piano": serializers.CharField(required=False),
            "interno": serializers.CharField(required=False),
            "attivo": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(name="IndirizzoUpdateResp", fields={"data": serializers.DictField()})},
    )
    def patch(self, request: Request, pk: int) -> JsonResponse:
        return success_response(GeoService().update_indirizzo(pk, corpo_oggetto(request)))


class IndirizziCheckDuplicatoView(DomainAPIView):
    """POST check duplicato indirizzo. Due flussi:
    A) stradario_id diretto, B) stradario_generale_id + comune_id."""
    area_funzionale = "anagrafiche"
    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

    @extend_schema(
        request=inline_serializer(name="IndirizzoCheckDupReq", fields={
            "stradario_id": serializers.IntegerField(required=False, help_text="Flusso A: stradario locale"),
            "stradario_generale_id": serializers.IntegerField(required=False, help_text="Flusso B: stradario generale"),
            "comune_id": serializers.IntegerField(required=False, help_text="Flusso B: comune"),
            "codice_postale_id": serializers.IntegerField(required=False, help_text="Flusso B: CAP (opzionale)"),
            "civico": serializers.IntegerField(required=False),
            "estensione_civico": serializers.CharField(required=False),
            "palazzina": serializers.CharField(required=False),
            "scala": serializers.CharField(required=False),
            "piano": serializers.CharField(required=False),
            "interno": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="IndirizzoCheckDupResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Check duplicato indirizzo per warning immediato nel frontend.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: GeoService().check_indirizzo_duplicato(p),
        )


