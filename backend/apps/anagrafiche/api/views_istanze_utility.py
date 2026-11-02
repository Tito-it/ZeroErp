# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view lookup delle forniture (istanze_utilities, una riga per
#        billing account) — endpoint dedicato di ricerca ricca per
#        autocomplete cross-dominio (preventivo, pratica). View sottile:
#        parsing query params + scope emittente + delega a service.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
from apps.core.api.base_views import DomainAPIView
from apps.core.api.payload_validators import qp_int_strict
from apps.core.api.success_responses import success_response
from apps.core.services.permissions_resolver import PermissionResolver


_LOOKUP_RESPONSE = inline_serializer(
    name="IstanzaUtilityLookupResp",
    fields={
        "data": serializers.DictField(),
        "meta": serializers.DictField(required=False),
    },
)


class IstanzaUtilityLookupView(DomainAPIView):
    """GET lookup ricco delle forniture (una riga per BA) per autocomplete UI."""

    # Lookup cross-dominio: lo usano il preventivo (vendite) e la pratica
    # (pratiche). Stesso pattern di BillingAccountLookupView.
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        operation_id="anagrafiche_istanze_utility_lookup_list",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                required=False,
                description=(
                    "Termine di ricerca (min 2 char; puo' essere vuoto se "
                    "presente un filtro soggetto_id/soggetto_ruolo_id). "
                    "Matcha codice istanza, ragione sociale soggetto, "
                    "indirizzo normalizzato."
                ),
            ),
            OpenApiParameter(
                name="utility_id",
                type=int,
                required=False,
                description=(
                    "Filtra per utility specifica (gas/ee/idrico): la "
                    "utility del billing account della riga."
                ),
            ),
            OpenApiParameter(
                name="soggetto_id",
                type=str,
                required=False,
                description="UUID soggetto. Filtra istanze del solo soggetto.",
            ),
            OpenApiParameter(
                name="soggetto_ruolo_id",
                type=int,
                required=False,
                description=(
                    "Filtra i billing account di quel ruolo (le forniture "
                    "del cliente), con o senza la riga cliente."
                ),
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                required=False,
                description="Numero massimo risultati (default 20, max 50).",
            ),
        ],
        responses={200: _LOOKUP_RESPONSE},
    )
    # Scopo: Gestisce GET lookup istanze_utilities.
    #        Risolve lo scope emittente dall'utente, parsa i query params,
    #        delega al service e restituisce envelope standard con results,
    #        total_count e limit per gestione UI "affina ricerca".
    def get(self, request: Request) -> JsonResponse:
        q = request.query_params.get("q", "")

        raw_utility = request.query_params.get("utility_id")
        utility_id: int | None = None
        if raw_utility is not None and raw_utility != "":
            utility_id = qp_int_strict(raw_utility, "utility_id", 0)

        # soggetto_id e' UUID stringa: passato as-is al repository (cast ::uuid in SQL).
        raw_soggetto = request.query_params.get("soggetto_id")
        soggetto_id: str | None = raw_soggetto if raw_soggetto else None

        raw_sr = request.query_params.get("soggetto_ruolo_id")
        soggetto_ruolo_id: int | None = None
        if raw_sr is not None and raw_sr != "":
            soggetto_ruolo_id = qp_int_strict(raw_sr, "soggetto_ruolo_id", 0)

        raw_limit = request.query_params.get("limit")
        limit_kwargs: dict = {}
        if raw_limit is not None and raw_limit != "":
            limit_kwargs["limit"] = qp_int_strict(raw_limit, "limit", 0)

        # Scope emittente fiscale: sr_ids perche' la query filtra su
        # emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id.
        cache: dict = {}
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(request.user, cache=cache)

        service = IstanzeUtilityService()
        result = service.search_lookup(
            q=q,
            utility_id=utility_id,
            soggetto_id=soggetto_id,
            soggetto_ruolo_id=soggetto_ruolo_id,
            emittente_ids=emittente_ids,
            **limit_kwargs,
        )
        return success_response(result)


class IstanzaUtilityLookupByIdView(DomainAPIView):
    """GET singola istanza_utility arricchita per restore AutoComplete in edit."""

    # Lookup cross-dominio (restore): stesso pattern del list lookup.
    skip_area_check = True

    @extend_schema(
        responses={200: _LOOKUP_RESPONSE},
    )
    # Scopo: Restituisce l'istanza_utility arricchita (codice, soggetto,
    #        indirizzo, BA campione, utility dichiarata) per ricostruire
    #        l'oggetto dell'AutoComplete in modalita' edit.
    # ⛔ Con `skip_area_check` la catena non guarda piu' niente: il perimetro
    #    e' lo scope emittente, lo stesso della ricerca. Fino al 2026-10-08
    #    qui non c'era, e con un id si leggeva un'istanza di qualunque
    #    emittente (D10-bis).
    def get(self, request: Request, istanza_utility_id: int) -> JsonResponse:
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(request.user, cache={})
        service = IstanzeUtilityService()
        result = service.get_lookup_by_id(istanza_utility_id, emittente_ids=emittente_ids)
        return success_response(result)
