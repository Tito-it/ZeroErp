# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views conti bancari — view sottili, logica nel service.
#        Lookup registro IBAN, lookup filiali, CRUD legami soggetto
#        e ruolo. Ref: docs/it/guide/gestione-conti-bancari.md
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.api.payload_validators import corpo_oggetto, parse_list_params, qp_int_optional
from apps.anagrafiche.services.conti_bancari_service import ContiBancariService


# =================================================================
# Lookup registro IBAN
# =================================================================

class ContiBancariLookupView(DomainAPIView):
    """GET ricerca IBAN nel registro per autocomplete."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "conto_bancario")

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=True),
            OpenApiParameter(name="limit", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="ContiBancariLookupResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Ricerca IBAN per autocomplete (min 2 char).
    def get(self, request: Request) -> JsonResponse:
        search = request.query_params.get("search", "")
        # Autocomplete: 10 righe di default; il tetto e la validazione del
        # numero sono quelli di ogni lista (prima `int()` nudo e nessun tetto:
        # `?limit=1000000` restituiva la tabella intera).
        limit = parse_list_params(request.query_params, default_limit=10)["limit"]
        svc = ContiBancariService()
        results = svc.search_conti_bancari(search, limit)
        return success_response({"results": results})


# =================================================================
# Lookup filiali bancarie
# =================================================================

class BankBranchesLookupView(DomainAPIView):
    """GET ricerca filiali bancarie per autocomplete."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "conto_bancario")

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=True),
            OpenApiParameter(name="limit", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="BankBranchesLookupResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Ricerca filiali per autocomplete (min 2 char).
    def get(self, request: Request) -> JsonResponse:
        search = request.query_params.get("search", "")
        # Autocomplete: 10 righe di default; il tetto e la validazione del
        # numero sono quelli di ogni lista (prima `int()` nudo e nessun tetto:
        # `?limit=1000000` restituiva la tabella intera).
        limit = parse_list_params(request.query_params, default_limit=10)["limit"]
        svc = ContiBancariService()
        results = svc.search_bank_branches(search, limit)
        return success_response({"results": results})


# =================================================================
# Conti bancari soggetto — lista + crea
# =================================================================

class SoggettoContiBancariView(DomainAPIView):
    """GET lista conti soggetto, POST crea legame soggetto ↔ conto."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "conto_bancario")

    @extend_schema(
        responses={200: inline_serializer(
            name="SoggettoContiBancariListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista conti bancari del soggetto.
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        svc = ContiBancariService()
        results = svc.list_conti_soggetto(soggetto_id)
        return success_response({"results": results})

    @extend_schema(
        request=inline_serializer(name="SoggettoContoBancarioCreateReq", fields={
            "iban": serializers.CharField(),
            "bic_swift": serializers.CharField(required=False),
            "bank_branch_id": serializers.IntegerField(),
            "uso": serializers.CharField(required=False),
            "predefinito": serializers.BooleanField(required=False),
            "valido_dal": serializers.DateField(required=False),
            "valido_al": serializers.DateField(required=False),
        }),
        responses={200: inline_serializer(
            name="SoggettoContoBancarioCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea legame soggetto ↔ conto (con get_or_create registro IBAN).
    def post(self, request: Request, soggetto_id: str) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: ContiBancariService().create_conto_soggetto(soggetto_id, p),
        )


# =================================================================
# Conti bancari soggetto — dettaglio (PATCH, DELETE)
# =================================================================

class SoggettoContiBancariDetailView(DomainAPIView):
    """PATCH aggiorna, DELETE elimina legame soggetto ↔ conto."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "conto_bancario")

    @extend_schema(
        request=inline_serializer(name="SoggettoContoBancarioUpdateReq", fields={
            "uso": serializers.CharField(required=False),
            "predefinito": serializers.BooleanField(required=False),
            "valido_dal": serializers.DateField(required=False),
            "valido_al": serializers.DateField(required=False),
            "intestazione_dichiarata": serializers.CharField(required=False),
            "verificato": serializers.BooleanField(required=False),
            "bloccato": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(
            name="SoggettoContoBancarioUpdateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna legame soggetto ↔ conto con ownership check.
    def patch(self, request: Request, soggetto_id: str, cb_id: int) -> JsonResponse:
        result = ContiBancariService().update_conto_soggetto(soggetto_id, cb_id, corpo_oggetto(request))
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="SoggettoContoBancarioDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina legame soggetto ↔ conto con ownership check.
    def delete(self, request: Request, soggetto_id: str, cb_id: int) -> JsonResponse:
        return success_response(
            ContiBancariService().delete_conto_soggetto(soggetto_id, cb_id)
        )


# =================================================================
# Conti bancari ruolo — lista + crea
# =================================================================

class RuoloContiBancariView(DomainAPIView):
    """GET lista conti ruolo (+ ereditati), POST crea legame ruolo ↔ conto."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "conto_bancario")

    @extend_schema(
        parameters=[
            OpenApiParameter(name="istanza_utility_id", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="RuoloContiBancariListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista conti del ruolo con cascata 3 livelli (istanza → ruolo → soggetto).
    #        Query param istanza_utility_id opzionale; se NULL, cascata parte da livello ruolo.
    def get(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        # BB `qp_int_optional`, come il gemello dei contatti: vuoto = assente,
        # un non intero o un numero oltre il bigint e' un 400 (fino al
        # 2026-10-20 `int()` grezzo: il fuori-range arrivava al DB).
        istanza_utility_id = qp_int_optional(
            request.query_params.get("istanza_utility_id"), "istanza_utility_id",
        )
        svc = ContiBancariService()
        result = svc.list_conti_ruolo(soggetto_ruolo_id, istanza_utility_id=istanza_utility_id)
        return success_response(result)

    @extend_schema(
        request=inline_serializer(name="RuoloContoBancarioCreateReq", fields={
            "iban": serializers.CharField(),
            "bic_swift": serializers.CharField(required=False),
            "bank_branch_id": serializers.IntegerField(),
            "uso": serializers.CharField(required=False),
            "predefinito": serializers.BooleanField(required=False),
            "istanza_utility_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(
            name="RuoloContoBancarioCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea legame ruolo ↔ conto (con get_or_create registro IBAN).
    def post(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: ContiBancariService().create_conto_ruolo(soggetto_ruolo_id, p),
        )


# =================================================================
# Conti bancari ruolo — dettaglio (PATCH, DELETE)
# =================================================================

class RuoloContiBancariDetailView(DomainAPIView):
    """PATCH aggiorna, DELETE elimina legame ruolo ↔ conto."""
    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "conto_bancario")

    @extend_schema(
        request=inline_serializer(name="RuoloContoBancarioUpdateReq", fields={
            "uso": serializers.CharField(required=False),
            "predefinito": serializers.BooleanField(required=False),
            "valido_dal": serializers.DateField(required=False),
            "valido_al": serializers.DateField(required=False),
            "intestazione_dichiarata": serializers.CharField(required=False),
            "verificato": serializers.BooleanField(required=False),
            "bloccato": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(
            name="RuoloContoBancarioUpdateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna legame ruolo ↔ conto con ownership check.
    def patch(self, request: Request, soggetto_ruolo_id: int, cb_id: int) -> JsonResponse:
        result = ContiBancariService().update_conto_ruolo(soggetto_ruolo_id, cb_id, corpo_oggetto(request))
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="RuoloContoBancarioDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina legame ruolo ↔ conto con ownership check.
    def delete(self, request: Request, soggetto_ruolo_id: int, cb_id: int) -> JsonResponse:
        return success_response(
            ContiBancariService().delete_conto_ruolo(soggetto_ruolo_id, cb_id)
        )
