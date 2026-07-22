# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint API per tracciamento processi e job (Anello 0).
#        Espone audit log, task registry multi-dominio, job run log +
#        la gestione code (coda lavori generica + coda stampa — brief
#        brief-be-fe-gestione-code-lavori-stampa, FASE BE).
# ------------------------------------------------------------

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView
from apps.core.db._helpers import LIST_MAX_LIMIT

from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    optional_int,
    qp_bool,
    qp_bool_optional,
    qp_int,
    qp_int_optional,
    qp_iso_date_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import SearchBurstRateThrottle
from apps.core.services.coda_lavori import gestione_service
from apps.core.services.tracciamento_service import (
    fn_list_audit_logs,
    fn_list_domini_task,
    fn_list_job_runs,
    fn_list_job_summary,
    fn_list_task_implementations,
    fn_list_task_registry,
)


# Scopo: page_size (page-based) da query string con default e cap standard
#        LIST_MAX_LIMIT. Helper
#        LOCALE: solo le liste di tracciamento usano la convenzione page/page_size
#        a livello view (le liste offset-based usano core.parse_list_params).
def _parse_page_size(qp, default: int) -> int:
    return min(qp_int(qp.get("page_size"), default), LIST_MAX_LIMIT)


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
    # Area core (allineamento 2026-07-21, ok Tid): prima le view tracciamento
    # non dichiaravano l'area → fail-closed = di fatto SUPER_ADMIN-only. Il
    # design del brief code-UI (P-1/P-2) vuole il layer leggibile da chi ha
    # l'area core (>= LETTURA).
    area_funzionale = "core"
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
    area_funzionale = "core"
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
    area_funzionale = "core"
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
    area_funzionale = "core"
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
    area_funzionale = "core"
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
    area_funzionale = "core"

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


# ==================================================================
# Gestione code (coda lavori generica + coda stampa)
# Brief brief-be-fe-gestione-code-lavori-stampa — FASE BE.
# ==================================================================

# Parametri OpenAPI comuni delle liste code.
_AMBITO_PARAM = OpenApiParameter(
    name="ambito", type=str, location=OpenApiParameter.QUERY,
    required=False, enum=["miei", "tutti"],
    description=(
        "'tutti' mostra i job di ogni scope (richiede permesso code_manage "
        "o SUPER_ADMIN); default: solo i propri."
    ),
)
_SOLO_VIVI_PARAM = OpenApiParameter(
    name="solo_vivi", type=bool, location=OpenApiParameter.QUERY,
    required=False, description="Solo job vivi (PENDING/IN_CORSO).",
)
_STATO_PARAM = OpenApiParameter(
    name="stato", type=str, location=OpenApiParameter.QUERY,
    required=False, description="Filtra per stato esatto (es. ERRORE).",
)
_DATA_DA_PARAM = OpenApiParameter(
    name="data_da", type=str, location=OpenApiParameter.QUERY,
    required=False, description="Accodati da (YYYY-MM-DD).",
)
_DATA_A_PARAM = OpenApiParameter(
    name="data_a", type=str, location=OpenApiParameter.QUERY,
    required=False, description="Accodati fino a (YYYY-MM-DD, inclusiva).",
)
_LIMIT_PARAM = OpenApiParameter(
    name="limit", type=int, location=OpenApiParameter.QUERY,
    required=False, description="Righe per pagina (default 50, max 200).",
)
_OFFSET_PARAM = OpenApiParameter(
    name="offset", type=int, location=OpenApiParameter.QUERY,
    required=False, description="Offset paginazione (default 0).",
)

_LISTA_CODE_RESPONSE = inline_serializer(
    name="CodeListaResponse",
    fields={
        "data": inline_serializer(
            name="CodeListaData",
            fields={
                "count": serializers.IntegerField(),
                "results": serializers.ListField(child=serializers.DictField()),
            },
        ),
        "meta": serializers.DictField(required=False),
    },
)


