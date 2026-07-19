# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API read-only serbatoio pre-commessa (stock documenti aperti-non-
#        chiusi per fase, senza asse temporale) — terza vista dei cruscotti
#        fatturazione (§6-ter).
# ------------------------------------------------------------

# Due endpoint GET sottili sopra le viste vendite.vw_dash_aperto_* v2
# (design brief-design-fatturazione-due-lenti §6-ter, DB in
# brief-db-situazione-aperta-v2). Livello LETTURA sufficiente; lo scope
# emittente e' interamente DB-side (RLS invoker sulle 5 aree documento).

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
    qp_int_optional,
    qp_int_strict,
    qp_str,
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
    #        5 aree documento sempre presenti (ordine funnel), ognuna con
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
                    "Filtro area documento: PREVENTIVI | ORDINI | DDT | "
                    "OFFERTE | CONTRATTI (default: tutte). Non whitellistato: un'area "
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
                    "APERTO | IN_ATTESA | IN_CORSO; default: tutte). Non "
                    "whitellistato: una fase sconosciuta da' lista vuota "
                    "(coerenza fail-visible col riepilogo)."
                ),
            ),
            OpenApiParameter(
                name="ritardo_giorni",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Soglia \"aperti da oltre N giorni\" su data documento "
                    "(DL-17): tiene solo i documenti con data_riferimento <= "
                    "oggi - N. Filtro del SOLO drill-down (le card del "
                    "riepilogo restano la fotografia completa). Strict: non "
                    "numerico -> 400; intero <= 0 -> 400 (E_VENDITE_VALIDATION)."
                ),
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): anzianita_giorni "
                    "(default, \"aperto da\") | codice | cliente_display | "
                    "valore_totale. Ordinamento server-side su tutte le pagine. "
                    "Colonna non ammessa -> 400 (E_VENDITE_VALIDATION)."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Direzione ordinamento: asc | desc (default desc per "
                    "anzianita_giorni: i piu' \"in essere da\" prima). Valore "
                    "diverso -> 400 (E_VENDITE_VALIDATION)."
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
    #        area/fase/ritardo_giorni.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        area = qp_str_upper(qp.get("area"))
        fase = qp_str_upper(qp.get("fase"))
        # Strict (presente-ma-non-numerico -> 400); assente/vuoto -> None ->
        # nessuna soglia. La guardia intero > 0 (E_VENDITE_VALIDATION) e' nel
        # service, unica definizione.
        ritardo_giorni = qp_int_optional(qp.get("ritardo_giorni"), "ritardo_giorni")
        # Ordinamento (convenzione order_by/order_dir): whitelist + direzione
        # validate nel service (unica definizione, fail-fast 400).
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        # Scope emittente interamente DB-side (RLS invoker): la view non
        # passa alcun auth_user_id.
        data = fn_dash_aperto_documenti(
            area=area,
            fase=fase,
            ritardo_giorni=ritardo_giorni,
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            page_size=page_size,
        )
        return success_response(data)
