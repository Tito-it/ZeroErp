# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view per dashboard configurabili (`/api/v1/ui/dashboard/*`).
#        Meta-API trasversale come le liste: `skip_area_check=True`
#        perche' lo schema `ui` non e' un'area funzionale (la
#        presentazione e' ortogonale alle aree di business). Il filtro
#        autorizzativo dei singoli widget vive dentro
#        `fn_resolve_dashboard_config` (brief DB §3b), non qui.
#
#        Endpoint:
#          - GET    /dashboard/<codice>/config     -> fn_resolve_dashboard_config
#          - GET    /dashboard/<codice>/contatori  -> KPI batch (per-key envelope)
#          - PUT    /dashboard/<codice>/preferenza -> upsert preferenza utente
#          - DELETE /dashboard/<codice>/preferenza -> elimina preferenza utente
#          - POST   /dashboard/<codice>/preferenza/ignore-preset-update
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.ui.services.dashboard_contatori_service import (
    DashboardContatoriService,
)
from apps.ui.services.dashboard_preferenza_service import (
    DashboardPreferenzaService,
)
from apps.ui.services.dashboard_service import DashboardService


_DATA_RESPONSE = inline_serializer(
    name="UiDashboardDataResponse",
    fields={
        "data": serializers.JSONField(),
        "meta": serializers.DictField(required=False),
    },
)


class ApiDashboardConfigView(DomainAPIView):
    """
    GET /api/v1/ui/dashboard/<codice>/config

    Risolve la configurazione effettiva della dashboard per l'utente
    autenticato: cascata preferenza -> preset ruolo/emittente/sistema ->
    catalogo grezzo, merge widget nuovi, filtro permessi. Tutto lato fn DB.
    """

    skip_area_check = True

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce la configurazione effettiva della dashboard.
    def get(self, request: Request, codice: str) -> JsonResponse:
        config = DashboardService().get_dashboard_config(request.user, codice)
        return success_response(config)


class ApiDashboardContatoriView(DomainAPIView):
    """
    GET /api/v1/ui/dashboard/<codice>/contatori

    Calcola in un solo giro i contatori KPI dei widget VISIBILI della
    dashboard risolta per l'utente.

    Non accetta chiavi dal client di proposito: le `contatore_key` sono
    quelle che la fn DB ha gia' concesso a questo utente. Passarle da
    fuori aprirebbe una lettura cross-area (es. conteggi vendite a un
    utente senza quell'area).

    Envelope per-key: un contatore rotto degrada la sua card
    (`{"valore": null, "ok": false}`) senza oscurare le altre.
    """

    skip_area_check = True

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce i contatori KPI dei widget visibili all'utente.
    def get(self, request: Request, codice: str) -> JsonResponse:
        # Risolve una sola volta e passa la config al service dei
        # contatori: evita di richiamare la fn DB due volte per la
        # stessa richiesta.
        config = DashboardService().get_dashboard_config(request.user, codice)
        contatori = DashboardContatoriService().get_contatori(
            request.user, codice, config=config,
        )
        return success_response({"contatori": contatori})


class ApiDashboardPreferenzaView(DomainAPIView):
    """
    PUT    /api/v1/ui/dashboard/<codice>/preferenza  -> upsert
    DELETE /api/v1/ui/dashboard/<codice>/preferenza  -> elimina
    """

    skip_area_check = True

    @extend_schema(
        request=inline_serializer(
            name="UiDashboardPreferenzaUpsertRequest",
            fields={
                "widget": serializers.ListField(
                    child=serializers.DictField(),
                    required=False,
                ),
                "dimensione_max": serializers.IntegerField(required=False),
            },
        ),
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: UPSERT preferenza utente. Idempotency-Key obbligatoria,
    #        come per le liste (pattern api.md su retry FE).
    def put(self, request: Request, codice: str) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return DashboardPreferenzaService().upsert(
                request.user, codice, dict(payload),
            )

        return handle_post_json(
            request,
            handler=_handler,
            require_idempotency_key=True,
        )

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Elimina preferenza utente (torna al default di ruolo).
    #        Idempotente: 200 anche se non esisteva.
    def delete(self, request: Request, codice: str) -> JsonResponse:
        result = DashboardPreferenzaService().delete(request.user, codice)
        return success_response(result)


class ApiDashboardIgnorePresetUpdateView(DomainAPIView):
    """
    POST /api/v1/ui/dashboard/<codice>/preferenza/ignore-preset-update

    Tombstone "Ignora banner preset aggiornato": setta
    `preset_aggiornato_ignored_at = NOW()` sulla preferenza utente.
    Body vuoto ammesso.
    """

    skip_area_check = True

    @extend_schema(request=None, responses={200: _DATA_RESPONSE})
    # Scopo: Setta il tombstone "ignore" del banner per (user, dashboard).
    def post(self, request: Request, codice: str) -> JsonResponse:
        def _handler(_payload: dict[str, Any]) -> dict[str, Any]:
            return DashboardPreferenzaService().ignore_preset_update(
                request.user, codice,
            )

        return handle_post_json(
            request,
            handler=_handler,
            require_idempotency_key=True,
        )
