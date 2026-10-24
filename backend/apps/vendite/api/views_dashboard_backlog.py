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

from django.http import HttpResponse, JsonResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.openapi_params import parametri_finestra
from apps.core.api.base_views import DomainAPIView
from apps.core.api.payload_validators import pagina_da_query, qp_int_optional, qp_str, qp_str_upper
from apps.core.api.success_responses import success_response
from apps.core.services.payload_helpers import INTEGER_MAX, INTEGER_MIN
from apps.vendite.api.dash_export_helpers import build_dash_export_response
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
    lista_codice = "vendite.dash_backlog_documenti"

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
                    "Filtro area funnel, col codice della sorgente: PREVENTIVO | "
                    "ORDINE_VENDITA | DDT_VENDITA | OFFERTA_COMMERCIALE | CONTRATTO | "
                    "COMMESSA | RESO_VENDITA (default: tutte)."
                ),
            ),
            OpenApiParameter(
                name="ritardo_giorni",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Soglia \"fermo da oltre N giorni\" su data documento: "
                    "tiene solo i documenti con data_riferimento <= oggi - N "
                    "(stessa semantica del filtro ritardo della Situazione "
                    "aperta). Solo sulla lista; le card per classe restano la "
                    "fotografia completa. Strict: non numerico -> 400; "
                    "intero <= 0 -> 400 (E_VENDITE_VALIDATION)."
                ),
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): anzianita_giorni "
                    "(default, \"fermo da\") | area | codice | cliente_display | "
                    "valore_fermo | stato_codice. Ordinamento server-side su "
                    "tutte le pagine. Colonna non ammessa -> 400."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Direzione ordinamento: asc | desc (default desc per "
                    "anzianita_giorni: i piu' \"fermo da\" prima). Valore "
                    "diverso -> 400 (E_VENDITE_VALIDATION)."
                ),
            ),
            *parametri_finestra(),
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
        classe = qp_str_upper(qp.get("classe"))
        area = qp_str_upper(qp.get("area"))
        # Filtro "fermo da oltre N giorni" (strict: non numerico -> 400). Solo
        # sul drill-down; le card per classe restano la fotografia completa.
        ritardo_giorni = qp_int_optional(
            qp.get("ritardo_giorni"), "ritardo_giorni",
            min_val=INTEGER_MIN, max_val=INTEGER_MAX,
        )
        # Ordinamento (convenzione order_by/order_dir): whitelist + direzione
        # validate nel service (unica definizione, fail-fast 400).
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        limit, offset = pagina_da_query(qp)

        # Scope emittente interamente DB-side (RLS invoker + GUC commesse):
        # la view non passa alcun auth_user_id.
        data = fn_dash_backlog_documenti(
            classe=classe,
            area=area,
            ritardo_giorni=ritardo_giorni,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiDashboardBacklogDocumentiExport(DomainAPIView):
    """GET /api/v1/vendite/dashboard-backlog/documenti/export/?formato=csv|xlsx

    Esporta la STESSA lista del drill-down backlog, con gli stessi filtri.
    Colonne e ordine vengono dal catalogo `vendite.dash_backlog_documenti`
    risolto sulla configurazione dell'operatore: il file e' quello che ha a
    video, non una lista fissa nel codice. Hard cap 10.000 righe.

    NB: il parametro si chiama `formato` (italiano) NON `format` — magic
    parameter DRF (content-negotiation) che intercetterebbe la chiamata.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.dash_backlog_documenti"

    @extend_schema(
        operation_id="vendite_dashboard_backlog_documenti_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="classe", type=str, required=False),
            OpenApiParameter(name="area", type=str, required=False),
            OpenApiParameter(name="ritardo_giorni", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    # Scopo: Genera il file (CSV/XLSX) del drill-down backlog. Stessi filtri e
    #        stesso ordinamento del GET di lista: l'export non e' una seconda
    #        query con criteri propri, e' la stessa lista scritta su file.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        return build_dash_export_response(
            request,
            lista_codice="vendite.dash_backlog_documenti",
            fetch=fn_dash_backlog_documenti,
            filtri={
                "classe": qp_str_upper(qp.get("classe")),
                "area": qp_str_upper(qp.get("area")),
                "ritardo_giorni": qp_int_optional(
                    qp.get("ritardo_giorni"), "ritardo_giorni",
                    min_val=INTEGER_MIN, max_val=INTEGER_MAX,
                ),
                "order_by": qp_str(qp.get("order_by")),
                "order_dir": qp_str(qp.get("order_dir")),
            },
        )
