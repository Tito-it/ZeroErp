# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API admin edizioni workflow versionate (Fase 2 Slice 1a): lista
#        + drift. AdminAPIView (super-admin). Read-only: le azioni write
#        (fork/nuova-versione/pubblica) arrivano in lockstep con la
#        conversione SECURITY DEFINER delle fn DB
#        (brief-db-accesso-be-definizioni-workflow.md §P1).
# ------------------------------------------------------------
from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import qp_int_optional
from apps.core.api.success_responses import success_response
from apps.pratiche.services import definizioni_service


class ApiDefinizioniWorkflow(AdminAPIView):
    """GET lista edizioni workflow (per tipo/emittente) con drift. Solo super-admin.

    Fase 2 Slice 1a — read-only: le letture su workflow_definizioni/vw_definizioni_drift
    sono gia' sbloccate a DB (GRANT SELECT). Le azioni fork/nuova-versione/pubblica
    verranno aggiunte in lockstep con la conversione DEFINER delle fn DB.
    """

    @extend_schema(
        parameters=[
            OpenApiParameter(name="tipo_prestazione_id", type=int, required=False),
            OpenApiParameter(name="emittente_fiscale_id", type=int, required=False,
                             description="Filtra per emittente; assente = tutte, preset inclusi."),
        ],
        responses={200: inline_serializer(
            name="PraticheDefinizioniListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista edizioni workflow con drift (super-admin).
    def get(self, request: Request) -> JsonResponse:
        results = definizioni_service.list_definizioni(
            tipo_prestazione_id=qp_int_optional(
                request.query_params.get("tipo_prestazione_id"), "tipo_prestazione_id"),
            emittente_fiscale_id=qp_int_optional(
                request.query_params.get("emittente_fiscale_id"), "emittente_fiscale_id"),
        )
        return success_response({"results": results})


# --- Azioni ciclo di vita (Slice 1b) -----------------------------------------
# Co-requisito lockstep: fn DB a SECURITY DEFINER (brief-db-accesso §P1). Finché
# INVOKER, restituiscono E_DATABASE (permesso negato sulla DML). Idempotenti.

class ApiDefinizioneFork(AdminAPIView):
    """`POST /pratiche/definizioni/<id>/fork/` — crea l'edizione BOZZA di un
    emittente dalla definizione (di solito il preset), con provenance per il drift."""

    @extend_schema(
        request=inline_serializer(
            name="PraticheDefinizioneForkReq",
            fields={"emittente_fiscale_id": serializers.IntegerField()},
        ),
        responses={200: inline_serializer(
            name="PraticheDefinizioneForkResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def post(self, request: Request, definizione_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return definizioni_service.fork_definizione(
                definizione_id, int(payload.get("emittente_fiscale_id") or 0),
            )
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiDefinizioneNuovaVersione(AdminAPIView):
    """`POST /pratiche/definizioni/<id>/nuova-versione/` — nuova versione BOZZA
    dello stesso scope (per editare una PUBBLICATA senza toccarla)."""

    @extend_schema(responses={200: inline_serializer(
        name="PraticheDefinizioneNuovaVersioneResp",
        fields={"data": serializers.DictField()},
    )})
    def post(self, request: Request, definizione_id: int) -> JsonResponse:
        def _handler(_payload: dict[str, object]) -> dict[str, object]:
            return definizioni_service.nuova_versione_definizione(definizione_id)
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiDefinizionePubblica(AdminAPIView):
    """`POST /pratiche/definizioni/<id>/pubblica/` — pubblica una BOZZA (→ PUBBLICATA;
    la precedente dello scope → RITIRATA)."""

    @extend_schema(responses={200: inline_serializer(
        name="PraticheDefinizionePubblicaResp",
        fields={"data": serializers.DictField()},
    )})
    def post(self, request: Request, definizione_id: int) -> JsonResponse:
        def _handler(_payload: dict[str, object]) -> dict[str, object]:
            return definizioni_service.pubblica_definizione(definizione_id)
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)
