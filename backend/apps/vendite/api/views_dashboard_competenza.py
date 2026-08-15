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

from django.http import HttpResponse, JsonResponse
from drf_spectacular.types import OpenApiTypes
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
    qp_str,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.vendite.api.dash_export_helpers import build_dash_export_response
from apps.core.services.error_manager import ErrorManager
from apps.vendite.services.vendite_service import (
    fn_dash_competenza_attivita,
    fn_dash_competenza_commesse,
    fn_dash_competenza_errori,
    fn_dash_competenza_gruppi,
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
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): commessa_codice | "
                    "cliente_display | articolo_codice (ordina per la descrizione "
                    "mostrata) | data_attivita (default) | valore. Ordinamento "
                    "server-side su tutte le pagine. Colonna non ammessa -> 400."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Direzione ordinamento: asc | desc. Valore diverso -> 400 "
                    "(E_VENDITE_VALIDATION)."
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
        # Ordinamento (convenzione order_by/order_dir): whitelist + direzione
        # validate nel service (unica definizione, fail-fast 400).
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        # Scope emittente interamente DB-side (GUC fail-closed nella vista):
        # la view non passa alcun auth_user_id.
        data = fn_dash_competenza_attivita(
            competenza_mese=competenza_mese,
            stadio=stadio,
            solo_ritardo=bool(solo_ritardo),
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            page_size=page_size,
        )
        return success_response(data)


class ApiDashboardCompetenzaCommesse(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/commesse/ — drill-down per commessa."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_competenza_commesse",
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
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): commessa_codice | "
                    "cliente_display | n_attivita | valore_tot (default) | "
                    "data_attivita_max. Colonna non ammessa -> 400."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Direzione ordinamento: asc | desc. Valore diverso -> 400.",
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
                name="VenditeDashCompetenzaCommesseResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaCommesseData",
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
    # Scopo: Restituisce via GET la lista paginata AGGREGATA per commessa del
    #        mese/stadio di competenza (DEC-4: una riga per commessa; il dettaglio
    #        a grana attivita' resta nel drawer di gestione).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        competenza_mese = qp_iso_date_optional(qp.get("competenza_mese"), "competenza_mese")
        ErrorManager.require(
            competenza_mese is not None,
            code="E_VENDITE_VALIDATION",
            message="Parametro competenza_mese obbligatorio.",
            function_name="vendite.api.views_dashboard_competenza.commesse",
        )
        assert competenza_mese is not None
        stadio = qp_str_upper(qp.get("stadio"))
        solo_ritardo = qp_bool_optional(qp.get("solo_ritardo"), "solo_ritardo")
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        data = fn_dash_competenza_commesse(
            competenza_mese=competenza_mese,
            stadio=stadio,
            solo_ritardo=bool(solo_ritardo),
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            page_size=page_size,
        )
        return success_response(data)


