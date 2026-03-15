# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view per lookup anagrafiche e config cross-dominio.
#        Endpoint: tipi soggetto dettaglio, matrice indirizzi,
#        autocomplete comuni, search stradario.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView

from apps.core.api.payload_validators import optional_int, qp_int
from apps.core.api.success_responses import success_response
from apps.core.db.lookup_repository import LookupRepository


class LookupTipiSoggettoDettaglioView(DomainAPIView):
    """Lista tipi soggetto dettaglio con natura e policy."""
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="TipiSoggettoDettaglioResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce i tipi soggetto dettaglio con natura, CF/PIVA/dati societari policy.
    # Il frontend usa questi dati per guidare la visibilita' dei campi nel SoggettoForm.
    def get(self, request: Request) -> JsonResponse:
        repo = LookupRepository()
        results = repo.list_tipi_soggetto_dettaglio()
        return success_response({"results": results})


class LookupMatriceIndirizziView(DomainAPIView):
    """Matrice indirizzi ammessi per un tipo soggetto dettaglio."""
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="MatriceIndirizziResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce la matrice tipi indirizzo ammessi/obbligatori per un tipo
    # soggetto dettaglio. Il frontend usa questi dati per mostrare i form indirizzo
    # corretti in base al tipo di soggetto selezionato.
    def get(self, request: Request, tipo_soggetto_dettaglio_id: int) -> JsonResponse:
        repo = LookupRepository()
        results = repo.list_matrice_indirizzi(tipo_soggetto_dettaglio_id)
        return success_response({"results": results})


class LookupComuniView(DomainAPIView):
    """Autocomplete comuni con ricerca ILIKE."""
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca ILIKE su denominazione comune."),
            OpenApiParameter(name="limit", type=int, required=False,
                             description="Righe massime (default 20, max 100)."),
            OpenApiParameter(name="offset", type=int, required=False,
                             description="Offset paginazione (default 0)."),
        ],
        responses={200: inline_serializer(
            name="ComuniAutocompleteResponse",
            fields={
                "data": inline_serializer(name="ComuniAutocompleteData", fields={
                    "count": serializers.IntegerField(),
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Ricerca comuni per autocomplete. Accetta search ILIKE su denominazione.
    # Restituisce id, descrizione, provincia_sigla con paginazione.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        search = (qp.get("search") or "").strip() or None
        limit = min(qp_int(qp.get("limit"), 20), 100)
        offset = qp_int(qp.get("offset"), 0)

        repo = LookupRepository()
        results, total_count = repo.search_comuni(
            search=search, limit=limit, offset=offset,
        )
        return success_response({"count": total_count, "results": results})


class SearchStradarioView(DomainAPIView):
    """Autocomplete vie (stradario) per comune."""
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="comune_id", type=int, required=False,
                             description="ID comune per filtrare le vie."),
            OpenApiParameter(name="search", type=str, required=False,
                             description="Ricerca su toponimo + denominazione via."),
            OpenApiParameter(name="limit", type=int, required=False,
                             description="Righe massime (default 30, max 100)."),
        ],
        responses={200: inline_serializer(
            name="StradarioSearchResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Ricerca vie per autocomplete. Chiama script.fn_search_stradario.
    # Il frontend usa questo endpoint dopo che l'utente ha selezionato un comune.
    # Restituisce stradario_id, via_completa, comune, provincia, CAP.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        comune_id = optional_int(qp, "comune_id")
        search = (qp.get("search") or "").strip() or None
        limit = min(qp_int(qp.get("limit"), 30), 100)

        repo = LookupRepository()
        results = repo.search_stradario(
            comune_id=comune_id, search=search, limit=limit,
        )
        return success_response({"results": results})