# Scopo: Parsing comune dei parametri condivisi dalle due liste code:
#        ambito (miei/tutti), stato (upper), intervallo date, solo_vivi,
#        limit (cap LIST_MAX_LIMIT, fonte unica coi repo)/offset. Ritorna un
#        dict di kwargs per il service.
def _parse_code_list_params(qp) -> dict:
    ambito = (qp_str_upper(qp.get("ambito")) or "MIEI")
    return {
        "tutti": ambito == "TUTTI",
        "stato": qp_str_upper(qp.get("stato")),
        "data_da": qp_iso_date_optional(qp.get("data_da"), "data_da"),
        "data_a": qp_iso_date_optional(qp.get("data_a"), "data_a"),
        "solo_vivi": qp_bool_optional(qp.get("solo_vivi"), "solo_vivi") or False,
        "limit": min(qp_int(qp.get("limit"), 50), LIST_MAX_LIMIT),
        "offset": qp_int(qp.get("offset"), 0),
    }


class ApiCodeConteggi(DomainAPIView):
    """BE-4: conteggi per il badge top bar — job vivi (PENDING/IN_CORSO) delle
    due code, SCOPED al chiamante, + liveness dei worker drainer (ultimo run
    entro soglia). Sola lettura, pollata dal FE a cadenza lenta (60s)."""

    area_funzionale = "strumenti"

    @extend_schema(
        responses={200: inline_serializer(
            name="CodeConteggiResponse",
            fields={
                "data": inline_serializer(
                    name="CodeConteggiData",
                    fields={
                        "coda_lavori": serializers.DictField(),
                        "coda_stampa": serializers.DictField(),
                        "worker": serializers.DictField(),
                    },
                ),
                "meta": serializers.DictField(required=False),
            },
        )},
    )
    # Scopo: Restituisce via GET i conteggi scoped + liveness worker.
    def get(self, request: Request) -> JsonResponse:
        data = gestione_service.conteggi_code(
            request.user, auth_user_id=get_scope_user_id(request),
        )
        return success_response(data)


class ApiCodaLavoriList(DomainAPIView):
    """BE-5: lista paginata della coda lavori generica (dbops.coda_lavori).
    Scope operatore (scope_key) di default; `?ambito=tutti` solo con
    code_manage/SUPER_ADMIN (colonna proprietario + is_mio dal BE, P-5)."""

    area_funzionale = "strumenti"
    is_search_endpoint = True
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            _AMBITO_PARAM, _STATO_PARAM, _SOLO_VIVI_PARAM,
            OpenApiParameter(
                name="tipo", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per job_type (es. FATTURAZIONE_GIRO).",
            ),
            _DATA_DA_PARAM, _DATA_A_PARAM, _LIMIT_PARAM, _OFFSET_PARAM,
        ],
        responses={200: _LISTA_CODE_RESPONSE},
    )
    # Scopo: Restituisce via GET l'elenco paginato dei job della coda lavori.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        params = _parse_code_list_params(qp)
        data = gestione_service.elenca_coda_lavori(
            request.user,
            job_type=qp_str_upper(qp.get("tipo")),
            **params,
        )
        return success_response(data)


class ApiCodaStampaList(DomainAPIView):
    """BE-6: lista paginata della coda stampa (vendite.fatture_stampa_coda,
    outbox PDF). Scope emittente dell'operatore via JOIN fatture (la coda e'
    per-emittente, non per-utente); `?ambito=tutti` con code_manage."""

    area_funzionale = "strumenti"
    is_search_endpoint = True
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            _AMBITO_PARAM, _STATO_PARAM, _SOLO_VIVI_PARAM,
            OpenApiParameter(
                name="lotto_id", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per lotto di fatturazione.",
            ),
            _DATA_DA_PARAM, _DATA_A_PARAM, _LIMIT_PARAM, _OFFSET_PARAM,
        ],
        responses={200: _LISTA_CODE_RESPONSE},
    )
    # Scopo: Restituisce via GET l'elenco paginato della coda stampa.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        params = _parse_code_list_params(qp)
        data = gestione_service.elenca_coda_stampa(
            request.user,
            auth_user_id=get_scope_user_id(request),
            lotto_id=qp_int_optional(qp.get("lotto_id"), "lotto_id"),
            **params,
        )
        return success_response(data)


