# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API read-only Lente 2 Backlog (contatori per classe + lista dei
#        non-collegati per anzianita') — cruscotti fatturazione a due lenti.
# ------------------------------------------------------------

# Due endpoint GET sottili sopra le viste vendite.vw_dash_backlog_*
# (brief brief-design-fatturazione-due-lenti §5, DB in
# brief-db-fatturazione-due-lenti §5). Livello LETTURA sufficiente;
# lo scope emittente e' interamente DB-side (RLS invoker + GUC commesse).

from django.http import JsonResponse
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.payload_validators import qp_int_strict, qp_str
from apps.core.api.success_responses import success_response
from apps.vendite.services.vendite_service import (
    fn_dash_backlog_documenti,
    fn_dash_backlog_riepilogo,
)


class ApiDashboardBacklog(DomainAPIView):
    """GET /api/v1/vendite/dashboard-backlog/ — contatori per classe di azionabilita'."""

    area_funzionale = "vendite"

    @extend_schema(
        operation_id="vendite_dashboard_backlog",
        responses={
            200: inline_serializer(
                name="VenditeDashBacklogResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashBacklogData",
                        fields={
                            "classi": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET i contatori di testata del backlog
    #        (🟠 recuperabile · 🔵 sollecito cliente · 🔴 anomalia, sempre
    #        presenti, con dettaglio per area).
    def get(self, request: Request) -> JsonResponse:
        data = fn_dash_backlog_riepilogo()
        return success_response(data)


class ApiDashboardBacklogDocumenti(DomainAPIView):
    """GET /api/v1/vendite/dashboard-backlog/documenti/ — lista per anzianita'."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_backlog_documenti",
        parameters=[
            OpenApiParameter(
                name="classe",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro classe azionabilita' (vocabolario config.motivi_fermo: "
                    "RECUPERABILE | SOLLECITO_CLIENTE | ANOMALIA; default: tutte). "
                    "Non whitellistato: una classe sconosciuta da' lista vuota "
                    "(coerenza fail-visible col riepilogo)."
                ),
            ),
            OpenApiParameter(
                name="area",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro area funnel: PREVENTIVI | ORDINI | OFFERTE | "
                    "CONTRATTI | COMMESSE (default: tutte)."
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
                name="VenditeDashBacklogDocumentiResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashBacklogDocumentiData",
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
    # Scopo: Restituisce via GET la lista paginata del backlog ordinata per
    #        anzianita' (i piu' vecchi prima), con filtri classe/area.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        classe_raw = qp_str(qp.get("classe"))
        classe = classe_raw.upper() if classe_raw else None
        area_raw = qp_str(qp.get("area"))
        area = area_raw.upper() if area_raw else None
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        # Scope emittente interamente DB-side (RLS invoker + GUC commesse):
        # la view non passa alcun auth_user_id.
        data = fn_dash_backlog_documenti(
            classe=classe,
            area=area,
            page=page,
            page_size=page_size,
        )
        return success_response(data)
