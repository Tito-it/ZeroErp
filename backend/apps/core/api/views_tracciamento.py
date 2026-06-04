# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint API per tracciamento processi e job (Anello 0).
#        Espone audit log, task registry multi-dominio, job run log.
# ------------------------------------------------------------

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView

from apps.core.api.payload_validators import qp_bool, qp_int, qp_str
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import SearchBurstRateThrottle
from apps.core.services.tracciamento_service import (
    fn_list_audit_logs,
    fn_list_domini_task,
    fn_list_job_runs,
    fn_list_job_summary,
    fn_list_task_implementations,
    fn_list_task_registry,
)


# Scopo: page_size (page-based) da query string con default e cap a 200. Helper
#        LOCALE: solo le liste di tracciamento usano la convenzione page/page_size
#        a livello view (le liste offset-based usano core.parse_list_params).
def _parse_page_size(qp, default: int) -> int:
    return min(qp_int(qp.get("page_size"), default), 200)


# ---- Parametri OpenAPI comuni riusabili ----

_PAGE_PARAM = OpenApiParameter(
    name="page", type=int, location=OpenApiParameter.QUERY,
    required=False, description="Numero pagina (default 1).",
)
_PAGE_SIZE_PARAM = OpenApiParameter(
    name="page_size", type=int, location=OpenApiParameter.QUERY,
    required=False, description="Dimensione pagina (default 50, max 200).",
)
_ATTIVO_ONLY_PARAM = OpenApiParameter(
    name="attivo_only", type=bool, location=OpenApiParameter.QUERY,
    required=False, description="Filtra solo record attivi (default: true).",
)
_SEARCH_PARAM = OpenApiParameter(
    name="search", type=str, location=OpenApiParameter.QUERY,
    required=False, description="Ricerca libera ILIKE.",
)


# ==================================================================
# Audit Log
# ==================================================================

