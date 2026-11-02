# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint API per tracciamento processi e job (Anello 0).
#        Espone audit log, task registry multi-dominio, job run log +
#        la gestione code (coda lavori generica + coda stampa — brief
#        brief-be-fe-gestione-code-lavori-stampa, FASE BE).
# ------------------------------------------------------------

from typing import Any
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.openapi_params import parametri_finestra
from apps.core.api.base_views import DomainAPIView

from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    optional_int,
    pagina_da_query,
    qp_bool_optional,
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




# ---- Parametri OpenAPI comuni riusabili ----

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
    # ⛔ QUI C'ERA `lista_codice = "storico.audit_log"`, ED E' STATO TOLTO IL
    #    2026-09-02: questo endpoint NON serve quella lista.
    #
    #    Due diari che si chiamano quasi uguale:
    #      · `storico.audit_log`  — le MODIFICHE alle righe (tabella, tipo
    #        operazione, chi, quando). La serve `/amm-software/audit-log/`
    #        (`amm_software.AuditLogView`, AdminAPIView), ed e' quella che il
    #        frontend monta;
    #      · `dbops.audit_log`    — le ESECUZIONI di funzione (function_name,
    #        status, duration_ms). La serve questo endpoint.
    #    Zero colonne in comune col catalogo di quella lista.
    #
    # ⚠️ E il difetto non era solo di etichetta: `lista_codice` accende il
    #    CANCELLO di perimetro, che leggeva i flag di `storico.audit_log`
    #    (`perimetro_emittente = true`, `multi_emittente = false`) e avrebbe
    #    risposto **422 «scegli un emittente»** a un operatore multi-emittente,
    #    su un endpoint dove l'emittente non c'entra niente. Dormiente solo
    #    perche' nessuna schermata lo chiama.
    #
    # ⚠️ E toglieva il posto alla dichiarazione VERA: `test_perimetro_emittente_
    #    copertura` trovava il codice qui e considerava la lista «coperta», dove
    #    invece e' ESENTE — la sua schermata e' `AdminAPIView`, come il log email
    #    e le altre nove. L'esenzione ora e' scritta li', con la sua ragione.
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
            _SEARCH_PARAM, *parametri_finestra(),
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

        limit, offset = pagina_da_query(qp)
        data = fn_list_audit_logs(
            status=status,
            function_name=qp_str(qp.get("function_name")),
            date_from=qp_iso_date_optional(qp.get("date_from"), "date_from"),
            date_to=qp_iso_date_optional(qp.get("date_to"), "date_to"),
            search=qp_str(qp.get("search")),
            limit=limit,
            offset=offset,
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
        parameters=[_ATTIVO_ONLY_PARAM, _SEARCH_PARAM, *parametri_finestra()],
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
        limit, offset = pagina_da_query(qp)
        data = fn_list_domini_task(
            attivo_only=qp_bool_optional(qp.get("attivo_only"), "attivo_only", default=True),
            search=qp_str(qp.get("search")),
            limit=limit,
            offset=offset,
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
            _ATTIVO_ONLY_PARAM, _SEARCH_PARAM, *parametri_finestra(),
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
        limit, offset = pagina_da_query(qp)
        data = fn_list_task_registry(
            dominio_codice=raw_dominio.upper() if raw_dominio else None,
            attivo_only=qp_bool_optional(qp.get("attivo_only"), "attivo_only", default=True),
            search=qp_str(qp.get("search")),
            limit=limit,
            offset=offset,
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
            _ATTIVO_ONLY_PARAM, *parametri_finestra(),
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
        limit, offset = pagina_da_query(qp)
        data = fn_list_task_implementations(
            task_code=qp_str(qp.get("task_code")),
            dominio_codice=raw_dominio.upper() if raw_dominio else None,
            attivo_only=qp_bool_optional(qp.get("attivo_only"), "attivo_only", default=True),
            limit=limit,
            offset=offset,
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
            _SEARCH_PARAM, *parametri_finestra(),
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
        # ⛔ Il vocabolario unico dei flag (§A6, 2026-10-20): prima `1/yes/y`
        #    erano «riuscite» e ogni altro valore, `banana` compreso, «fallite».
        ok = qp_bool_optional(qp.get("ok"), "ok")

        limit, offset = pagina_da_query(qp)
        data = fn_list_job_runs(
            jobname=qp_str(qp.get("jobname")),
            ok=ok,
            date_from=qp_iso_date_optional(qp.get("date_from"), "date_from"),
            date_to=qp_iso_date_optional(qp.get("date_to"), "date_to"),
            search=qp_str(qp.get("search")),
            limit=limit,
            offset=offset,
        )
        return success_response(data)




# ==================================================================
# Job Summary
# ==================================================================

class ApiJobSummary(DomainAPIView):
    area_funzionale = "core"

    @extend_schema(
        parameters=[*parametri_finestra()],
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
        limit, offset = pagina_da_query(qp)
        data = fn_list_job_summary(
            limit=limit,
            offset=offset,
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
_SORT_BY_PARAM = OpenApiParameter(
    name="order_by", type=str, location=OpenApiParameter.QUERY,
    required=False, description=(
        "Colonna di ordinamento. Coda lavori: id, job_type, stato, "
        "proprietario, started_at, ended_at, archiviato_il (default "
        "started_at). Coda stampa: id, fattura_numero, emittente_codice, "
        "operatore, stato, lotto_id, data_update, archiviato_il (default "
        "data_update). Fino al 2026-10-20 si chiamava `sort_by`."
    ),
)
_SORT_DIR_PARAM = OpenApiParameter(
    name="order_dir", type=str, location=OpenApiParameter.QUERY,
    required=False, description="Direzione: asc | desc, maiuscole ammesse (default desc). Fino al 2026-10-20 si chiamava `sort_dir`.",
)
_ARCHIVIATE_PARAM = OpenApiParameter(
    name="archiviate", type=bool, location=OpenApiParameter.QUERY,
    required=False, description=(
        "Includi anche le righe ARCHIVIATE (default false: sono nascoste). "
        "Quante ne restano fuori lo dice `archiviate_count` nell'envelope."
    ),
)

_LISTA_CODE_RESPONSE = inline_serializer(
    name="CodeListaResponse",
    fields={
        "data": inline_serializer(
            name="CodeListaData",
            fields={
                "count": serializers.IntegerField(),
                # Quante righe l'archiviazione lascia FUORI dall'elenco (0 se
                # sono incluse: li' non c'e' niente di nascosto da dichiarare).
                # Senza questo numero «coda pulita» e «tre righe messe via» si
                # leggono uguali — stessa lezione di `ritirate_count`.
                "archiviate_count": serializers.IntegerField(),
                "results": serializers.ListField(child=serializers.DictField()),
            },
        ),
        "meta": serializers.DictField(required=False),
    },
)


# Scopo: Parsing comune dei parametri condivisi dalle due liste code:
#        ambito (miei/tutti), stato (upper), intervallo date, solo_vivi,
#        limit (cap MAX_LIMIT, fonte unica coi repo)/offset. Ritorna un
#        dict di kwargs per il service.
def _parse_code_list_params(qp) -> dict:
    limit, offset = pagina_da_query(qp)
    ambito = (qp_str_upper(qp.get("ambito")) or "MIEI")
    return {
        "tutti": ambito == "TUTTI",
        "stato": qp_str_upper(qp.get("stato")),
        "data_da": qp_iso_date_optional(qp.get("data_da"), "data_da"),
        "data_a": qp_iso_date_optional(qp.get("data_a"), "data_a"),
        "solo_vivi": qp_bool_optional(qp.get("solo_vivi"), "solo_vivi") or False,
        # Le archiviate sono NASCOSTE di default: l'interruttore «mostra
        # archiviate» della toolbar le chiede (brief-db-archiviazione-righe-code).
        "includi_archiviate": (
            qp_bool_optional(qp.get("archiviate"), "archiviate") or False
        ),
        "limit": limit,
        "offset": offset,
        # Whitelist e default vivono nel service (differiscono per coda):
        # qui solo il pass-through delle stringhe grezze.
        # ⛔ In query si chiamano `order_by`/`order_dir` come in ogni altra
        #    lista (decisione Tid 2026-10-20, brief-be-verifica-documentazione-
        #    api §A4): fino a quel giorno le due code usavano `sort_by`/`sort_dir`.
        "sort_by": qp_str(qp.get("order_by")),
        "sort_dir": qp_str(qp.get("order_dir")),
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
    lista_codice = "dbops.coda_lavori"
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            _AMBITO_PARAM, _STATO_PARAM, _SOLO_VIVI_PARAM,
            OpenApiParameter(
                name="tipo", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per job_type (es. FATTURAZIONE_GIRO).",
            ),
            _DATA_DA_PARAM, _DATA_A_PARAM, _ARCHIVIATE_PARAM,
            *parametri_finestra(), _SORT_BY_PARAM, _SORT_DIR_PARAM,
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
    outbox PDF). Ambito per-OPERATORE come la coda lavori (2026-07-23):
    `?ambito=miei` = righe innescate dal chiamante (user_insert), `tutti` =
    tutte (visibilita' aperta a ogni operatore)."""

    area_funzionale = "strumenti"
    is_search_endpoint = True
    lista_codice = "vendite.fatture_stampa_coda"
    throttle_classes = [SearchBurstRateThrottle]

    @extend_schema(
        parameters=[
            _AMBITO_PARAM, _STATO_PARAM, _SOLO_VIVI_PARAM,
            OpenApiParameter(
                name="lotto_id", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Filtra per lotto di fatturazione.",
            ),
            _DATA_DA_PARAM, _DATA_A_PARAM, _ARCHIVIATE_PARAM,
            *parametri_finestra(), _SORT_BY_PARAM, _SORT_DIR_PARAM,
        ],
        responses={200: _LISTA_CODE_RESPONSE},
    )
    # Scopo: Restituisce via GET l'elenco paginato della coda stampa.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        params = _parse_code_list_params(qp)
        data = gestione_service.elenca_coda_stampa(
            request.user,
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
        def _handler(_payload: dict[str, Any]) -> dict[str, Any]:
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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            extra = optional_int(payload, "extra_tentativi")
            kwargs = {} if extra is None else {"extra_tentativi": extra}
            return gestione_service.requeue_job(
                request.user, int(job_id), **kwargs,
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ══════════════════════════════════════════════════════════════
#  ARCHIVIAZIONE delle righe di coda (2026-09-04,
#  brief-db-archiviazione-righe-code)
# ══════════════════════════════════════════════════════════════
#
# ⛔ IL GATE E' `code_manage`, NON l'ownership degli altri due verbi. Annulla e
#    requeue sono owner-scoped — un operatore agisce sui PROPRI job e il
#    permesso serve solo ad allargare agli altrui. L'archiviazione ha effetto
#    GLOBALE: chi archivia toglie la riga dall'elenco anche all'amministratore.
#    Effetto globale, permesso globale (decisione di Tid, brief §7.2).
# ⛔ E il gate lo verifica il SERVICE, non un `post_permission` qui: la catena
#    dei permessi, trovando un `<metodo>_permission`, ritorna l'esito
#    dell'azione di processo e SALTA il controllo di area — cioe' un operatore
#    con `code_manage` e area `strumenti` in sola LETTURA passerebbe, mentre i
#    due verbi accanto (che quel permesso non lo dichiarano) cadono su
#    `METHOD_REQUIRES['POST'] = 'add'` e pretendono `TUTTO`. Senza
#    `post_permission` valgono ENTRAMBI i controlli: l'area dalla catena, il
#    `code_manage` dal service.
# ⭐ Due verbi e non un flag nel corpo: le due direzioni hanno esiti diversi —
#    archiviare una riga ancora VIVA e' un rifiuto del database
#    (`E_CODA_ARCHIVIAZIONE_NON_AMMESSA`, 409), ripristinare non fallisce mai —
#    e un endpoint il cui esito dipende da un booleano nel payload nasconde
#    quella differenza a chi legge le rotte.
# ⚠️ Il perimetro dell'ARCHIVIAZIONE non e' il perimetro della LISTA: la lista
#    e' visibilita' e la vede ogni operatore, qui si scrive.

_ARCHIVIAZIONE_REQUEST = inline_serializer(
    name="CodaArchiviazioneRequest",
    fields={"ids": serializers.ListField(child=serializers.IntegerField())},
)

_ARCHIVIAZIONE_RESPONSE = inline_serializer(
    name="CodaArchiviazioneResponse",
    fields={
        "data": inline_serializer(
            name="CodaArchiviazioneData",
            fields={
                # COMPLETATO | PARZIALE | ERRORE: chi legge DEVE guardarlo,
                # perche' un 200 non dice che sono passate tutte.
                "esito": serializers.CharField(),
                "archiviato": serializers.BooleanField(),
                "richieste": serializers.IntegerField(),
                "riuscite": serializers.IntegerField(),
                "falliti": serializers.ListField(child=serializers.DictField()),
            },
        ),
        "meta": serializers.DictField(required=False),
    },
)


class _ArchiviazioneCodaBaseView(DomainAPIView):
    """Telaio comune dei quattro verbi di archiviazione delle due code.

    Le sottoclassi dichiarano solo `esegui` (quale coda, quale direzione).
    ⭐ Il telaio esiste perche' lo stesso endpoint va scritto DUE volte per coda
    e DUE volte per direzione: quattro copie della stessa decorazione, dello
    stesso gate e dello stesso `handle_post_json` sono quattro posti in cui la
    prossima modifica ne dimentica uno.
    ⭐ Rotte di COLLEZIONE, con l'elenco nel corpo: un verbo di massa e uno
    per singola riga sarebbero due contratti da tenere allineati per lo stesso
    identico rifiuto, che e' per riga. Il menu di riga manda un elenco di uno.
    """

    area_funzionale = "strumenti"

    # Scopo: esegue il verbo sulle righe indicate. La implementa la
    #        sottoclasse, che sa a quale coda appartengono e in che direzione
    #        va la bandiera.
    def esegui(self, request: Request, ids: object) -> dict[str, Any]:
        raise NotImplementedError

    @extend_schema(
        parameters=[_IDEMPOTENCY_HEADER_PARAM],
        request=_ARCHIVIAZIONE_REQUEST,
        responses={200: _ARCHIVIAZIONE_RESPONSE},
    )
    # Scopo: Alza o abbassa la bandiera `archiviato` sulle righe indicate. Il
    #        guard di stato («solo una riga non viva si archivia») e la
    #        derivazione dei timbri sono del DATABASE: qui non se ne tiene una
    #        copia. ⚠️ Risponde 200 anche a esito PARZIALE — la riga che il
    #        database ha rifiutato sta in `falliti`, col suo codice e la sua
    #        frase: chi legge deve guardare `esito`, non lo status.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return self.esegui(request, payload.get("ids"))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiCodaLavoriArchivia(_ArchiviazioneCodaBaseView):
    """Archivia un job TERMINALE della coda lavori: la riga esce dall'elenco,
    lo stato non si tocca e i conteggi restano fermi. Riga ancora viva → 409
    `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` dal trigger."""

    # Scopo: alza la bandiera sui job indicati.
    def esegui(self, request: Request, ids: object) -> dict[str, Any]:
        return gestione_service.imposta_archiviazione_job(
            request.user, ids, archiviato=True,
        )


class ApiCodaLavoriRipristina(_ArchiviazioneCodaBaseView):
    """Rimette in elenco un job archiviato della coda lavori."""

    # Scopo: abbassa la bandiera sui job indicati.
    def esegui(self, request: Request, ids: object) -> dict[str, Any]:
        return gestione_service.imposta_archiviazione_job(
            request.user, ids, archiviato=False,
        )


class ApiCodaStampaArchivia(_ArchiviazioneCodaBaseView):
    """Archivia una riga TERMINALE della coda stampa. ⚠️ E' la prima scrittura
    dell'operatore su `vendite.fatture_stampa_coda`: oltre alla policy RLS
    armata il 2026-09-04, il repository applica anche il filtro applicativo di
    emittente — la RLS si somma ai filtri, non li sostituisce. Fuori perimetro
    → 404, indistinguibile da inesistente."""

    # Scopo: alza la bandiera sulle righe di coda stampa indicate.
    def esegui(self, request: Request, ids: object) -> dict[str, Any]:
        return gestione_service.imposta_archiviazione_stampa(
            request.user, ids, archiviato=True,
            auth_user_id=get_scope_user_id(request),
        )


class ApiCodaStampaRipristina(_ArchiviazioneCodaBaseView):
    """Rimette in elenco una riga archiviata della coda stampa."""

    # Scopo: abbassa la bandiera sulle righe di coda stampa indicate.
    def esegui(self, request: Request, ids: object) -> dict[str, Any]:
        return gestione_service.imposta_archiviazione_stampa(
            request.user, ids, archiviato=False,
            auth_user_id=get_scope_user_id(request),
        )
