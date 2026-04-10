# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view per parametri di sistema con risoluzione override.
#        Endpoint:
#        - GET    /api/v1/core/parameters/defaults/                — risoluzione N parametri
#        - GET    /api/v1/core/parameters/settings/                — lista parametri per utente con livelli
#        - POST   /api/v1/core/parameters/settings/override/       — upsert override personale o emittente
#        - DELETE /api/v1/core/parameters/settings/override/<id>/  — rimuovi override personale o emittente
#        Lo scope ('user'|'emittente') determina la fascia di applicazione.
#        Lo scope 'emittente' e' riservato agli amministratori.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.permissions import IsAdminZeroERP
from apps.core.api.success_responses import success_response
from apps.core.db.parameter_repository import MAX_CODES
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService

# Scope override consentiti dal payload del POST.
SCOPE_USER = "user"
SCOPE_EMITTENTE = "emittente"
ALLOWED_SCOPES = (SCOPE_USER, SCOPE_EMITTENTE)


# Scopo: Verifica che l'utente corrente sia ADMIN o superuser.
#        Riusa la logica di IsAdminZeroERP (l'argomento `view` non e' usato
#        dall'implementazione, quindi passare None e' sicuro per questo check).
def _is_admin(request: Request) -> bool:
    return IsAdminZeroERP().has_permission(request, view=None)


# Scopo: Verifica che l'operazione su scope='emittente' sia consentita e
#        restituisce l'emittente_fiscale_id da usare per l'override.
#        Solleva E_PERMISSION_DENIED se non admin, E_PARAMETER_VALIDATION
#        se l'utente non e' associato ad alcun emittente.
#        Centralizza il controllo riusato da POST e DELETE.
def _require_admin_emittente_id(request: Request, svc: ParameterService) -> int:
    ErrorManager.require(
        _is_admin(request),
        code="E_PERMISSION_DENIED",
        message="Solo gli amministratori possono operare sugli override a livello emittente.",
    )
    emittente_fiscale_id = svc.get_emittente_fiscale_id_for_user(request.user.id)
    ErrorManager.require(
        emittente_fiscale_id is not None,
        code="E_PARAMETER_VALIDATION",
        message="Emittente fiscale non risolvibile per l'utente corrente.",
    )
    return emittente_fiscale_id  # type: ignore[return-value]


# Scopo: Normalizza e valida lo scope ricevuto da payload o query string.
#        Default 'user' se assente. Solleva E_PARAMETER_VALIDATION se non valido.
def _parse_scope(raw: str | None) -> str:
    scope = (raw or SCOPE_USER).strip().lower()
    ErrorManager.require(
        scope in ALLOWED_SCOPES,
        code="E_PARAMETER_VALIDATION",
        message=f"Scope override non valido: '{scope}'.",
    )
    return scope


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
    #        Per la lista settings, risolve sempre django_user_id e
    #        emittente_fiscale_id anche per superuser, altrimenti il LEFT JOIN
    #        su emittente_fiscale_id = NULL non matcha mai (NULL = NULL e' false
    #        in SQL) e gli override emittente non vengono mostrati.
    def get(self, request: Request) -> JsonResponse:
        svc = ParameterService()
        ctx = _get_user_context(request, svc)

        # Fallback per superuser: risolve sempre user e emittente reali.
        django_user_id = ctx["django_user_id"] or request.user.id
        emittente_fiscale_id = ctx["emittente_fiscale_id"] or svc.get_emittente_fiscale_id_for_user(request.user.id)

        parameters = svc.list_parameters_for_user(
            django_user_id=django_user_id,
            group_ids=ctx["group_ids"],
            emittente_fiscale_id=emittente_fiscale_id,
        )
        return success_response(parameters)


class ParameterOverrideView(DomainAPIView):
    """Crea/aggiorna un override per un parametro a scope personale o emittente.

    Scope ammessi:
    - "user"      → override personale (default per qualunque utente)
    - "emittente" → override valido per tutti gli utenti dell'emittente corrente
                    (riservato agli admin)
    """

    skip_area_check = True

    @extend_schema(
        summary="Crea o aggiorna override parametro",
        request=inline_serializer(
            name="ParameterOverrideRequest",
            fields={
                "parameter_code": serializers.CharField(
                    help_text="Codice del parametro da sovrascrivere",
                ),
                "value": serializers.CharField(
                    help_text="Nuovo valore dell'override",
                ),
                "scope": serializers.ChoiceField(
                    choices=list(ALLOWED_SCOPES),
                    required=False,
                    help_text="Scope: 'user' (default) o 'emittente' (solo admin)",
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="ParameterOverrideResponse",
                fields={
                    "data": serializers.DictField(
                        help_text="ID dell'override creato/aggiornato + scope",
                    ),
                },
            )
        },
    )
    # Scopo: Crea o aggiorna un override per il parametro indicato.
    #        Lo scope determina la fascia di applicazione (user/emittente).
    def post(self, request: Request) -> JsonResponse:
        svc = ParameterService()

        def handler(payload: dict) -> dict:
            scope = _parse_scope(payload.get("scope"))
            raw_value = payload.get("value")
            value = str(raw_value) if raw_value is not None else ""
            parameter_code = payload.get("parameter_code", "")

            if scope == SCOPE_EMITTENTE:
                emittente_fiscale_id = _require_admin_emittente_id(request, svc)
                override_id = svc.upsert_emittente_override(
                    parameter_code=parameter_code,
                    emittente_fiscale_id=emittente_fiscale_id,
                    value=value,
                )
            else:
                override_id = svc.upsert_user_override(
                    parameter_code=parameter_code,
                    django_user_id=request.user.id,
                    value=value,
                )

            return {"override_id": override_id, "scope": scope}

        return handle_post_json(request, handler=handler)


class ParameterOverrideDeleteView(DomainAPIView):
    """Rimuove un override (personale o emittente) per un parametro.

    Lo scope viene passato come query string ?scope=user|emittente
    (default 'user'). Lo scope 'emittente' richiede ruolo admin.
    """

    skip_area_check = True

    @extend_schema(
        summary="Rimuovi override parametro",
        parameters=[
            OpenApiParameter(
                name="scope",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Scope dell'override: 'user' (default) o 'emittente'.",
                required=False,
            ),
        ],
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
    # Scopo: Rimuove un override per il parametro indicato.
    def delete(self, request: Request, override_id: int) -> JsonResponse:
        svc = ParameterService()
        scope = _parse_scope(request.query_params.get("scope"))

        if scope == SCOPE_EMITTENTE:
            emittente_fiscale_id = _require_admin_emittente_id(request, svc)
            svc.delete_emittente_override(
                override_id=override_id,
                emittente_fiscale_id=emittente_fiscale_id,
            )
        else:
            svc.delete_user_override(
                override_id=override_id,
                django_user_id=request.user.id,
            )

        return success_response({"deleted": True, "scope": scope})
