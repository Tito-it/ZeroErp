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
from apps.core.api.base_views import DomainAPIView

from apps.core.api.payload_validators import paginated_envelope, qp_int_strict, qp_str
from apps.core.api.search_validators import require_min_search_length, validate_order_params
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import SearchBurstRateThrottle
from apps.core.db.search_repository import SearchRepository
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.service_errors import ServiceError

# Ricerca universale soggetti — endpoint a due livelli.


# Limiti paginazione per la ricerca
_PAGE_SIZE_MIN = 1
_PAGE_SIZE_MAX = 100
_PAGE_SIZE_DEFAULT = 25


# Scopo: Estrae e valida tipo_ruolo_id da query params. Verifica obbligatorieta',
# conversione a intero e flag ricerca_visibile tramite repository.
def _require_tipo_ruolo_id(query_params, repo: SearchRepository) -> int:
    raw = query_params.get("tipo_ruolo_id")
    if not raw:
        raise ServiceError(
            code="E_SEARCH_VALIDATION",
            message="Parametri ricerca non validi.",
            detail="Il parametro 'tipo_ruolo_id' e' obbligatorio.",
        )
    tipo_ruolo_id = qp_int_strict(raw, "tipo_ruolo_id", 0)

    if not repo.is_tipo_ruolo_visibile(tipo_ruolo_id):
        raise ServiceError(
            code="E_SEARCH_VALIDATION",
            message="Tipo ruolo non valido per la ricerca.",
            detail=f"tipo_ruolo_id={tipo_ruolo_id} non e' abilitato per la ricerca universale.",
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
    """GET /api/v1/core/search/ — ricerca soggetti livello 1 (una riga per soggetto)."""

    skip_area_check = True
    is_search_endpoint = True
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
                description="ID tipo ruolo (obbligatorio). Solo tipi con ricerca_visibile=true.",
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
                description="Dimensione pagina (default 25, max 100).",
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Colonna di ordinamento. Valori: ragione_sociale_completa, soggetto_codice, id_fiscale_univoco, utility_list.",
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
    # Valida parametri, applica scope emittente, delega al repository DB e
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
        require_min_search_length(q, field_name="q")

        repo = SearchRepository()
        tipo_ruolo_id = _require_tipo_ruolo_id(request.query_params, repo)

        page = qp_int_strict(request.query_params.get("page"), "page", 1)
        page_size = qp_int_strict(
            request.query_params.get("page_size"), "page_size", _PAGE_SIZE_DEFAULT
        )

        # Validazione range paginazione
        if page < 1:
            raise ServiceError(
                code="E_SEARCH_VALIDATION",
                message="Parametri paginazione non validi.",
                detail="page deve essere >= 1.",
            )
        if not (_PAGE_SIZE_MIN <= page_size <= _PAGE_SIZE_MAX):
            raise ServiceError(
                code="E_SEARCH_VALIDATION",
                message="Parametri paginazione non validi.",
                detail=f"page_size deve essere compreso tra {_PAGE_SIZE_MIN} e {_PAGE_SIZE_MAX}.",
            )

        # Ordinamento opzionale
        order_by, order_dir = validate_order_params(
            qp_str(request.query_params.get("order_by")),
            qp_str(request.query_params.get("order_dir")),
        )

        # Scope emittente — sr_ids perche' la funzione SQL filtra su
        # emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id
        cache: dict = {}
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(
            request.user, cache=cache
        )

        offset = (page - 1) * page_size
        results, total_count = repo.search_soggetti(
            search_term=q,
            tipo_ruolo_id=tipo_ruolo_id,
            emittente_ids=emittente_ids,
            limit=page_size,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )

        data = paginated_envelope(results, total_count, page, page_size)
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
    # Valida tipo_ruolo_id, verifica ricerca_visibile e applica scope emittente.
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        repo = SearchRepository()
        tipo_ruolo_id = _require_tipo_ruolo_id(request.query_params, repo)

        # utility_id opzionale — filtra dettaglio CLIENTE per utility specifica
        raw_utility = request.query_params.get("utility_id")
        utility_id = qp_int_strict(raw_utility, "utility_id", None) if raw_utility else None

        # Scope emittente — sr_ids, stesso filtro della search list
        cache: dict = {}
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(
            request.user, cache=cache
        )

        result = repo.get_search_detail(
            soggetto_id=str(soggetto_id),
            tipo_ruolo_id=tipo_ruolo_id,
            utility_id=utility_id,
            emittente_ids=emittente_ids,
        )

        if result is None:
            raise ServiceError(
                code="E_SEARCH_NOT_FOUND",
                message="Dettaglio soggetto non trovato.",
                detail=f"Nessun dettaglio per soggetto_id={soggetto_id} e tipo_ruolo_id={tipo_ruolo_id}.",
            )

        return success_response(result)
