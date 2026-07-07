# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API read-only Lente 1 Competenza (aggregata mensile + drill-down
#        attivita' + errori vivi) — cruscotti fatturazione a due lenti.
# ------------------------------------------------------------

# Tre endpoint GET sottili sopra le viste vendite.vw_dash_competenza_*
# (brief brief-design-fatturazione-due-lenti §4, DB in
# brief-db-fatturazione-due-lenti §4). Livello LETTURA sufficiente;
# lo scope emittente e' interamente DB-side (GUC fail-closed nelle viste).

from datetime import date

from django.http import JsonResponse
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.payload_validators import (
    qp_bool_optional,
    qp_int_strict,
    qp_iso_date_optional,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.vendite.services.vendite_service import (
    fn_dash_competenza_attivita,
    fn_dash_competenza_errori,
    fn_dash_competenza_mensile,
)


class ApiDashboardCompetenza(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/ — 12 mesi × 4 stadi funnel."""

    area_funzionale = "vendite"

    @extend_schema(
        operation_id="vendite_dashboard_competenza",
        parameters=[
            OpenApiParameter(
                name="anno",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Anno di competenza (default: anno corrente; range 2000-2100).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeDashCompetenzaResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaData",
                        fields={
                            "anno": serializers.IntegerField(),
                            "mesi": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET l'aggregata annuale della Lente Competenza
    #        (12 mesi sempre presenti, 4 stadi per mese con breakdown stato
    #        fattura sul FATTURATA + conteggio errori vivi per mese).
    def get(self, request: Request) -> JsonResponse:
        anno = qp_int_strict(
            request.query_params.get("anno"), "anno", date.today().year
        )
        data = fn_dash_competenza_mensile(anno=anno)
        return success_response(data)


class ApiDashboardCompetenzaAttivita(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/attivita/ — drill-down attivita'."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_competenza_attivita",
        parameters=[
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Mese di competenza ISO (YYYY-MM-DD, normalizzato al 1° del mese).",
            ),
            OpenApiParameter(
                name="stadio",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro stadio funnel: DA_APPROVARE | DA_EMETTERE | "
                    "EMESSA_NON_FATTURATA | FATTURATA (default: tutti)."
                ),
            ),
            OpenApiParameter(
                name="solo_ritardo",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Se true, solo attivita' emesse in ritardo (recuperi tardivi).",
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Numero pagina (default 1).",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Dimensione pagina (default 50, max 200).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeDashCompetenzaAttivitaResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaAttivitaData",
                        fields={
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "results": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET la lista paginata delle attivita' del mese di
    #        competenza richiesto (drill-down card stadio della Lente 1).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        competenza_mese = qp_iso_date_optional(qp.get("competenza_mese"), "competenza_mese")
        ErrorManager.require(
            competenza_mese is not None,
            code="E_VENDITE_VALIDATION",
            message="Parametro competenza_mese obbligatorio.",
            function_name="vendite.api.views_dashboard_competenza.attivita",
        )
        assert competenza_mese is not None
        stadio = qp_str_upper(qp.get("stadio"))
        solo_ritardo = qp_bool_optional(qp.get("solo_ritardo"), "solo_ritardo")
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        # Scope emittente interamente DB-side (GUC fail-closed nella vista):
        # la view non passa alcun auth_user_id.
        data = fn_dash_competenza_attivita(
            competenza_mese=competenza_mese,
            stadio=stadio,
            solo_ritardo=bool(solo_ritardo),
            page=page,
            page_size=page_size,
        )
        return success_response(data)


class ApiDashboardCompetenzaErrori(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/errori/ — errori vivi fatturazione."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_competenza_errori",
        parameters=[
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Mese di competenza ISO (YYYY-MM-DD, normalizzato al 1° del mese); "
                    "assente = errori vivi di tutti i mesi."
                ),
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Numero pagina (default 1).",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Dimensione pagina (default 50, max 200).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeDashCompetenzaErroriResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaErroriData",
                        fields={
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "results": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET la lista paginata degli errori vivi della
    #        fatturazione (task run in ERRORE non superati + fatture critical),
    #        opzionalmente filtrata per mese di competenza (blocco 4 Lente 1).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        competenza_mese = qp_iso_date_optional(qp.get("competenza_mese"), "competenza_mese")
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        data = fn_dash_competenza_errori(
            competenza_mese=competenza_mese,
            page=page,
            page_size=page_size,
        )
        return success_response(data)
