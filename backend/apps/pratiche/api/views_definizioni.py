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

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import corpo_oggetto, qp_int_optional
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


class ApiDefinizioneDettaglio(AdminAPIView):
    """`GET /pratiche/definizioni/<id>/` — dettaglio editing di un'edizione:
    header (con drift) + steps ordinati. Base della UI editing BOZZA (Slice 2).
    Solo super-admin. 404 se l'id non esiste."""

    @extend_schema(
        responses={200: inline_serializer(
            name="PraticheDefinizioneDettaglioResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: dettaglio edizione (header + steps) per la UI editing.
    def get(self, request: Request, definizione_id: int) -> JsonResponse:
        dettaglio = definizioni_service.get_definizione_dettaglio(definizione_id)
        return success_response(dettaglio)


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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return definizioni_service.fork_definizione(
                definizione_id, int(payload.get("emittente_fiscale_id") or 0),
            )
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiDefinizioneNuovaVersione(AdminAPIView):
    """`POST /pratiche/definizioni/<id>/nuova-versione/` — nuova versione BOZZA
    dello stesso scope (per editare una PUBBLICATA senza toccarla)."""

    @extend_schema(request=None, responses={200: inline_serializer(
        name="PraticheDefinizioneNuovaVersioneResp",
        fields={"data": serializers.DictField()},
    )})
    def post(self, request: Request, definizione_id: int) -> JsonResponse:
        def _handler(_payload: dict[str, Any]) -> dict[str, Any]:
            return definizioni_service.nuova_versione_definizione(definizione_id)
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiDefinizionePubblica(AdminAPIView):
    """`POST /pratiche/definizioni/<id>/pubblica/` — pubblica una BOZZA (→ PUBBLICATA;
    la precedente dello scope → RITIRATA)."""

    @extend_schema(request=None, responses={200: inline_serializer(
        name="PraticheDefinizionePubblicaResp",
        fields={"data": serializers.DictField()},
    )})
    def post(self, request: Request, definizione_id: int) -> JsonResponse:
        def _handler(_payload: dict[str, Any]) -> dict[str, Any]:
            return definizioni_service.pubblica_definizione(definizione_id)
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# --- Editing strutturale step su BOZZA (Slice 2 anello 3) ---------------------
# CRUD dei campi core di uno step. L'immutabilità (edizione per-emittente emessa)
# è enforce dai guard DB (marker TEMPLATE_DEFINIZIONE_CONGELATA → banner). Solo super-admin.
_STEP_CORE_SCHEMA = inline_serializer(
    name="PraticheStepCoreReq",
    fields={
        "codice": serializers.CharField(),
        "descrizione": serializers.CharField(),
        "sequenza": serializers.IntegerField(required=False),
        "obbligatorio": serializers.BooleanField(required=False),
        "direzione": serializers.CharField(required=False),
        "modalita_esito": serializers.CharField(required=False),
        "esito_default": serializers.CharField(required=False, allow_null=True),
    },
)


class ApiDefinizioneSteps(AdminAPIView):
    """`POST /pratiche/definizioni/<id>/steps/` — crea uno step (campi core) nella BOZZA."""

    @extend_schema(request=_STEP_CORE_SCHEMA, responses={200: inline_serializer(
        name="PraticheStepCreateResp", fields={"data": serializers.DictField()},
    )})
    def post(self, request: Request, definizione_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return definizioni_service.create_step(definizione_id, dict(payload))
        return handle_post_json(request, handler=_handler)


class ApiDefinizioneStepDetail(AdminAPIView):
    """`PATCH/DELETE /pratiche/definizioni/<id>/steps/<step_id>/` — aggiorna i campi
    core o cancella (hard) uno step della BOZZA."""

    @extend_schema(request=_STEP_CORE_SCHEMA, responses={200: inline_serializer(
        name="PraticheStepUpdateResp", fields={"data": serializers.DictField()},
    )})
    def patch(self, request: Request, definizione_id: int, step_id: int) -> JsonResponse:
        return success_response(
            definizioni_service.update_step(definizione_id, step_id, corpo_oggetto(request))
        )

    @extend_schema(responses={200: inline_serializer(
        name="PraticheStepDeleteResp", fields={"data": serializers.DictField()},
    )})
    def delete(self, request: Request, definizione_id: int, step_id: int) -> JsonResponse:
        return success_response(definizioni_service.delete_step(definizione_id, step_id))


# --- Figli per-nodo di uno step su BOZZA (Slice 2 anello 4) -------------------
# Una coppia di view generiche parametrizzate da `child_kind` (canali /
# handler_eventi / competenze), passato dalla urlconf (allowlist fissa).
_FIGLIO_SCHEMA = inline_serializer(
    name="PraticheStepFiglioReq", fields={"__campi__": serializers.DictField()},
)


class ApiDefinizioneStepFigli(AdminAPIView):
    """`POST /pratiche/definizioni/<id>/steps/<step_id>/{canali|handler-eventi|competenze}/`
    — aggiunge un figlio per-nodo allo step della BOZZA."""

    @extend_schema(request=_FIGLIO_SCHEMA, responses={200: inline_serializer(
        name="PraticheStepFiglioCreateResp", fields={"data": serializers.DictField()},
    )})
    def post(self, request: Request, definizione_id: int, step_id: int,
             child_kind: str) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return definizioni_service.create_step_figlio(
                definizione_id, step_id, child_kind, dict(payload))
        return handle_post_json(request, handler=_handler)


class ApiDefinizioneStepFiglioDetail(AdminAPIView):
    """`PATCH/DELETE .../steps/<step_id>/<kind>/<row_id>/` — aggiorna o cancella
    (hard) un figlio per-nodo dello step della BOZZA."""

    @extend_schema(request=_FIGLIO_SCHEMA, responses={200: inline_serializer(
        name="PraticheStepFiglioUpdateResp", fields={"data": serializers.DictField()},
    )})
    def patch(self, request: Request, definizione_id: int, step_id: int,
              child_kind: str, row_id: int) -> JsonResponse:
        return success_response(definizioni_service.update_step_figlio(
            definizione_id, step_id, child_kind, row_id, corpo_oggetto(request)))

    @extend_schema(responses={200: inline_serializer(
        name="PraticheStepFiglioDeleteResp", fields={"data": serializers.DictField()},
    )})
    def delete(self, request: Request, definizione_id: int, step_id: int,
               child_kind: str, row_id: int) -> JsonResponse:
        return success_response(definizioni_service.delete_step_figlio(
            definizione_id, step_id, child_kind, row_id))


# --- Archi del grafo di una BOZZA (Slice 2 anello 5) -------------------------
# Gli archi vivono al livello edizione (collegano due step); `edge_kind` (prerequisiti
# / formule_tempo / regole_generazione) è passato dalla urlconf (allowlist fissa).
_ARCO_SCHEMA = inline_serializer(
    name="PraticheArcoReq", fields={"__campi__": serializers.DictField()},
)


class ApiDefinizioneArchi(AdminAPIView):
    """`POST /pratiche/definizioni/<id>/archi/{prerequisiti|formule-tempo|regole-generazione}/`
    — aggiunge un arco al grafo della BOZZA."""

    @extend_schema(request=_ARCO_SCHEMA, responses={200: inline_serializer(
        name="PraticheArcoCreateResp", fields={"data": serializers.DictField()},
    )})
    def post(self, request: Request, definizione_id: int, edge_kind: str) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return definizioni_service.create_arco(definizione_id, edge_kind, dict(payload))
        return handle_post_json(request, handler=_handler)


class ApiDefinizioneArcoDetail(AdminAPIView):
    """`PATCH/DELETE .../archi/<kind>/<row_id>/` — aggiorna o cancella (hard) un
    arco del grafo della BOZZA."""

    @extend_schema(request=_ARCO_SCHEMA, responses={200: inline_serializer(
        name="PraticheArcoUpdateResp", fields={"data": serializers.DictField()},
    )})
    def patch(self, request: Request, definizione_id: int, edge_kind: str,
              row_id: int) -> JsonResponse:
        return success_response(
            definizioni_service.update_arco(definizione_id, edge_kind, row_id, corpo_oggetto(request))
        )

    @extend_schema(responses={200: inline_serializer(
        name="PraticheArcoDeleteResp", fields={"data": serializers.DictField()},
    )})
    def delete(self, request: Request, definizione_id: int, edge_kind: str,
               row_id: int) -> JsonResponse:
        return success_response(definizioni_service.delete_arco(definizione_id, edge_kind, row_id))
