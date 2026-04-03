# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per preventivi vendita (lista, dettaglio, righe, stato, integrazione).
# ------------------------------------------------------------

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    optional_int,
    optional_iso_date,
    qp_int,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.vendite.services import preventivi_service


# ── Lista + Creazione ──


class ApiPreventiviList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False, description="ISO date"),
            OpenApiParameter(name="data_al", type=str, required=False, description="ISO date"),
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="PreventiviListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET l'elenco paginato dei preventivi vendita.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        auth_user_id = get_scope_user_id(request)
        data = preventivi_service.list_preventivi(
            stato_codice=qp_str(qp.get("stato")),
            billing_account_id=optional_int({"v": qp.get("billing_account_id")}, "v"),
            utility_id=optional_int({"v": qp.get("utility_id")}, "v"),
            data_da=optional_iso_date({"v": qp.get("data_da")}, "v"),
            data_al=optional_iso_date({"v": qp.get("data_al")}, "v"),
            search=qp_str(qp.get("search")),
            auth_user_id=auth_user_id,
            page=qp_int(qp.get("page"), 1),
            page_size=qp_int(qp.get("page_size"), 50),
        )
        return success_response(data)

    @extend_schema(
        request=inline_serializer(
            name="PreventivoCreateRequest",
            fields={
                "utility_id": serializers.IntegerField(),
                "billing_account_id": serializers.IntegerField(required=False, allow_null=True),
                "istanza_utility_id": serializers.IntegerField(required=False, allow_null=True),
                "valuta_id": serializers.IntegerField(required=False, allow_null=True),
                "termine_pagamento_id": serializers.IntegerField(required=False, allow_null=True),
                "validita_dal": serializers.DateField(required=False, allow_null=True),
                "validita_al": serializers.DateField(required=False, allow_null=True),
                "competenza_mese": serializers.DateField(required=False, allow_null=True),
                "fatturazione_immediata": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoCreateResponse",
            fields={
                "data": inline_serializer(name="PreventivoCreateData", fields={
                    "id": serializers.IntegerField(),
                    "uid": serializers.CharField(),
                    "numero": serializers.CharField(),
                }),
            },
        )},
    )
    # Scopo: Crea un nuovo preventivo vendita via POST.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.crea_preventivo(payload)
        return handle_post_json(request, handler=_handler)


# ── Dettaglio + Aggiornamento ──


class ApiPreventivoDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoDetailResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET il dettaglio completo di un preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.get_preventivo(preventivo_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(
            name="PreventivoUpdateRequest",
            fields={
                "billing_account_id": serializers.IntegerField(required=False, allow_null=True),
                "validita_dal": serializers.DateField(required=False, allow_null=True),
                "validita_al": serializers.DateField(required=False, allow_null=True),
                "competenza_mese": serializers.DateField(required=False, allow_null=True),
                "fatturazione_immediata": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoUpdateResponse",
            fields={"data": inline_serializer(name="PreventivoUpdateData", fields={
                "status": serializers.CharField(),
                "preventivo_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Aggiorna un preventivo via PATCH.
    def patch(self, request: Request, preventivo_id: int) -> JsonResponse:
        result = preventivi_service.aggiorna_preventivo(preventivo_id, request.data)
        return success_response(result)


# ── Cambio stato ──


class ApiPreventivoStato(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "cambia_stato_preventivi"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoStatoRequest",
            fields={"nuovo_stato": serializers.CharField()},
        ),
        responses={200: inline_serializer(
            name="PreventivoStatoResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Cambia stato preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            nuovo_stato = str(payload.get("nuovo_stato", ""))
            return preventivi_service.cambia_stato(preventivo_id, nuovo_stato)
        return handle_post_json(request, handler=_handler)


# ── Revisione ──


class ApiPreventivoRevisione(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRevisioneResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea nuova revisione preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.crea_revisione(preventivo_id)
        return handle_post_json(request, handler=_handler)


# ── Righe: lista + creazione ──


class ApiPreventivoRigheList(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigheListResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET le righe del preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.list_righe(preventivo_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(
            name="PreventivoRigaCreateRequest",
            fields={
                "articolo_id": serializers.CharField(),
                "descrizione": serializers.CharField(required=False, allow_null=True),
                "quantita": serializers.DecimalField(max_digits=22, decimal_places=6, required=False),
                "prezzo_unitario": serializers.DecimalField(max_digits=22, decimal_places=10, required=False),
                "sconto_percentuale": serializers.DecimalField(max_digits=5, decimal_places=2, required=False),
                "iva_id": serializers.IntegerField(required=False, allow_null=True),
                "uom_operativa_id": serializers.IntegerField(required=False, allow_null=True),
                "ordine": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoRigaCreateResponse",
            fields={"data": inline_serializer(name="PreventivoRigaCreateData", fields={
                "id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Aggiunge riga al preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.gestisci_riga(preventivo_id, payload)
        return handle_post_json(request, handler=_handler)


# ── Righe: aggiornamento + eliminazione ──


class ApiPreventivoRigaDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoRigaUpdateRequest",
            fields={
                "quantita": serializers.DecimalField(max_digits=22, decimal_places=6, required=False),
                "prezzo_unitario": serializers.DecimalField(max_digits=22, decimal_places=10, required=False),
                "sconto_percentuale": serializers.DecimalField(max_digits=5, decimal_places=2, required=False),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoRigaUpdateResponse",
            fields={"data": inline_serializer(name="PreventivoRigaUpdateData", fields={
                "status": serializers.CharField(),
                "riga_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Aggiorna riga preventivo via PATCH.
    def patch(self, request: Request, preventivo_id: int, riga_id: int) -> JsonResponse:
        result = preventivi_service.aggiorna_riga(preventivo_id, riga_id, request.data)
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigaDeleteResponse",
            fields={"data": inline_serializer(name="PreventivoRigaDeleteData", fields={
                "status": serializers.CharField(),
                "riga_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Elimina (soft delete) riga preventivo via DELETE.
    def delete(self, request: Request, preventivo_id: int, riga_id: int) -> JsonResponse:
        result = preventivi_service.elimina_riga(preventivo_id, riga_id)
        return success_response(result)


# ── Indirizzi ──


class ApiPreventivoIndirizzi(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoIndirizziListResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET gli indirizzi del preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.list_indirizzi(preventivo_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(
            name="PreventivoIndirizzoUpsertRequest",
            fields={
                "tipo_indirizzo_id": serializers.IntegerField(),
                "snapshot": serializers.DictField(),
                "origine_indirizzo_id": serializers.IntegerField(required=False, allow_null=True),
                "origine_soggetto_ruolo_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoIndirizzoUpsertResponse",
            fields={"data": inline_serializer(name="PreventivoIndirizzoUpsertData", fields={
                "id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Upsert indirizzo preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.upsert_indirizzo(preventivo_id, payload)
        return handle_post_json(request, handler=_handler)


# ── Integrazione: push commessa ──


class ApiPreventivoPushCommessa(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "push_commessa_preventivi"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoPushCommessaResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Push preventivo in commessa per fatturazione via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.push_a_commessa(preventivo_id)
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ── Integrazione: stato fatturazione ──


class ApiPreventivoStatoFatturazione(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoStatoFatturazioneResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET lo stato fatturazione del preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.stato_fatturazione(preventivo_id)
        return success_response(data)


# ── Integrazione: genera pratica ──


class ApiPreventivoGeneraPratica(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "genera_pratica_preventivi"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoGeneraPraticaRequest",
            fields={
                "tipo_prestazione_id": serializers.IntegerField(),
                "priorita_id": serializers.IntegerField(),
                "descrizione": serializers.CharField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoGeneraPraticaResponse",
            fields={"data": inline_serializer(name="PreventivoGeneraPraticaData", fields={
                "pratica_id": serializers.IntegerField(),
                "preventivo_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Genera pratica esecutiva da preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.genera_pratica(
                preventivo_id,
                tipo_prestazione_id=int(payload["tipo_prestazione_id"]),
                priorita_id=int(payload["priorita_id"]),
                descrizione=payload.get("descrizione"),
            )
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ── Integrazione: pratiche collegate ──


class ApiPreventivoPratiche(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoPraticheResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET le pratiche collegate al preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.list_pratiche(preventivo_id)
        return success_response(data)
