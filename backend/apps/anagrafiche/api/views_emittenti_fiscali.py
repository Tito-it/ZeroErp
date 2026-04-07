# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views emittenti fiscali — view sottili, logica nel service.
#        Lista paginata, dettaglio, creazione e aggiornamento emittente.
#        Riservato agli amministratori (eredita AdminAPIView).
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.anagrafiche.services.emittenti_fiscali_service import (
    EmittentiFiscaliBillingAccountService,
    EmittentiFiscaliService,
    EmittentiFiscaliUtilitiesService,
)
from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import paginated_envelope, parse_list_params, qp_bool_optional
from apps.core.api.success_responses import success_response


# =================================================================
# Emittenti fiscali — lista + crea
# =================================================================


class EmittentiFiscaliView(AdminAPIView):
    """GET lista paginata, POST crea emittente fiscale (admin only)."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca su codice, descrizione, ragione_sociale, P.IVA, C.F."),
            OpenApiParameter(name="attivo", type=bool, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="EmittentiFiscaliListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata emittenti fiscali con search e filtro attivo.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="descrizione")
        svc = EmittentiFiscaliService()
        results, total = svc.list_emittenti_fiscali(
            search=p["search"],
            attivo=qp_bool_optional(request.query_params.get("attivo")),
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="EmittenteFiscaleCreateReq", fields={
            "soggetto_id": serializers.UUIDField(),
            "codice": serializers.CharField(),
            "descrizione": serializers.CharField(),
            "attivo": serializers.BooleanField(required=False),
            "regime_fiscale_rf": serializers.CharField(required=False),
            "esigibilita_iva_default": serializers.CharField(required=False),
            "split_payment_default": serializers.BooleanField(required=False),
            "bollo_auto": serializers.BooleanField(required=False),
            "bollo_soglia": serializers.FloatField(required=False),
            "rounding_policy": serializers.CharField(required=False),
            "valuta_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(
            name="EmittenteFiscaleCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea emittente fiscale completo (ruolo EF + insert in transazione atomica).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=EmittentiFiscaliService().crea_emittente)


# =================================================================
# Emittente fiscale — dettaglio
# =================================================================


class EmittentiFiscaliDetailView(AdminAPIView):
    """GET dettaglio, PATCH aggiorna emittente fiscale (admin only)."""

    @extend_schema(
        responses={200: inline_serializer(
            name="EmittenteFiscaleDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio completo di un emittente fiscale.
    def get(self, request: Request, emittente_id: int) -> JsonResponse:
        svc = EmittentiFiscaliService()
        data = svc.get_emittente(emittente_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(name="EmittenteFiscaleUpdateReq", fields={
            "descrizione": serializers.CharField(required=False),
            "attivo": serializers.BooleanField(required=False),
            "regime_fiscale_rf": serializers.CharField(required=False),
            "esigibilita_iva_default": serializers.CharField(required=False),
            "split_payment_default": serializers.BooleanField(required=False),
            "bollo_auto": serializers.BooleanField(required=False),
            "bollo_soglia": serializers.FloatField(required=False),
            "rounding_policy": serializers.CharField(required=False),
            "valuta_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(
            name="EmittenteFiscaleUpdateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna campi editabili dell'emittente fiscale.
    #        Il campo codice e' bloccato dal trigger DB lock_columns.
    def patch(self, request: Request, emittente_id: int) -> JsonResponse:
        svc = EmittentiFiscaliService()
        result = svc.update_emittente(emittente_id, request.data)
        return success_response(result)


# =================================================================
# Sub-resource: mapping BA -> emittente
# =================================================================


class EmittentiFiscaliBillingAccountView(AdminAPIView):
    """GET lista mapping BA, POST crea mapping (admin only)."""

    @extend_schema(
        responses={200: inline_serializer(
            name="EmittenteFiscaleBALListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista i mapping BA per un emittente fiscale.
    def get(self, request: Request, emittente_id: int) -> JsonResponse:
        svc = EmittentiFiscaliBillingAccountService()
        results = svc.list_mapping(emittente_id)
        return success_response({"results": results})

    @extend_schema(
        request=inline_serializer(name="EmittenteFiscaleBACreateReq", fields={
            "billing_account_id": serializers.IntegerField(
                required=False,
                help_text="Se omesso/null crea il default globale (one-shot, unico).",
            ),
        }),
        responses={200: inline_serializer(
            name="EmittenteFiscaleBACreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea un nuovo mapping BA->emittente. Senza billing_account_id crea il default globale.
    def post(self, request: Request, emittente_id: int) -> JsonResponse:
        svc = EmittentiFiscaliBillingAccountService()
        result = svc.crea_mapping(emittente_id, request.data or {})
        return success_response(result)


class EmittentiFiscaliBillingAccountDetailView(AdminAPIView):
    """DELETE mapping BA->emittente (admin only)."""

    @extend_schema(
        responses={200: inline_serializer(
            name="EmittenteFiscaleBADeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina un mapping per id, verificando appartenenza all'emittente padre.
    def delete(self, request: Request, emittente_id: int, mapping_id: int) -> JsonResponse:
        svc = EmittentiFiscaliBillingAccountService()
        result = svc.elimina_mapping(emittente_id, mapping_id)
        return success_response(result)


# =================================================================
# Sub-resource: utilities per emittente fiscale
# =================================================================


class EmittentiFiscaliUtilitiesView(AdminAPIView):
    """GET lista record utility, POST crea record (admin only)."""

    @extend_schema(
        responses={200: inline_serializer(
            name="EmittenteFiscaleUtilitiesListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista i record utility per un emittente fiscale.
    def get(self, request: Request, emittente_id: int) -> JsonResponse:
        svc = EmittentiFiscaliUtilitiesService()
        results = svc.list_records(emittente_id)
        return success_response({"results": results})

    @extend_schema(
        request=inline_serializer(name="EmittenteFiscaleUtilityCreateReq", fields={
            "utility_id": serializers.IntegerField(),
            "arrotondamento_importi_dec": serializers.IntegerField(),
            "metodo_arrotondamento_importi": serializers.CharField(),
            "minimo_soglia_min": serializers.FloatField(required=False),
            "minimo_soglia_max": serializers.FloatField(required=False),
            "attivo": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(
            name="EmittenteFiscaleUtilityCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea un record utility per l'emittente.
    def post(self, request: Request, emittente_id: int) -> JsonResponse:
        svc = EmittentiFiscaliUtilitiesService()
        result = svc.crea_record(emittente_id, request.data or {})
        return success_response(result)


class EmittentiFiscaliUtilitiesDetailView(AdminAPIView):
    """PATCH aggiorna, DELETE elimina record utility (admin only)."""

    @extend_schema(
        request=inline_serializer(name="EmittenteFiscaleUtilityUpdateReq", fields={
            "minimo_soglia_min": serializers.FloatField(required=False),
            "minimo_soglia_max": serializers.FloatField(required=False),
            "arrotondamento_importi_dec": serializers.IntegerField(required=False),
            "metodo_arrotondamento_importi": serializers.CharField(required=False),
            "attivo": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(
            name="EmittenteFiscaleUtilityUpdateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna campi editabili di un record utility (utility_id immutabile).
    def patch(self, request: Request, emittente_id: int, record_id: int) -> JsonResponse:
        svc = EmittentiFiscaliUtilitiesService()
        result = svc.aggiorna_record(emittente_id, record_id, request.data)
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="EmittenteFiscaleUtilityDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina un record utility per id, verificando appartenenza all'emittente padre.
    def delete(self, request: Request, emittente_id: int, record_id: int) -> JsonResponse:
        svc = EmittentiFiscaliUtilitiesService()
        result = svc.elimina_record(emittente_id, record_id)
        return success_response(result)


