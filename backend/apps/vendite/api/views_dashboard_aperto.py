# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from apps.core.api.payload_validators import (
    pagina_da_query,
    qp_int_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.core.services.payload_helpers import INTEGER_MAX, INTEGER_MIN
from apps.vendite.api.dash_export_helpers import build_dash_export_response
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
    lista_codice = "vendite.dash_aperto_documenti"

    @extend_schema(
        operation_id="vendite_dashboard_aperto_documenti",
        parameters=[
            OpenApiParameter(
                name="area",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro area documento, col codice della sorgente: PREVENTIVO | "
                    "ORDINE_VENDITA | DDT_VENDITA | OFFERTA_COMMERCIALE | CONTRATTO "
                    "(default: tutte). Un codice che non e' una sorgente "
                    "(config.sorgenti) e' 400 E_VENDITE_VALIDATION. Una sorgente "
                    "fuori da queste cinque e' ammessa (il riepilogo la accoda, "
                    "fail-visible); COMMESSA, esclusa dalla vista, da' lista vuota."
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
                    "Fuori vocabolario e' 400 E_VENDITE_VALIDATION; CHIUSO e' "
                    "ammessa ma la vista non la contiene (lista vuota)."
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
            *parametri_finestra(),
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
        ritardo_giorni = qp_int_optional(
            qp.get("ritardo_giorni"), "ritardo_giorni",
            min_val=INTEGER_MIN, max_val=INTEGER_MAX,
        )
        # Ordinamento (convenzione order_by/order_dir): whitelist + direzione
        # validate nel service (unica definizione, fail-fast 400).
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        limit, offset = pagina_da_query(qp)

        # Scope emittente interamente DB-side (RLS invoker): la view non
        # passa alcun auth_user_id.
        data = fn_dash_aperto_documenti(
            area=area,
            fase=fase,
            ritardo_giorni=ritardo_giorni,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiDashboardApertoDocumentiExport(DomainAPIView):
    """GET /api/v1/vendite/dashboard-aperto/documenti/export/?formato=csv|xlsx

    Esporta la STESSA lista del drill-down situazione aperta, con gli stessi
    filtri. Colonne e ordine dal catalogo `vendite.dash_aperto_documenti`
    risolto sulla configurazione dell'operatore. Hard cap 10.000 righe.

    NB: il parametro si chiama `formato` (italiano) NON `format` — magic
    parameter DRF (content-negotiation) che intercetterebbe la chiamata.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.dash_aperto_documenti"

    @extend_schema(
        operation_id="vendite_dashboard_aperto_documenti_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="area", type=str, required=False),
            OpenApiParameter(name="fase", type=str, required=False),
            OpenApiParameter(name="ritardo_giorni", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    # Scopo: Genera il file (CSV/XLSX) del drill-down situazione aperta.
    #        Stessi filtri e stesso ordinamento del GET di lista.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        return build_dash_export_response(
            request,
            lista_codice="vendite.dash_aperto_documenti",
            fetch=fn_dash_aperto_documenti,
            filtri={
                "area": qp_str_upper(qp.get("area")),
                "fase": qp_str_upper(qp.get("fase")),
                "ritardo_giorni": qp_int_optional(
                    qp.get("ritardo_giorni"), "ritardo_giorni",
                    min_val=INTEGER_MIN, max_val=INTEGER_MAX,
                ),
                "order_by": qp_str(qp.get("order_by")),
                "order_dir": qp_str(qp.get("order_dir")),
            },
        )
