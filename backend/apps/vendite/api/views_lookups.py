# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint lookup statici per enum di dominio vendite (Fase 2 refactor
#        frontend vendite). Esposti come `GET /api/v1/vendite/lookup/<nome>/`,
#        senza paginazione, area_funzionale=vendite (livello LETTURA).
#
#        Pattern modello: catalogo.api.views.ApiUomRoundingModesLookup.
#        Single source of truth: vendite_lookups_service._TIPI_VARIAZIONE_*
#        + _AMBITI_CONTRATTO + _MODALITA_PRICING_CONTRATTO.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.success_responses import success_response
from apps.vendite.services.vendite_lookups_service import (
    fn_list_ambiti_contratto,
    fn_list_modalita_pricing_contratto,
    fn_list_tipi_variazione_contratto,
    fn_list_tipi_variazione_promo,
)


def _lookup_response_schema(name: str):
    # Scopo: factory per schema OpenAPI uniforme delle 4 lookup view.
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


class ApiModalitaPricingContrattoLookup(DomainAPIView):
    # Scopo: Lookup statico modalita pricing contratto (A/B/C). La modalita
    #        non e' una colonna DB ma un'astrazione UI; il backend la
    #        single-sources qui per evitare di duplicare i tre codici nel FE.
    area_funzionale = "vendite"

    @extend_schema(responses=_lookup_response_schema("VenditeModalitaPricingContrattoLookupResponse"))
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response(fn_list_modalita_pricing_contratto())
