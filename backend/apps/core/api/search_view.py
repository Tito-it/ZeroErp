# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint API ricerca universale soggetti (livello 1 e livello 2)
# e lookup tipi ruolo per il drawer di ricerca.
# Espone GET /api/v1/core/search/, /search/<uuid>/detail/,
# /lookup/tipi-ruoli/.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.openapi_params import parametri_finestra
from apps.core.api.base_views import DomainAPIView

from apps.core.api.payload_validators import envelope_da_offset, pagina_da_query, qp_int_optional, qp_str
from apps.core.api.search_validators import require_min_search_length, validate_order_params
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import SearchBurstRateThrottle
from apps.core.db._helpers import soglia_ricerca
from apps.core.db.search_repository import RICERCA_SOGGETTI, SearchRepository
from apps.core.services.payload_helpers import INTEGER_MAX, INTEGER_MIN
from apps.core.services.service_errors import ServiceError

# Ricerca universale soggetti — endpoint a due livelli.


# Limiti paginazione per la ricerca
_PAGE_SIZE_MAX = 100
_PAGE_SIZE_DEFAULT = 25


# Scopo: Estrae tipo_ruolo_id da query params: obbligatorieta' e conversione
#        a intero, nient'altro.
# ⛔ Se il ruolo esiste ed e' ricercabile lo dice il DB, non questa funzione:
#    `script.fn_predicato_soggetto_ruolo_visibile`, chiamata da lista e
#    dettaglio, risponde 404 `E_TIPO_RUOLO_NON_TROVATO` /
#    `E_TIPO_RUOLO_NON_RICERCABILE` (Q-2 di
#    brief-db-codici-non-trovato-email-e-permessi, 2026-10-10). Il controllo
#    su `ricerca_visibile` che stava qui era una seconda copia della regola.
# ⚠️ Tetto `integer`: il valore va a `p_tipo_ruolo_id integer` delle due
#    funzioni, e un bigint li' e' un 500, non un 400 (BB `qp_int_optional`).
def _require_tipo_ruolo_id(query_params) -> int:
    tipo_ruolo_id = qp_int_optional(
        query_params.get("tipo_ruolo_id"), "tipo_ruolo_id",
        min_val=INTEGER_MIN, max_val=INTEGER_MAX,
    )
    if tipo_ruolo_id is None:
        raise ServiceError(
            code="E_SEARCH_VALIDATION",
            message="Parametri ricerca non validi.",
            detail="Il parametro 'tipo_ruolo_id' e' obbligatorio.",
        )
    return tipo_ruolo_id