class ApiCodaLavoriDetail(DomainAPIView):
    """BE-8: dettaglio completo di un job per il drawer (payload, timeline,
    tentativi/errore, esito, proprietario, is_mio). Ownership scope-based:
    fuori scope/inesistente → 404 unificato (no leak)."""

    area_funzionale = "strumenti"

    @extend_schema(
        responses={200: inline_serializer(
            name="CodaLavoroDettaglioResponse",
            fields={
                "data": serializers.DictField(),
                "meta": serializers.DictField(required=False),
            },
        )},
    )
    # Scopo: Restituisce via GET il dettaglio del job (scoped).
    def get(self, request: Request, job_id: int) -> JsonResponse:
        data = gestione_service.dettaglio_job(request.user, int(job_id))
        return success_response(data)


_AZIONE_JOB_RESPONSE = inline_serializer(
    name="CodaLavoroAzioneResponse",
    fields={
        "data": inline_serializer(
            name="CodaLavoroAzioneData",
            fields={
                "job_id": serializers.IntegerField(),
                "stato": serializers.CharField(),
            },
        ),
        "meta": serializers.DictField(required=False),
    },
)

_IDEMPOTENCY_HEADER_PARAM = OpenApiParameter(
    name="Idempotency-Key",
    type=str,
    location=OpenApiParameter.HEADER,
    required=True,
    description="Chiave idempotenza obbligatoria per endpoint write.",
)


class ApiCodaLavoriAnnulla(DomainAPIView):
    """BE-7: annulla un job PENDING della coda lavori (→ ANNULLATO). Ownership
    BE: un operatore annulla solo i job del proprio scope (fuori scope → 404);
    job altrui solo con code_manage/SUPER_ADMIN. Non piu' PENDING → 409
    (nessuna race col worker: l'UPDATE ri-verifica stato e scope)."""

    area_funzionale = "strumenti"

    @extend_schema(
        parameters=[_IDEMPOTENCY_HEADER_PARAM],
        request=None,
        responses={200: _AZIONE_JOB_RESPONSE},
    )
    # Scopo: Annulla il job (guard ownership+stato nel service).
    def post(self, request: Request, job_id: int) -> JsonResponse:
        def _handler(_payload: dict[str, object]) -> dict[str, object]:
            return gestione_service.annulla_job(request.user, int(job_id))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiCodaLavoriRequeue(DomainAPIView):
    """BE-7: requeue/sblocco di un job IN_CORSO (bloccato) o ERRORE (terminale)
    → PENDING con `max_tentativi += extra_tentativi` (storia preservata).
    Stessa ownership dell'annullo; stato non riaccodabile → 409."""

    area_funzionale = "strumenti"

    @extend_schema(
        parameters=[_IDEMPOTENCY_HEADER_PARAM],
        request=inline_serializer(
            name="CodaLavoroRequeueRequest",
            fields={"extra_tentativi": serializers.IntegerField(required=False)},
        ),
        responses={200: _AZIONE_JOB_RESPONSE},
    )
    # Scopo: Riaccoda il job (guard ownership+stato nel service). Il default
    #        di `extra_tentativi` vive SOLO nel service (fonte unica): qui si
    #        passa il kwarg solo se il client l'ha fornito.
    def post(self, request: Request, job_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            extra = optional_int(payload, "extra_tentativi")
            kwargs = {} if extra is None else {"extra_tentativi": extra}
            return gestione_service.requeue_job(
                request.user, int(job_id), **kwargs,
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