class ApiAuditLog(DomainAPIView):
    is_search_endpoint = True
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status", type=str, location=OpenApiParameter.QUERY,
                required=False, enum=["SUCCESS", "FAILED", "WARNING"],
                description="Filtra per status (SUCCESS, FAILED, WARNING).",
            ),
            OpenApiParameter(
                name="function_name", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per function_name (ILIKE).",
            ),
            OpenApiParameter(
                name="date_from", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data inizio (YYYY-MM-DD).",
            ),
            OpenApiParameter(
                name="date_to", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data fine (YYYY-MM-DD).",
            ),
            _SEARCH_PARAM, _PAGE_PARAM, _PAGE_SIZE_PARAM,
        ],
        responses={200: inline_serializer(
            name="AuditLogResponse",
            fields={
                "data": inline_serializer(
                    name="AuditLogData",
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
        )},
    )
    # Scopo: Restituisce via GET l'elenco paginato dell'audit log
    # con filtri opzionali su status, function_name, intervallo date e ricerca libera.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        raw_status = qp_str(qp.get("status"))
        status = raw_status.upper() if raw_status else None

        data = fn_list_audit_logs(
            status=status,
            function_name=qp_str(qp.get("function_name")),
            date_from=qp_str(qp.get("date_from")),
            date_to=qp_str(qp.get("date_to")),
            search=qp_str(qp.get("search")),
            page=qp_int(qp.get("page"), 1),
            page_size=_parse_page_size(qp, 50),
        )
        return success_response(data)




# ==================================================================
# Task Registry — Domini
# ==================================================================

class ApiDominiTask(DomainAPIView):
    is_search_endpoint = True
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[_ATTIVO_ONLY_PARAM, _SEARCH_PARAM, _PAGE_PARAM, _PAGE_SIZE_PARAM],
        responses={200: inline_serializer(
            name="DominiTaskResponse",
            fields={
                "data": inline_serializer(
                    name="DominiTaskData",
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
        )},
    )
    # Scopo: Restituisce via GET l'elenco paginato dei domini task.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        data = fn_list_domini_task(
            attivo_only=qp_bool(qp.get("attivo_only")),
            search=qp_str(qp.get("search")),
            page=qp_int(qp.get("page"), 1),
            page_size=_parse_page_size(qp, 50),
        )
        return success_response(data)




# ==================================================================
# Task Registry — Task
# ==================================================================

class ApiTaskRegistry(DomainAPIView):
    is_search_endpoint = True
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="dominio", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per codice dominio (es. FATTURAZIONE).",
            ),
            _ATTIVO_ONLY_PARAM, _SEARCH_PARAM, _PAGE_PARAM, _PAGE_SIZE_PARAM,
        ],
        responses={200: inline_serializer(
            name="TaskRegistryResponse",
            fields={
                "data": inline_serializer(
                    name="TaskRegistryData",
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
        )},
    )
    # Scopo: Restituisce via GET l'elenco paginato dei task registrati
    # con filtro opzionale per dominio.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        raw_dominio = qp_str(qp.get("dominio"))
        data = fn_list_task_registry(
            dominio_codice=raw_dominio.upper() if raw_dominio else None,
            attivo_only=qp_bool(qp.get("attivo_only")),
            search=qp_str(qp.get("search")),
            page=qp_int(qp.get("page"), 1),
            page_size=_parse_page_size(qp, 100),
        )
        return success_response(data)




# ==================================================================
# Task Registry — Implementazioni
# ==================================================================

class ApiTaskImplementations(DomainAPIView):
    is_search_endpoint = True
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="task_code", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per task_code specifico.",
            ),
            OpenApiParameter(
                name="dominio", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per codice dominio.",
            ),
            _ATTIVO_ONLY_PARAM, _PAGE_PARAM, _PAGE_SIZE_PARAM,
        ],
        responses={200: inline_serializer(
            name="TaskImplResponse",
            fields={
                "data": inline_serializer(
                    name="TaskImplData",
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
        )},
    )
    # Scopo: Restituisce via GET le implementazioni dei task con filtro
    # per task_code e dominio.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        raw_dominio = qp_str(qp.get("dominio"))
        data = fn_list_task_implementations(
            task_code=qp_str(qp.get("task_code")),
            dominio_codice=raw_dominio.upper() if raw_dominio else None,
            attivo_only=qp_bool(qp.get("attivo_only")),
            page=qp_int(qp.get("page"), 1),
            page_size=_parse_page_size(qp, 100),
        )
        return success_response(data)




# ==================================================================
# Job Run Log
# ==================================================================

class ApiJobRuns(DomainAPIView):
    is_search_endpoint = True
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="jobname", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per jobname esatto.",
            ),
            OpenApiParameter(
                name="ok", type=bool, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per esito (true/false).",
            ),
            OpenApiParameter(
                name="date_from", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data inizio (YYYY-MM-DD).",
            ),
            OpenApiParameter(
                name="date_to", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data fine (YYYY-MM-DD).",
            ),
            _SEARCH_PARAM, _PAGE_PARAM, _PAGE_SIZE_PARAM,
        ],
        responses={200: inline_serializer(
            name="JobRunsResponse",
            fields={
                "data": inline_serializer(
                    name="JobRunsData",
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
        )},
    )
    # Scopo: Restituisce via GET l'elenco paginato delle esecuzioni job pgAgent
    # con filtri opzionali su jobname, esito, intervallo date e ricerca libera.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        raw_ok = qp.get("ok")
        ok: bool | None = None
        if raw_ok is not None:
            ok = raw_ok.strip().lower() in {"1", "true", "yes", "y"}

        data = fn_list_job_runs(
            jobname=qp_str(qp.get("jobname")),
            ok=ok,
            date_from=qp_str(qp.get("date_from")),
            date_to=qp_str(qp.get("date_to")),
            search=qp_str(qp.get("search")),
            page=qp_int(qp.get("page"), 1),
            page_size=_parse_page_size(qp, 50),
        )
        return success_response(data)




# ==================================================================
# Job Summary
# ==================================================================

class ApiJobSummary(DomainAPIView):

    @extend_schema(
        parameters=[_PAGE_PARAM, _PAGE_SIZE_PARAM],
        responses={200: inline_serializer(
            name="JobSummaryResponse",
            fields={
                "data": inline_serializer(
                    name="JobSummaryData",
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
        )},
    )
    # Scopo: Restituisce via GET il riepilogo dei job con conteggi esecuzioni,
    # successi, fallimenti e ultimo esito.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        data = fn_list_job_summary(
            page=qp_int(qp.get("page"), 1),
            page_size=_parse_page_size(qp, 50),
        )
        return success_response(data)


