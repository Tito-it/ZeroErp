# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API read-only Dashboard Fatturazione (matrice mensile + drill-down fermi).
# ------------------------------------------------------------

# Due endpoint GET sottili sopra le viste vendite.vw_dash_fatturazione_*
# (brief brief-design-dashboard-fatturazione §6). Livello LETTURA sufficiente;
# la RLS emittente filtra il perimetro via viste invoker.

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
    qp_int_strict,
    qp_iso_date_optional,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.vendite.services.vendite_service import (
    fn_dash_fatturazione_fermi,
    fn_dash_fatturazione_mensile,
)


class ApiDashboardFatturazione(DomainAPIView):
    """GET /api/v1/vendite/dashboard-fatturazione/ — matrice 12 mesi × 5 aree."""

    area_funzionale = "vendite"

    @extend_schema(
        operation_id="vendite_dashboard_fatturazione",
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
                name="VenditeDashFatturazioneResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashFatturazioneData",
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
    # Scopo: Restituisce via GET la matrice area × mese dell'anno richiesto
    #        (12 mesi sempre presenti, mesi vuoti con zeri — decisione D-5).
    def get(self, request: Request) -> JsonResponse:
        anno = qp_int_strict(
            request.query_params.get("anno"), "anno", date.today().year
        )
        data = fn_dash_fatturazione_mensile(anno=anno)
        return success_response(data)


class ApiDashboardFatturazioneFermi(DomainAPIView):
    """GET /api/v1/vendite/dashboard-fatturazione/fermi/ — drill-down elementi fermi."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_fatturazione_fermi",
        parameters=[
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Mese di competenza ISO (YYYY-MM-DD, normalizzato al 1° del mese).",
            ),
            OpenApiParameter(
                name="area",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Area funnel: PREVENTIVI | ORDINI | OFFERTE | CONTRATTI | COMMESSE.",
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
                name="VenditeDashFatturazioneFermiResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashFatturazioneFermiData",
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
    # Scopo: Restituisce via GET la lista paginata degli elementi fermi
    #        dell'area nel mese di competenza richiesto (drill-down card).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        competenza_mese = qp_iso_date_optional(qp.get("competenza_mese"), "competenza_mese")
        ErrorManager.require(
            competenza_mese is not None,
            code="E_VENDITE_VALIDATION",
            message="Parametro competenza_mese obbligatorio.",
            function_name="vendite.api.views_dashboard_fatturazione.fermi",
        )
        assert competenza_mese is not None
        area = (qp_str(qp.get("area")) or "").upper()
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        # Scope emittente interamente DB-side (RLS + filtro GUC nel resolver
        # commesse dal 20260703-60): la view non passa alcun auth_user_id.
        data = fn_dash_fatturazione_fermi(
            competenza_mese=competenza_mese,
            area=area,
            page=page,
            page_size=page_size,
        )
        return success_response(data)
