# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from apps.core.api.payload_validators import corpo_oggetto, paginated_envelope, parse_list_params, qp_bool_optional
from apps.core.api.success_responses import success_response
from apps.core.api.openapi_params import param_ricerca_full


# =================================================================
# Emittenti fiscali — lista + crea
# =================================================================


class EmittentiFiscaliView(AdminAPIView):
    """GET lista paginata, POST crea emittente fiscale (admin only)."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
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
        # Default d'ordinamento allineato all'`ordinamento_default` del preset
        # `emittenti_fiscali_default` (seed lista 18): la ragione sociale del
        # soggetto. Era `descrizione`, colonna droppata il 2026-08-02.
        p = parse_list_params(request.query_params, default_order="ragione_sociale_completa")
        svc = EmittentiFiscaliService()
        results, total = svc.list_emittenti_fiscali(
            search=p["search"],
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(name="EmittenteFiscaleCreateReq", fields={
            "soggetto_id": serializers.UUIDField(
                help_text="UUID del soggetto: deve avere P.IVA valorizzata. "
                          "La denominazione dell'emittente e' la ragione sociale di questo soggetto.",
            ),
            "codice": serializers.CharField(),
            "attivo": serializers.BooleanField(required=False, help_text="Default DB: true."),
            "regime_fiscale_rf": serializers.CharField(
                required=False,
                help_text="Codice del catalogo config.regimi_fiscali (es. RF01). "
                          "Se presente e' il regime dichiarato, e l'emittente nasce "
                          "con il regime confermato (data e autore li deriva il DB). "
                          "Omesso: default RF01, NON confermato. Vuoto o null: 400.",
            ),
            "bollo_auto": serializers.BooleanField(required=False),
            "bollo_soglia": serializers.FloatField(required=False),
            "rounding_policy": serializers.ChoiceField(
                required=False,
                choices=["UP", "DOWN", "HALF_UP", "HALF_DOWN"],
                help_text="Allineato ai metodi della matrice utility.",
            ),
            "valuta_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(
            name="EmittenteFiscaleCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea emittente fiscale (ruolo EF + insert in transazione atomica).
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
            "attivo": serializers.BooleanField(required=False),
            "regime_fiscale_rf": serializers.CharField(
                required=False,
                help_text="Codice del catalogo config.regimi_fiscali. Se presente "
                          "(anche invariato) dichiara e CONFERMA il regime: data e "
                          "autore li deriva il DB. Chi non tocca il regime omette la "
                          "chiave. Vuoto o null: 400.",
            ),
            "bollo_auto": serializers.BooleanField(required=False),
            "bollo_soglia": serializers.FloatField(required=False),
            "rounding_policy": serializers.ChoiceField(
                required=False,
                choices=["UP", "DOWN", "HALF_UP", "HALF_DOWN"],
            ),
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
        result = svc.update_emittente(emittente_id, corpo_oggetto(request))
        return success_response(result)


# =================================================================
# Sub-resource: mapping BA -> emittente
# =================================================================


class EmittentiFiscaliBillingAccountView(AdminAPIView):
    """GET lista mapping BA, POST crea mapping (admin only)."""

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="EmittenteFiscaleBALListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata i mapping BA per un emittente fiscale con search.
    def get(self, request: Request, emittente_id: int) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="billing_account_codice")
        svc = EmittentiFiscaliBillingAccountService()
        results, total = svc.list_mapping(
            emittente_id,
            search=p["search"],
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

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
        result = svc.crea_mapping(emittente_id, corpo_oggetto(request))
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


class EmittentiFiscaliBillingAccountSummaryView(AdminAPIView):
    """GET summary mapping BA per un emittente (admin only)."""

    @extend_schema(
        responses={200: inline_serializer(
            name="EmittenteFiscaleBASummaryResp",
            fields={"data": inline_serializer(
                name="EmittenteFiscaleBASummaryData",
                fields={
                    "has_default": serializers.BooleanField(
                        help_text="True se esiste il mapping default globale per l'emittente.",
                    ),
                    "count_specifici": serializers.IntegerField(
                        help_text="Numero mapping specifici (con billing_account_id valorizzato).",
                    ),
                },
            )},
        )},
    )
    # Scopo: Riepilogo mapping BA per un emittente, indipendente dalla pagina FE.
    #        Risolve il bug A8/C3 in cui il pulsante "default" si riabilita se
    #        il record default non e' nella pagina corrente della lista paginata.
    def get(self, request: Request, emittente_id: int) -> JsonResponse:
        svc = EmittentiFiscaliBillingAccountService()
        result = svc.summary_mapping(emittente_id)
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
        result = svc.crea_record(emittente_id, corpo_oggetto(request))
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
        result = svc.aggiorna_record(emittente_id, record_id, corpo_oggetto(request))
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


