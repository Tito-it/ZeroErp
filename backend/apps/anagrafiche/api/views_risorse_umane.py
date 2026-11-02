# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint lookup delle risorse umane (picker cross-dominio).
# Note: `GET /anagrafiche/risorse-umane/lookup/`. Primo consumatore: il campo
#       «responsabile» del drawer commessa (brief-db-modifiche-certe-ciclo-
#       vendita-e-articolo, §5.5 voce 4).
# ------------------------------------------------------------

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.anagrafiche.services.anagrafiche_service import AnagraficheService
from apps.core.api.base_views import DomainAPIView
from apps.core.api.payload_validators import qp_str
from apps.core.api.success_responses import success_response


class RisorseUmaneLookupView(DomainAPIView):
    """GET lookup delle risorse umane attive — id + nome + qualifica/reparto."""

    # Lookup cross-dominio (pattern «lookup top-level liberato» del catalogo BB:
    # `BillingAccountLookupView`, `SoggettiRuoliLookupView`): lo consuma il
    # drawer commessa di `vendite`, e chiuderlo sull'area `anagrafiche`
    # spegnerebbe il campo per chi non ha quell'area, in silenzio. Sola
    # lettura di dati non sensibili (nome e reparto); JWT + throttling restano.
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                required=False,
                description="Ricerca libera sul nome (min 3 caratteri). Assente = tutte le attive.",
            ),
        ],
        responses={200: inline_serializer(
            name="RisorseUmaneLookupResp",
            fields={
                "data": inline_serializer(
                    name="RisorseUmaneLookupData",
                    fields={"results": serializers.ListField(child=serializers.DictField())},
                ),
                "meta": serializers.DictField(required=False),
            },
        )},
    )
    # Scopo: Restituisce via GET le risorse umane attive nell'envelope `{"results": [...]}`.
    def get(self, request: Request) -> JsonResponse:
        search = qp_str(request.query_params.get("search"))
        return success_response(AnagraficheService().lookup_risorse_umane(search=search))
