# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: View form-defaults BA-aware e contestuali per vendite
#        (Fase 2.B3-B5 refactor frontend vendite).
#
#        5 endpoint sola lettura consumati dai drawer FE all'apertura
#        / al cambio BA (o sorgente versione). Pattern view sottile:
#        delega a vendite_form_defaults_service che orchestra
#        BillingAccountRepository / ListiniRepository / ParameterService.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_actor_user_id
from apps.core.api.payload_validators import optional_int
from apps.core.api.success_responses import success_response
from apps.vendite.services.vendite_form_defaults_service import (
    fn_get_contratto_form_defaults,
    fn_get_ddt_form_defaults,
    fn_get_offerta_form_defaults,
    fn_get_ordine_form_defaults,
    fn_get_preventivo_form_defaults,
    fn_get_versione_clone_defaults,
    fn_get_versione_close_defaults,
    fn_get_versione_new_defaults,
)


def _ba_aware_response_schema(name: str):
    # Scopo: schema OpenAPI uniforme per le risposte form-defaults
    #        (envelope success_response standard).
    return {
        200: inline_serializer(
            name=name,
            fields={
                "data": serializers.DictField(),
                "meta": serializers.DictField(required=False),
            },
        )
    }


class ApiContrattoFormDefaults(DomainAPIView):
    # Scopo: Defaults form contratto contestuali al BA (categoria_cliente_id_snapshot,
    #        utility/istanza, default_data, default_valido_dal). Sostituisce le
    #        derivazioni cablate in ContrattoDrawer.onBaSelected.
    area_funzionale = "vendite"
    model_permission = ("vendite", "contratto")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="billing_account_id",
                type=int,
                required=False,
                description="Se presente, popola i campi BA-derived. Se assente, ritorna solo i default da parameters.",
            ),
        ],
        responses=_ba_aware_response_schema("VenditeContrattoFormDefaultsResponse"),
    )
    # Scopo: GET form-defaults contratto. Risolve auth_user_id per applicare
    #        eventuali override personali dei parameters.
    def get(self, request: Request) -> JsonResponse:
        ba_id = optional_int({"v": request.query_params.get("billing_account_id")}, "v")
        auth_user_id = get_actor_user_id(request)
        return success_response(
            fn_get_contratto_form_defaults(
                billing_account_id=ba_id,
                auth_user_id=auth_user_id,
            )
        )


class ApiOffertaFormDefaults(DomainAPIView):
    # Scopo: Defaults form offerta commerciale contestuali al BA
    #        (categoria_cliente_id_snapshot, utility/istanza, valuta_id).
    #        Simmetrico a ApiContrattoFormDefaults: offerta e contratto
    #        condividono il modello "testata + eccezioni" senza
    #        termini/iva sul testata.
    area_funzionale = "vendite"
    model_permission = ("vendite", "offerta_commerciale")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="billing_account_id",
                type=int,
                required=False,
                description=(
                    "Se presente, popola i campi BA-derived (categoria_cliente, "
                    "utility, valuta). Se assente, ritorna valuta da EF utente "
                    "o gestore globale, BA-derived a null."
                ),
            ),
        ],
        responses=_ba_aware_response_schema("VenditeOffertaFormDefaultsResponse"),
    )
    # Scopo: GET form-defaults offerta. Risolve auth_user_id per
    #        cascata valuta (EF utente fallback) e per override personali
    #        eventuali sui parameters in futuro.
    def get(self, request: Request) -> JsonResponse:
        ba_id = optional_int({"v": request.query_params.get("billing_account_id")}, "v")
        auth_user_id = get_actor_user_id(request)
        return success_response(
            fn_get_offerta_form_defaults(
                billing_account_id=ba_id,
                auth_user_id=auth_user_id,
            )
        )


class ApiOrdineFormDefaults(DomainAPIView):
    # Scopo: Defaults form ordine di vendita contestuali al BA (utility, valuta).
    #        Allinea ordini alla famiglia: senza BA ritorna valuta dalla catena
    #        EF utente → gestore globale; con BA aggiunge utility BA-derived. La
    #        utility di default globale (DEFAULT_UTILITY) la risolve il FE.
    area_funzionale = "vendite"
    model_permission = ("vendite", "ordine")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="billing_account_id",
                type=int,
                required=False,
                description=(
                    "Se presente, popola utility BA-derived + valuta. Se assente, "
                    "ritorna valuta da EF utente o gestore globale."
                ),
            ),
        ],
        responses=_ba_aware_response_schema("VenditeOrdineFormDefaultsResponse"),
    )
    # Scopo: GET form-defaults ordine.
    def get(self, request: Request) -> JsonResponse:
        ba_id = optional_int({"v": request.query_params.get("billing_account_id")}, "v")
        auth_user_id = get_actor_user_id(request)
        return success_response(
            fn_get_ordine_form_defaults(
                billing_account_id=ba_id,
                auth_user_id=auth_user_id,
            )
        )


