# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API read-only Situazione aperta (stock documenti per fase, senza
#        asse temporale) — terza vista dei cruscotti fatturazione (§6-bis).
# ------------------------------------------------------------

# Due endpoint GET sottili sopra le viste vendite.vw_dash_aperto_*
# (design brief-design-fatturazione-due-lenti §6-bis, DB in
# brief-db-situazione-aperta). Livello LETTURA sufficiente; lo scope
# emittente e' interamente DB-side (RLS invoker sulle 4 aree documento).

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
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.vendite.services.vendite_service import (
    fn_dash_aperto_documenti,
    fn_dash_aperto_riepilogo,
)


class ApiDashboardAperto(DomainAPIView):
    """GET /api/v1/vendite/dashboard-aperto/ — riepilogo stock area × fase."""

    area_funzionale = "vendite"

    @extend_schema(
        operation_id="vendite_dashboard_aperto",
        responses={
            200: inline_serializer(
                name="VenditeDashApertoResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashApertoData",
                        fields={
                            "aree": serializers.ListField(child=serializers.DictField()),
                            "fasi": serializers.ListField(child=serializers.CharField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il riepilogo dello stock documenti aperto:
    #        4 aree documento sempre presenti (ordine funnel), ognuna con
    #        totali e griglia per fase normalizzata (ordine ciclo di vita),
    #        piu' il vocabolario `fasi` per i filtri FE.
    def get(self, request: Request) -> JsonResponse:
        data = fn_dash_aperto_riepilogo()
        return success_response(data)


class ApiDashboardApertoDocumenti(DomainAPIView):
    """GET /api/v1/vendite/dashboard-aperto/documenti/ — drill-down stock."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_aperto_documenti",
        parameters=[
            OpenApiParameter(
                name="area",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro area documento: PREVENTIVI | ORDINI | OFFERTE | "
                    "CONTRATTI (default: tutte). Non whitellistato: un'area "
                    "sconosciuta (o COMMESSE, esclusa dalla vista — coperta "
                    "dalla Lente 1) da' lista vuota (coerenza fail-visible "
                    "col riepilogo, che accoda le aree fuori whitelist)."
                ),
            ),
            OpenApiParameter(
                name="fase",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro fase normalizzata (vocabolario config.stati_doc_*: "
                    "APERTO | IN_ATTESA | IN_CORSO | CHIUSO; default: tutte). "
                    "Non whitellistato: una fase sconosciuta da' lista vuota "
                    "(coerenza fail-visible col riepilogo)."
                ),
            ),
            OpenApiParameter(
                name="solo_aperti",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Default true: solo documenti non completamente transitati "
                    "(is_aperto; il giudizio sospeso dei contratti conta "
                    "aperto). false = fotografia completa dello stock. "
                    "Strict: un token non riconosciuto da' 400 (niente "
                    "coercion silenziosa a true)."
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
                name="VenditeDashApertoDocumentiResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashApertoDocumentiData",
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
    # Scopo: Restituisce via GET la lista paginata dello stock aperto
    #        ordinata per "in essere da" (i piu' vecchi prima), con filtri
    #        area/fase/solo_aperti.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        area = qp_str_upper(qp.get("area"))
        fase = qp_str_upper(qp.get("fase"))
        # Strict (niente coercion silenziosa a True su token sconosciuti);
        # assente/vuoto -> None -> il default di pagina (True) lo applica il
        # service, unica definizione.
        solo_aperti = qp_bool_optional(qp.get("solo_aperti"), "solo_aperti")
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        # Scope emittente interamente DB-side (RLS invoker): la view non
        # passa alcun auth_user_id.
        data = fn_dash_aperto_documenti(
            area=area,
            fase=fase,
            solo_aperti=solo_aperti,
            page=page,
            page_size=page_size,
        )
        return success_response(data)
