# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view lookup billing_account — endpoint dedicato di ricerca ricca
#        per autocomplete cross-dominio (listini, preventivi, ordini, ...).
#        View sottile: parsing query params + scope emittente + delega a service.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.anagrafiche.services.billing_account_service import BillingAccountService
from apps.core.api.base_views import DomainAPIView
from apps.core.api.payload_validators import qp_bool_optional, qp_int_strict
from apps.core.api.request_parsers import parse_iso_date
from apps.core.api.success_responses import success_response
from apps.core.services.permissions_resolver import PermissionResolver


_LOOKUP_RESPONSE = inline_serializer(
    name="BillingAccountLookupResp",
    fields={
        "data": serializers.DictField(),
        "meta": serializers.DictField(required=False),
    },
)


class BillingAccountLookupView(DomainAPIView):
    """GET lookup ricco billing_account per autocomplete UI."""

    # Lookup cross-dominio: preventivi/contratti/ordini/fatture lo usano da
    # aree diverse. Allineato al pattern dei lookup core (skip_area_check).
    # JWT + throttling search + scope emittente lato repository bastano.
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        operation_id="anagrafiche_billing_account_lookup_list",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                required=True,
                description="Termine di ricerca (min 2 char). Matcha codice BA, ragione sociale, id fiscale, PDP.",
            ),
            OpenApiParameter(
                name="utility_id",
                type=int,
                required=False,
                description="Filtra per utility specifica (gas/ee/idrico).",
            ),
            OpenApiParameter(
                name="solo_validi",
                type=bool,
                required=False,
                description="Se true (default) mostra solo BA validi alla data di riferimento.",
            ),
            OpenApiParameter(
                name="valid_at",
                type=str,
                required=False,
                description="Data ISO YYYY-MM-DD per filtro validita'. Default: oggi (solo se solo_validi=true).",
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
    # Scopo: Gestisce GET lookup billing_account.
    #        Risolve lo scope emittente dall'utente, parsa i query params,
    #        delega al service e restituisce envelope standard con results,
    #        total_count e limit per gestione UI "affina ricerca".
    def get(self, request: Request) -> JsonResponse:
        q = request.query_params.get("q", "")
        # qp_int_strict vuole un default int: usiamo una sentinella per distinguere
        # "non fornito" dal valore fornito. Il service applica il proprio default.
        raw_utility = request.query_params.get("utility_id")
        utility_id: int | None = None
        if raw_utility is not None and raw_utility != "":
            utility_id = qp_int_strict(raw_utility, "utility_id", 0)

        solo_validi = qp_bool_optional(request.query_params.get("solo_validi"), "solo_validi", default=True)

        raw_limit = request.query_params.get("limit")
        limit_kwargs: dict = {}
        if raw_limit is not None and raw_limit != "":
            limit_kwargs["limit"] = qp_int_strict(raw_limit, "limit", 0)

        raw_valid_at = request.query_params.get("valid_at")
        valid_at: date | None
        if raw_valid_at:
            valid_at = parse_iso_date(raw_valid_at)
        elif solo_validi:
            valid_at = oggi_aziendale()
        else:
            valid_at = None

        # Lo scope emittente lo risolve il service dall'utente.
        service = BillingAccountService()
        result = service.search_lookup(
            user=request.user,
            q=q,
            utility_id=utility_id,
            solo_validi=solo_validi,
            valid_at=valid_at,
            **limit_kwargs,
        )
        return success_response(result)


class BillingAccountLookupByIdView(DomainAPIView):
    """GET singolo billing_account arricchito per restore AutoComplete in edit."""

    # Lookup cross-dominio (restore): stesso ragionamento di
    # BillingAccountLookupView. Solo lettura singolo record gia' selezionato.
    skip_area_check = True

    @extend_schema(
        responses={200: _LOOKUP_RESPONSE},
    )
    # Scopo: Restituisce il billing_account arricchito (codice, ragione sociale,
    #        id fiscale, pdp, utility) per ricostruire l'oggetto dell'AutoComplete
    #        quando un form apre in edit e ha solo l'id.
    def get(self, request: Request, billing_account_id: int) -> JsonResponse:
        del request
        service = BillingAccountService()
        result = service.get_lookup_by_id(billing_account_id)
        return success_response(result)


class BillingAccountUtilitiesView(DomainAPIView):
    """GET utility "guidate da emittente" per un billing account.

    Refactor operatore-emittenti, sez. 3 del WIP. Pattern slot/override:
    elenca le utility ammesse per il ruolo del soggetto del BA, intersecate
    con quelle ammesse per il ruolo EF dell'emittente associato al BA, e
    decorate con i parametri override di emittenti_fiscali_utilities quando
    presenti per la coppia (emittente, utility).

    Permission: scope emittente sul BA target. Operatori vedono solo le
    utility dei BA del proprio emittente; admin globale e superuser bypass.
    """

    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "cliente")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="ruolo",
                type=str,
                required=True,
                description="Codice ruolo soggetto del BA: CL (cliente), FO (fornitore), GE (gestore).",
            ),
        ],
        responses={200: inline_serializer(
            name="BillingAccountUtilitiesResp",
            fields={
                "data": serializers.DictField(),
                "meta": serializers.DictField(required=False),
            },
        )},
    )
    # Scopo: GET utility per BA — risolve scope emittente e delega al service.
    def get(self, request: Request, billing_account_id: int) -> JsonResponse:
        ruolo = request.query_params.get("ruolo", "")
        # user_emittente_id 1-a-1 (PK reale). None per admin globale,
        # "0 emittenti" o utenti senza bridge HR.
        user_emittente_id = PermissionResolver.get_emittente_for_user(request.user)
        is_superuser = bool(getattr(request.user, "is_superuser", False))

        result = BillingAccountService().list_utilities_for_ba(
            billing_account_id=billing_account_id,
            ruolo_codice_soggetto=ruolo,
            user_emittente_id=user_emittente_id,
            is_superuser=is_superuser,
        )
        return success_response(result)
