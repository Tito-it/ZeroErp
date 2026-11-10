# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint lookup statici per enum di dominio vendite (Fase 2 refactor
#        frontend vendite). Esposti come `GET /api/v1/vendite/lookup/<nome>/`,
#        senza paginazione, area_funzionale=vendite (livello LETTURA).
#
#        Pattern modello: amm_software.api.views.EmittenteRoundingModesLookupView
#        (quello di catalogo, sulle UoM, e' ritirato il 2026-11-09 col campo).
#        Single source of truth: vendite_lookups_service._TIPI_VARIAZIONE_*
#        + _AMBITI_CONTRATTO.
#
#        Nota (refactor modalita 2026-05-15): la lookup
#        `modalita-pricing-contratto` (A/B/C) e' stata rimossa. Nel modello
#        unificato la "modalita" non e' piu' una scelta utente ma una forma
#        derivata dai dati (`listino_id` valorizzato vs NULL). Il FE non deve
#        presentare la scelta.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.openapi_params import risposta_lookup
from apps.core.api.payload_validators import qp_int_optional
from apps.core.api.success_responses import success_response
from apps.core.services.payload_helpers import INTEGER_MAX, INTEGER_MIN
from apps.vendite.services.vendite_lookups_service import (
    fn_list_ambiti_contratto,
    fn_list_listini_selezionabili,
    fn_list_tipi_variazione_contratto,
    fn_list_tipi_variazione_promo,
)


def _lookup_response_schema(name: str):
    # Scopo: factory per schema OpenAPI uniforme delle 3 lookup statiche.
    return {
        200: inline_serializer(
            name=name,
            fields={
                "data": serializers.ListField(child=serializers.DictField()),
                "meta": serializers.DictField(required=False),
            },
        )
    }


class ApiTipiVariazioneContrattoLookup(DomainAPIView):
    # Scopo: Lookup statico tipi_variazione ammessi nei contratti.
    #        Sostituisce il `tipoVariazioneOptions` cablato in ContrattoDrawer.
    area_funzionale = "vendite"

    @extend_schema(responses=_lookup_response_schema("VenditeTipiVariazioneContrattoLookupResponse"))
    # Scopo: Restituisce la lista codice/descrizione/ordering dei tipi variazione contratto.
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response(fn_list_tipi_variazione_contratto())


class ApiTipiVariazionePromoLookup(DomainAPIView):
    # Scopo: Lookup statico tipi_variazione ammessi nelle promo articoli.
    #        Aggiunge PREZZO_FISSO rispetto ai contratti (vedi service).
    area_funzionale = "vendite"

    @extend_schema(responses=_lookup_response_schema("VenditeTipiVariazionePromoLookupResponse"))
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response(fn_list_tipi_variazione_promo())


class ApiAmbitiContrattoLookup(DomainAPIView):
    # Scopo: Lookup statico ambiti contratto. Sostituisce `ambitoOptions`
    #        cablato in ContrattoDrawer.
    area_funzionale = "vendite"

    @extend_schema(responses=_lookup_response_schema("VenditeAmbitiContrattoLookupResponse"))
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response(fn_list_ambiti_contratto())


class ApiListiniSelezionabiliLookup(DomainAPIView):
    """GET /vendite/lookup/listini-selezionabili/?utility_id=&emittente_fiscale_id=

    I listini che un contratto o un'offerta di questa utility e di questo
    emittente puo' scegliere: la lettura del DB (`vendite.fn_listini_selezionabili`),
    lo stesso predicato del guard che rifiuta un listino di un'altra utility o
    di un altro emittente (`E_DOC_LISTINO_UTILITY_DIVERSA`,
    `E_DOC_LISTINO_EMITTENTE_DIVERSO`). ⛔ Il backend la trasporta, non la deduce.
    Sui VALORI del form (utility ed emittente scelti), perche' in creazione il
    documento non esiste; uno dei due assente → nessun listino. Envelope dei
    lookup `{"results": [...]}`, senza paginazione (brief-db-offerta-emissione-
    ed-erogazione F-2.3).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="utility_id", type=int, required=False,
                description="La utility del documento. Assente: nessun listino.",
            ),
            OpenApiParameter(
                name="emittente_fiscale_id", type=int, required=False,
                description=(
                    "L'emittente fiscale del documento (id di "
                    "`anagrafiche.emittenti_fiscali`). Assente: nessun listino."
                ),
            ),
        ],
        responses={200: risposta_lookup(
            "VenditeListiniSelezionabiliLookupResponse",
            riga=inline_serializer(
                name="VenditeListinoSelezionabile",
                fields={
                    "id": serializers.IntegerField(),
                    "codice": serializers.CharField(),
                    "descrizione": serializers.CharField(),
                },
            ),
        )},
    )
    # Scopo: i listini sceglibili per (utility, emittente) del form, 400 su un
    #        valore non numerico o fuori dal tipo del parametro della funzione
    #        (`utility_id integer`, `emittente_fiscale_id bigint`): oltre, la
    #        chiamata non si risolverebbe a DB, un 500.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        utility_id = qp_int_optional(
            qp.get("utility_id"), "utility_id",
            min_val=INTEGER_MIN, max_val=INTEGER_MAX,
        )
        emittente_fiscale_id = qp_int_optional(
            qp.get("emittente_fiscale_id"), "emittente_fiscale_id",
        )
        return success_response({
            "results": fn_list_listini_selezionabili(utility_id, emittente_fiscale_id),
        })
