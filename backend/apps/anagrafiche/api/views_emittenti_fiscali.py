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
from apps.core.api.payload_validators import corpo_oggetto, parse_list_params, qp_bool_optional
from apps.core.api.success_responses import success_response
from apps.core.api.openapi_params import param_ricerca_full, parametri_ordinamento
from apps.core.services.list_helpers import pagina_con_totale


# =================================================================
# Emittenti fiscali — lista + crea
# =================================================================


class EmittentiFiscaliView(AdminAPIView):
    """GET lista paginata, POST crea emittente fiscale (admin only)."""

    lista_codice = "anagrafiche.emittenti_fiscali"

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            *parametri_ordinamento(),
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
        return success_response(pagina_con_totale(results, total))

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
    """GET lista dei BA dell'emittente (consultazione), POST la rende predefinita (admin only)."""

    lista_codice = "anagrafiche.emittente_billing_account"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            *parametri_ordinamento(),
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
        return success_response(pagina_con_totale(results, total))

    @extend_schema(
        request=inline_serializer(name="EmittenteFiscaleBACreateReq", fields={}),
        responses={200: inline_serializer(
            name="EmittenteFiscaleBACreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Rende l'emittente l'azienda predefinita (corpo vuoto). Un BA nasce
    #        gia' collegato alla sua azienda: `billing_account_id` e' un 400.
    #        ⛔ Il DELETE del collegamento e' ritirato il 2026-11-27: il DB
    #        rifiuta la cancellazione di ogni collegamento
    #        (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`, giro 6).
    def post(self, request: Request, emittente_id: int) -> JsonResponse:
        svc = EmittentiFiscaliBillingAccountService()
        result = svc.imposta_predefinita(emittente_id, corpo_oggetto(request))
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
    """GET le utility dell'azienda, POST attiva un'utility (solo SUPER_ADMIN)."""

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
            "arrotondamento_importi_dec": serializers.IntegerField(required=False, allow_null=True),
            "metodo_arrotondamento_importi": serializers.CharField(required=False, allow_null=True),
            "minimo_soglia_min": serializers.FloatField(required=False, allow_null=True),
            "minimo_soglia_max": serializers.FloatField(required=False, allow_null=True),
        }),
        responses={200: inline_serializer(
            name="EmittenteFiscaleUtilityCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Attiva un'utility per l'azienda (i parametri sono facoltativi).
    def post(self, request: Request, emittente_id: int) -> JsonResponse:
        svc = EmittentiFiscaliUtilitiesService()
        result = svc.crea_record(emittente_id, corpo_oggetto(request))
        return success_response(result)


class EmittentiFiscaliUtilitiesDetailView(AdminAPIView):
    """PATCH i parametri, DELETE toglie l'utility all'azienda (solo SUPER_ADMIN)."""

    @extend_schema(
        request=inline_serializer(name="EmittenteFiscaleUtilityUpdateReq", fields={
            "minimo_soglia_min": serializers.FloatField(required=False, allow_null=True),
            "minimo_soglia_max": serializers.FloatField(required=False, allow_null=True),
            "arrotondamento_importi_dec": serializers.IntegerField(required=False, allow_null=True),
            "metodo_arrotondamento_importi": serializers.CharField(required=False, allow_null=True),
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
    # Scopo: Toglie l'utility all'azienda, verificando l'appartenenza all'emittente
    #        padre. Rifiutata se un billing account o un documento la usa.
    def delete(self, request: Request, emittente_id: int, record_id: int) -> JsonResponse:
        svc = EmittentiFiscaliUtilitiesService()
        result = svc.elimina_record(emittente_id, record_id)
        return success_response(result)