class ApiDashboardCompetenzaGruppi(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/gruppi/ — gruppi fatturabili.

    L'unita' su cui l'operatore decide nella card «Da emettere»: un documento
    sorgente (PRV-0012, CTR-0007…) **oppure** gli oneri di una commessa, che
    documento non hanno e senza questa lista resterebbero lavoro conteggiato ma
    invisibile e non azionabile.

    La `gruppo_key` di ogni riga e' la stessa che si rimanda a
    `POST /vendite/fatturazione/run/` nel campo `gruppi`: non va costruita ne'
    trasformata dal client."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_competenza_gruppi",
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
                    "EMESSA_NON_FATTURATA | FATTURATA (default: tutti). Il "
                    "cockpit usa DA_EMETTERE."
                ),
            ),
            OpenApiParameter(
                name="tipo_gruppo",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro tipo documento/sorgente (assente = tutti): "
                    "codice_interno della sorgente (PREVENTIVO, ORDINE_VENDITA, "
                    "CONTRATTO, DDT_VENDITA, ...) oppure ONERI_COMMESSA per le "
                    "righe manuali senza documento. Le voci disponibili nel "
                    "perimetro sono nel blocco `tipi` della risposta."
                ),
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): riferimento | "
                    "tipo_gruppo | cliente_display | commessa_codice | "
                    "n_attivita | valore (default) | data_attivita_max. "
                    "Colonna non ammessa -> 400."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Direzione ordinamento: asc | desc. Valore diverso -> 400.",
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
                name="VenditeDashCompetenzaGruppiResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaGruppiData",
                        fields={
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "results": serializers.ListField(child=serializers.DictField()),
                            "riepilogo": serializers.DictField(),
                            "tipi": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET la lista paginata dei gruppi fatturabili del
    #        mese/stadio richiesto PIU' il riepilogo di perimetro (n gruppi, n
    #        attivita', valore, di cui oneri) nella stessa risposta.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        competenza_mese = qp_iso_date_optional(qp.get("competenza_mese"), "competenza_mese")
        ErrorManager.require(
            competenza_mese is not None,
            code="E_VENDITE_VALIDATION",
            message="Parametro competenza_mese obbligatorio.",
            function_name="vendite.api.views_dashboard_competenza.gruppi",
        )
        assert competenza_mese is not None
        stadio = qp_str_upper(qp.get("stadio"))
        # Vocabolario ESTENSIBILE lato DB (config.sorgenti.codice_interno +
        # ONERI_COMMESSA): nessuna whitelist Python, che si disallineerebbe al
        # primo tipo di sorgente aggiunto. Il valore e' un bind param (nessuna
        # injection) e le voci valide le dichiara il blocco `tipi` della
        # risposta, calcolato sui dati.
        tipo_gruppo = qp_str_upper(qp.get("tipo_gruppo"))
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        data = fn_dash_competenza_gruppi(
            competenza_mese=competenza_mese,
            stadio=stadio,
            tipo_gruppo=tipo_gruppo,
            order_by=order_by,
            order_dir=order_dir,
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
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (tipo_evento, lotto_codice, "
                    "fattura_numero, error_code, data_evento). Assente = "
                    "eventi recenti prima."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Direzione ordinamento: asc | desc.",
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
        # Ordinamento (convenzione order_by/order_dir): whitelist + direzione
        # validate nel service (unica definizione, fail-fast 400).
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        page = qp_int_strict(qp.get("page"), "page", 1)
        page_size = qp_int_strict(qp.get("page_size"), "page_size", 50)

        data = fn_dash_competenza_errori(
            competenza_mese=competenza_mese,
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            page_size=page_size,
        )
        return success_response(data)


# Scopo: Guard comune delle tre export di competenza per il mese obbligatorio.
#        Le liste gruppi/commesse non hanno senso senza perimetro: senza mese
#        esporterebbero «tutto», che non e' cio' che l'operatore ha a video.
def _competenza_mese_obbligatoria(request: Request, *, function_name: str) -> date:
    competenza_mese = qp_iso_date_optional(
        request.query_params.get("competenza_mese"), "competenza_mese",
    )
    ErrorManager.require(
        competenza_mese is not None,
        code="E_VENDITE_VALIDATION",
        message="Parametro competenza_mese obbligatorio.",
        function_name=function_name,
    )
    assert competenza_mese is not None
    return competenza_mese


class ApiDashboardCompetenzaGruppiExport(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/gruppi/export/?formato=csv|xlsx

    Esporta la STESSA lista dei gruppi fatturabili, con gli stessi filtri.
    Colonne e ordine dal catalogo `vendite.dash_competenza_gruppi` risolto
    sulla configurazione dell'operatore. Hard cap 10.000 righe.

    NB: il parametro si chiama `formato` (italiano) NON `format` — magic
    parameter DRF (content-negotiation) che intercetterebbe la chiamata.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_competenza_gruppi_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="competenza_mese", type=str, required=True),
            OpenApiParameter(name="stadio", type=str, required=False),
            OpenApiParameter(name="tipo_gruppo", type=str, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    # Scopo: Genera il file (CSV/XLSX) dei gruppi fatturabili del mese.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        competenza_mese = _competenza_mese_obbligatoria(
            request,
            function_name="vendite.api.views_dashboard_competenza.gruppi_export",
        )
        return build_dash_export_response(
            request,
            lista_codice="vendite.dash_competenza_gruppi",
            fetch=fn_dash_competenza_gruppi,
            filtri={
                "competenza_mese": competenza_mese,
                "stadio": qp_str_upper(qp.get("stadio")),
                "tipo_gruppo": qp_str_upper(qp.get("tipo_gruppo")),
                "order_by": qp_str(qp.get("order_by")),
                "order_dir": qp_str(qp.get("order_dir")),
            },
        )


class ApiDashboardCompetenzaCommesseExport(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/commesse/export/?formato=csv|xlsx

    Esporta la STESSA lista aggregata per commessa, con gli stessi filtri.
    Colonne e ordine dal catalogo `vendite.dash_competenza_commesse`.
    Hard cap 10.000 righe. Parametro `formato`, non `format`.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_competenza_commesse_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="competenza_mese", type=str, required=True),
            OpenApiParameter(name="stadio", type=str, required=False),
            OpenApiParameter(name="solo_ritardo", type=bool, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    # Scopo: Genera il file (CSV/XLSX) del drill-down per commessa del mese.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        competenza_mese = _competenza_mese_obbligatoria(
            request,
            function_name="vendite.api.views_dashboard_competenza.commesse_export",
        )
        return build_dash_export_response(
            request,
            lista_codice="vendite.dash_competenza_commesse",
            fetch=fn_dash_competenza_commesse,
            filtri={
                "competenza_mese": competenza_mese,
                "stadio": qp_str_upper(qp.get("stadio")),
                "solo_ritardo": bool(
                    qp_bool_optional(qp.get("solo_ritardo"), "solo_ritardo"),
                ),
                "order_by": qp_str(qp.get("order_by")),
                "order_dir": qp_str(qp.get("order_dir")),
            },
        )


class ApiDashboardCompetenzaErroriExport(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/errori/export/?formato=csv|xlsx

    Esporta la STESSA lista degli errori del mese. Colonne e ordine dal
    catalogo `vendite.dash_competenza_errori`. Hard cap 10.000 righe.
    `competenza_mese` e' OPZIONALE qui, come nel GET di lista gemello.
    Parametro `formato`, non `format`.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_competenza_errori_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="competenza_mese", type=str, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    # Scopo: Genera il file (CSV/XLSX) della lista errori del mese.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        return build_dash_export_response(
            request,
            lista_codice="vendite.dash_competenza_errori",
            fetch=fn_dash_competenza_errori,
            filtri={
                "competenza_mese": qp_iso_date_optional(
                    qp.get("competenza_mese"), "competenza_mese",
                ),
                "order_by": qp_str(qp.get("order_by")),
                "order_dir": qp_str(qp.get("order_dir")),
            },
        )