class LookupTipiRuoliView(DomainAPIView):
    """GET /api/v1/core/lookup/tipi-ruoli/ — tipi ruolo visibili per ricerca universale."""

    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="ricerca_visibile",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filtra solo tipi con ricerca_visibile=true (default true).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="LookupTipiRuoliResponse",
                fields={
                    "data": inline_serializer(
                        name="LookupTipiRuoliData",
                        fields={
                            "results": serializers.ListField(
                                child=serializers.DictField()
                            ),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce i tipi ruolo con ricerca_visibile = true per il dropdown ricerca.
    def get(self, request: Request) -> JsonResponse:
        repo = SearchRepository()
        results = repo.list_tipi_ruoli_visibili()
        return success_response({"results": results})


class SearchUniversaleView(DomainAPIView):
    """GET /api/v1/core/search/ — ricerca soggetti livello 1 (una riga per soggetto).

    Dal 2026-10-31 e' la lista a catalogo `anagrafiche.ricerca_soggetti` (113):
    colonne e personalizzazione dal catalogo, ordinamento dalla whitelist
    `ALLOWED_ORDER_COLUMNS` (`search_validators`).
    ⚠️ La RICERCA e' della funzione DB (`q`, i campi li sceglie lei): le colonne
    `ricercabile_full` del catalogo qui non la governano (richiesta al team DB,
    brief-db-liste-datatable-grezze-secondo-giro §4.4).
    """

    skip_area_check = True
    is_search_endpoint = True
    lista_codice = "anagrafiche.ricerca_soggetti"
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Termine di ricerca (min 3 caratteri). Cerca su ragione_sociale_completa e id_fiscale_univoco_cf_piva.",
            ),
            OpenApiParameter(
                name="tipo_ruolo_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description="ID tipo ruolo (obbligatorio). Solo tipi con ricerca_visibile=true: gli altri 404 E_TIPO_RUOLO_NON_RICERCABILE.",
            ),
            *parametri_finestra(default_limit=_PAGE_SIZE_DEFAULT, max_limit=_PAGE_SIZE_MAX),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Colonna di ordinamento. Valori: ragione_sociale_completa, soggetto_codice, id_fiscale_univoco. utility_list non e' ordinabile (aggregato della sola pagina).",
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Direzione ordinamento: ASC (default) o DESC.",
            ),
        ],
        responses={
            200: inline_serializer(
                name="SearchUniversaleResponse",
                fields={
                    "data": inline_serializer(
                        name="SearchUniversaleData",
                        fields={
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "results": serializers.ListField(
                                child=serializers.DictField()
                            ),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta GET di ricerca universale soggetti (livello 1).
    # Valida parametri, delega al repository DB e
    # restituisce risultati paginati nell'envelope standard.
    def get(self, request: Request) -> JsonResponse:
        # Validazione q: prima obbligatorieta', poi lunghezza minima
        q = qp_str(request.query_params.get("q"))
        if q is None:
            raise ServiceError(
                code="E_SEARCH_VALIDATION",
                message="Parametri ricerca non validi.",
                detail="Il parametro 'q' e' obbligatorio.",
            )
        # ⭐ La soglia e' quella della lista a catalogo (D-6 di brief-db-liste-
        #    datatable-grezze-secondo-giro, Tid 2026-11-01), la stessa che il
        #    frontend legge dalla configurazione: cambiata dal pannello admin,
        #    il 400 la segue. La funzione DB rifiuta solo il termine vuoto.
        require_min_search_length(
            q, min_length=soglia_ricerca(RICERCA_SOGGETTI.lista_codice), field_name="q",
        )

        tipo_ruolo_id = _require_tipo_ruolo_id(request.query_params)

        # La finestra dal BB: dal 2026-10-21 un dialetto solo, `limit`/`offset`
        # (`page`/`page_size` sono un 400). Oltre il massimo della ricerca la
        # finestra si riporta nei limiti, come ogni lista.
        limit, offset = pagina_da_query(
            request.query_params, default_limit=_PAGE_SIZE_DEFAULT, max_limit=_PAGE_SIZE_MAX,
        )

        # Ordinamento opzionale
        order_by, order_dir = validate_order_params(
            qp_str(request.query_params.get("order_by")),
            qp_str(request.query_params.get("order_dir")),
        )

        results, total_count = SearchRepository().search_soggetti(
            search_term=q,
            tipo_ruolo_id=tipo_ruolo_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )

        data = envelope_da_offset(results, total_count, limit=limit, offset=offset)
        return success_response(data)


class SearchDetailView(DomainAPIView):
    """GET /api/v1/core/search/<uuid>/detail/ — dettaglio soggetto per tipo ruolo (livello 2)."""

    skip_area_check = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="tipo_ruolo_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description="ID tipo ruolo per il dettaglio.",
            ),
            OpenApiParameter(
                name="utility_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filtro opzionale per utility specifica (solo CLIENTE).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="SearchDetailResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta GET di dettaglio soggetto per tipo ruolo (livello 2).
    # Carica lazy il dettaglio specifico per tipo ruolo tramite fn_get_search_detail.
    # Valida tipo_ruolo_id; ruolo ricercabile e perimetro dei clienti li decide il DB.
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        tipo_ruolo_id = _require_tipo_ruolo_id(request.query_params)

        # utility_id opzionale — filtra dettaglio CLIENTE per utility specifica
        # ⚠️ Tetto `integer`: il valore va a `p_utility_id integer` di
        #    `fn_get_search_detail`, e un bigint li' e' un 500, non un 400.
        utility_id = qp_int_optional(
            request.query_params.get("utility_id"), "utility_id",
            min_val=INTEGER_MIN, max_val=INTEGER_MAX,
        )

        result = SearchRepository().get_search_detail(
            soggetto_id=str(soggetto_id),
            tipo_ruolo_id=tipo_ruolo_id,
            utility_id=utility_id,
        )

        if result is None:
            raise ServiceError(
                code="E_SEARCH_NOT_FOUND",
                message="Dettaglio soggetto non trovato.",
                detail=f"Nessun dettaglio per soggetto_id={soggetto_id} e tipo_ruolo_id={tipo_ruolo_id}.",
            )

        return success_response(result)
