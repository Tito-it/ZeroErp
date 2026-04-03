# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view per parametri di sistema con risoluzione override.
#        Endpoint:
#        - GET  /api/v1/core/parameters/defaults/   — risoluzione N parametri
#        - GET  /api/v1/core/parameters/settings/    — lista parametri per utente con livelli
#        - POST /api/v1/core/parameters/settings/override/  — upsert override personale
#        - DELETE /api/v1/core/parameters/settings/override/<id>/ — rimuovi override
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.db.parameter_repository import MAX_CODES
from apps.core.services.parameter_service import ParameterService


# Scopo: Helper per estrarre contesto utente per risoluzione parametri.
#        Superuser: nessun filtro (vede default globali).
#        Operatore: user_id, group_ids, emittente_fiscale_id.
def _get_user_context(request: Request, svc: ParameterService) -> dict:
    user = request.user
    if user.is_superuser:
        return {
            "django_user_id": None,
            "group_ids": None,
            "emittente_fiscale_id": None,
        }
    return {
        "django_user_id": user.id,
        "group_ids": list(user.groups.values_list("id", flat=True)),
        "emittente_fiscale_id": svc.get_emittente_fiscale_id_for_user(user.id),
    }


class ParameterDefaultsView(DomainAPIView):
    """Risolve N parametri di sistema con override per l'utente loggato."""

    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="codes",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Codici parametro separati da virgola (es. DEFAULT_IVA_ID,DEFAULT_CURRENCY).",
                required=True,
            ),
        ],
        responses={
            200: inline_serializer(
                name="ParameterDefaultsResponse",
                fields={
                    "data": serializers.DictField(
                        child=serializers.CharField(),
                        help_text="Mappa {code: valore_risolto}",
                    ),
                },
            )
        },
    )
    # Scopo: Restituisce i valori risolti (con override utente) per i codici richiesti.
    #        I codici non trovati vengono esclusi dal risultato.
    def get(self, request: Request) -> JsonResponse:
        raw_codes = request.query_params.get("codes", "")
        codes = [c.strip() for c in raw_codes.split(",") if c.strip()]
        if not codes:
            return success_response({})
        codes = codes[:MAX_CODES]

        svc = ParameterService()
        ctx = _get_user_context(request, svc)
        defaults = svc.get_defaults(codes, **ctx)
        return success_response(defaults)


class ParameterSettingsView(DomainAPIView):
    """Lista parametri con valori a ogni livello di scope per l'utente loggato."""

    skip_area_check = True

    @extend_schema(
        summary="Lista parametri con livelli override",
        description=(
            "Restituisce tutti i parametri di sistema con i valori a ogni livello "
            "(default, emittente, gruppo, utente) e il valore risolto finale."
        ),
        responses={
            200: inline_serializer(
                name="ParameterSettingsResponse",
                fields={
                    "data": serializers.ListField(
                        child=serializers.DictField(),
                        help_text="Lista parametri con livelli override",
                    ),
                },
            )
        },
    )
    # Scopo: Restituisce la lista completa dei parametri con i valori a ogni
    #        livello di scope e il valore risolto finale per l'utente corrente.
    def get(self, request: Request) -> JsonResponse:
        svc = ParameterService()
        ctx = _get_user_context(request, svc)

        parameters = svc.list_parameters_for_user(
            django_user_id=ctx["django_user_id"] or request.user.id,
            group_ids=ctx["group_ids"],
            emittente_fiscale_id=ctx["emittente_fiscale_id"],
        )
        return success_response(parameters)


class ParameterOverrideView(DomainAPIView):
    """Crea/aggiorna un override personale dell'utente per un parametro."""

    skip_area_check = True

    @extend_schema(
        summary="Crea o aggiorna override personale",
        request=inline_serializer(
            name="ParameterOverrideRequest",
            fields={
                "parameter_code": serializers.CharField(
                    help_text="Codice del parametro da sovrascrivere",
                ),
                "value": serializers.CharField(
                    help_text="Nuovo valore dell'override",
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="ParameterOverrideResponse",
                fields={
                    "data": serializers.DictField(
                        help_text="ID dell'override creato/aggiornato",
                    ),
                },
            )
        },
    )
    # Scopo: Crea o aggiorna un override personale dell'utente corrente.
    def post(self, request: Request) -> JsonResponse:
        svc = ParameterService()

        def handler(payload: dict) -> dict:
            raw_value = payload.get("value")
            override_id = svc.upsert_user_override(
                parameter_code=payload.get("parameter_code", ""),
                django_user_id=request.user.id,
                value=str(raw_value) if raw_value is not None else "",
            )
            return {"override_id": override_id}

        return handle_post_json(request, handler=handler)


class ParameterOverrideDeleteView(DomainAPIView):
    """Rimuove un override personale dell'utente."""

    skip_area_check = True

    @extend_schema(
        summary="Rimuovi override personale",
        responses={
            200: inline_serializer(
                name="ParameterOverrideDeleteResponse",
                fields={
                    "data": serializers.DictField(
                        help_text="Conferma eliminazione",
                    ),
                },
            )
        },
    )
    # Scopo: Rimuove un override personale dell'utente corrente.
    def delete(self, request: Request, override_id: int) -> JsonResponse:
        svc = ParameterService()
        svc.delete_user_override(
            override_id=override_id,
            django_user_id=request.user.id,
        )
        return success_response({"deleted": True})