class ApiDdtFormDefaults(DomainAPIView):
    # Scopo: Defaults form DDT di vendita contestuali al BA (utility, valuta).
    #        Allinea il DDT alla famiglia ordini/preventivi/offerte: senza BA
    #        ritorna la valuta dalla catena EF utente → gestore globale; con BA
    #        aggiunge utility BA-derived + valuta del cliente. Il DDT è un
    #        documento di trasporto: nessun termine/modalita di pagamento in
    #        testata.
    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="billing_account_id",
                type=int,
                required=False,
                description=(
                    "Se presente, popola utility BA-derived + valuta. Se assente, "
                    "ritorna valuta da EF utente o gestore globale."
                ),
            ),
        ],
        responses=_ba_aware_response_schema("VenditeDdtFormDefaultsResponse"),
    )
    # Scopo: GET form-defaults DDT.
    def get(self, request: Request) -> JsonResponse:
        ba_id = optional_int({"v": request.query_params.get("billing_account_id")}, "v")
        auth_user_id = get_actor_user_id(request)
        return success_response(
            fn_get_ddt_form_defaults(
                billing_account_id=ba_id,
                auth_user_id=auth_user_id,
            )
        )


class ApiPreventivoFormDefaults(DomainAPIView):
    # Scopo: Defaults form preventivo contestuali al BA (valuta_id, termine_pagamento_id,
    #        iva_id derivati dal cliente del BA + emittente come fallback valuta).
    #        Sostituisce le combo "lascia vuoto e l'utente sceglie" dei drawer FE.
    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="billing_account_id",
                type=int,
                required=False,
                description="Se presente, popola i campi BA-derived (valuta, termini, IVA). Se assente, solo default da parameters.",
            ),
        ],
        responses=_ba_aware_response_schema("VenditePreventivoFormDefaultsResponse"),
    )
    # Scopo: GET form-defaults preventivo.
    def get(self, request: Request) -> JsonResponse:
        ba_id = optional_int({"v": request.query_params.get("billing_account_id")}, "v")
        auth_user_id = get_actor_user_id(request)
        return success_response(
            fn_get_preventivo_form_defaults(
                billing_account_id=ba_id,
                auth_user_id=auth_user_id,
            )
        )


class ApiListinoVersioneNewDefaults(DomainAPIView):
    # Scopo: Defaults form "Nuova versione" listino (default_valido_dal,
    #        existing_drafts). Sostituisce il calcolo `addDaysToToday(leadGg)`
    #        + lettura store nel VersioneFormDrawer.
    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

    @extend_schema(responses=_ba_aware_response_schema("VenditeListinoVersioneNewDefaultsResponse"))
    # Scopo: GET form-defaults nuova versione.
    def get(self, request: Request, listino_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        return success_response(
            fn_get_versione_new_defaults(
                listino_id=int(listino_id),
                auth_user_id=auth_user_id,
            )
        )


class ApiListinoVersioneCloneDefaults(DomainAPIView):
    # Scopo: Defaults form clone versione listino (default_codice_versione con
    #        suffisso configurato, default_valido_dal,
    #        is_retroactive_default). Sostituisce derivazioni cablate in
    #        CloneVersioneDrawer.
    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

    @extend_schema(responses=_ba_aware_response_schema("VenditeListinoVersioneCloneDefaultsResponse"))
    # Scopo: GET form-defaults clone versione.
    def get(self, request: Request, listino_id: int, src_versione_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        return success_response(
            fn_get_versione_clone_defaults(
                listino_id=int(listino_id),
                src_versione_id=int(src_versione_id),
                auth_user_id=auth_user_id,
            )
        )


class ApiListinoVersioneCloseDefaults(DomainAPIView):
    # Scopo: Defaults dialog chiusura versione listino (default_valido_al,
    #        current_valido_al per UX "ha_gia_chiusura"). Sostituisce
    #        l'inferenza `props.versione.valido_al ?? oggi+leadGg` di
    #        ChiudiVersioneDialog.
    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

    @extend_schema(responses=_ba_aware_response_schema("VenditeListinoVersioneCloseDefaultsResponse"))
    # Scopo: GET form-defaults chiusura versione.
    def get(self, request: Request, listino_id: int, versione_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        return success_response(
            fn_get_versione_close_defaults(
                listino_id=int(listino_id),
                versione_id=int(versione_id),
                auth_user_id=auth_user_id,
            )
        )
