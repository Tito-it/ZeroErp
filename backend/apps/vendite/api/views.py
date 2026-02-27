from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.api.error_responses import exception_to_error_response
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_bool, optional_int, optional_iso_date, optional_uuid
from apps.core.api.success_responses import success_response
from apps.vendite.services.commesse_service import (
    fn_get_commessa_stato,
    fn_get_commesse_push_log,
    fn_list_commessa_attivita,
    pr_run_commesse_push,
)
from apps.vendite.services.pipeline_service import (
    fn_get_lotto_segnalazioni_summary,
    fn_get_lotto_task_runs,
    fn_reset_lotto_draft,
    fn_reset_lotto_fattura_draft,
    pr_run_lotto_pipeline,
)
from apps.vendite.services.vendite_service import fn_list_lotti, fn_list_lotto_fatture

# View API vendite: espone endpoint HTTP per avviare pipeline lotto.


class ApiRunLottoPipeline(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Chiave idempotenza obbligatoria per endpoint write.",
            )
        ],
        request=inline_serializer(
            name="VenditeRunLottoPipelineRequest",
            fields={
                "lotto_id": serializers.IntegerField(required=False, allow_null=True),
                "competenza_mese": serializers.DateField(required=False, allow_null=True),
                "tipo_doc_fiscale_id": serializers.IntegerField(required=False, allow_null=True),
                "utility_id": serializers.IntegerField(required=False, allow_null=True),
                "billing_account_id": serializers.IntegerField(required=False, allow_null=True),
                "emittente_soggetto_ruolo_id": serializers.IntegerField(required=False, allow_null=True),
                "lock_batch_id": serializers.UUIDField(required=False, allow_null=True),
                "meta": serializers.DictField(required=False),
                "dry_run": serializers.BooleanField(required=False),
                "tipo_lotto": serializers.CharField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeRunLottoPipelineResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeRunLottoPipelineData",
                        fields={
                            "lotto_id": serializers.IntegerField(),
                            "status": serializers.CharField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP POST del relativo endpoint API.
    def post(self, request: Request) -> JsonResponse:
        # Scopo: Gestisce la logica interna del caso d'uso richiamato dall'endpoint.
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            lotto_id = pr_run_lotto_pipeline(
                lotto_id=optional_int(payload, "lotto_id", zero_as_none=True),
                competenza_mese=optional_iso_date(payload, "competenza_mese"),
                tipo_doc_fiscale_id=optional_int(payload, "tipo_doc_fiscale_id", zero_as_none=True),
                utility_id=optional_int(payload, "utility_id", zero_as_none=True),
                billing_account_id=optional_int(payload, "billing_account_id", zero_as_none=True),
                emittente_soggetto_ruolo_id=optional_int(
                    payload, "emittente_soggetto_ruolo_id", zero_as_none=True
                ),
                lock_batch_id=optional_uuid(payload, "lock_batch_id"),
                meta=payload.get("meta"),
                dry_run=optional_bool(payload, "dry_run", default=False),
                tipo_lotto=payload.get("tipo_lotto", "MASSIVO"),
            )
            return {"lotto_id": lotto_id, "status": "ok"}

        # Pattern condiviso: JSON parse + envelope errori centralizzato.
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRunLottoPipelineV1(ApiRunLottoPipeline):
    # Versione canonica protetta: richiede JWT su /api/v1/*
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiLottoSegnalazioniSummary(APIView):
    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeLottoSegnalazioniSummaryResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeLottoSegnalazioniSummaryData",
                        fields={
                            "lotto_id": serializers.IntegerField(),
                            "critical_count": serializers.IntegerField(),
                            "warning_count": serializers.IntegerField(),
                            "attention_count": serializers.IntegerField(),
                            "is_error": serializers.BooleanField(),
                            "blocks_next_step": serializers.BooleanField(),
                            "summary": serializers.DictField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il riepilogo segnalazioni del lotto per uso operativo/UI.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        try:
            data = fn_get_lotto_segnalazioni_summary(lotto_id=lotto_id)
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiLottoSegnalazioniSummaryV1(ApiLottoSegnalazioniSummary):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiLottoTaskRuns(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Numero massimo task run restituiti (default 100, max 500).",
            )
        ],
        responses={
            200: inline_serializer(
                name="VenditeLottoTaskRunsResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeLottoTaskRunsData",
                        fields={
                            "lotto_id": serializers.IntegerField(),
                            "count": serializers.IntegerField(),
                            "task_runs": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET i task run runtime del lotto per monitoraggio operativo.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        try:
            limit = optional_int({"limit": request.query_params.get("limit", "100")}, "limit")
            data = fn_get_lotto_task_runs(lotto_id=lotto_id, limit=limit)
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiLottoTaskRunsV1(ApiLottoTaskRuns):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiResetLottoDraft(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Chiave idempotenza obbligatoria per endpoint write.",
            )
        ],
        request=inline_serializer(
            name="VenditeResetLottoDraftRequest",
            fields={},
        ),
        responses={
            200: inline_serializer(
                name="VenditeResetLottoDraftResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeResetLottoDraftData",
                        fields={
                            "updated_lotti": serializers.IntegerField(),
                            "updated_attivita": serializers.IntegerField(),
                            "deleted_fatture": serializers.IntegerField(),
                            "deleted_righe": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP POST del relativo endpoint API.
    def post(self, request: Request, lotto_id: int) -> JsonResponse:
        # Scopo: Gestisce la logica interna del caso d'uso richiamato dall'endpoint.
        def _handler(_payload: dict[str, object]) -> dict[str, object]:
            result = fn_reset_lotto_draft(lotto_id=lotto_id)
            return result

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiResetLottoDraftV1(ApiResetLottoDraft):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiResetLottoFatturaDraft(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Chiave idempotenza obbligatoria per endpoint write.",
            )
        ],
        request=inline_serializer(
            name="VenditeResetLottoFatturaDraftRequest",
            fields={},
        ),
        responses={
            200: inline_serializer(
                name="VenditeResetLottoFatturaDraftResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeResetLottoFatturaDraftData",
                        fields={
                            "updated_attivita": serializers.IntegerField(),
                            "deleted_fatture": serializers.IntegerField(),
                            "deleted_righe": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP POST del relativo endpoint API.
    def post(self, request: Request, lotto_id: int, fattura_id: int) -> JsonResponse:
        # Scopo: Gestisce la logica interna del caso d'uso richiamato dall'endpoint.
        def _handler(_payload: dict[str, object]) -> dict[str, object]:
            result = fn_reset_lotto_fattura_draft(lotto_id=lotto_id, fattura_id=fattura_id)
            return {"data": result}

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiResetLottoFatturaDraftV1(ApiResetLottoFatturaDraft):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiLottiList(APIView):
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="competenza_mese", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro mese di competenza (YYYY-MM-DD)."),
            OpenApiParameter(name="utility_id", type=int, location=OpenApiParameter.QUERY, required=False, description="Filtro per utility."),
            OpenApiParameter(name="stato_lotto", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato lotto (es. DRAFT, COMPLETATO)."),
            OpenApiParameter(name="area_geografica_id", type=int, location=OpenApiParameter.QUERY, required=False, description="Filtro per area geografica fatturazione."),
            OpenApiParameter(name="tipo_doc_fiscale_id", type=int, location=OpenApiParameter.QUERY, required=False, description="Filtro per tipo documento fiscale."),
            OpenApiParameter(name="emittente_soggetto_ruolo_id", type=int, location=OpenApiParameter.QUERY, required=False, description="Filtro per emittente fiscale (soggetto_ruolo_id)."),
            OpenApiParameter(name="page", type=int, location=OpenApiParameter.QUERY, required=False, description="Numero pagina (default 1)."),
            OpenApiParameter(name="page_size", type=int, location=OpenApiParameter.QUERY, required=False, description="Dimensione pagina (default 50, max 200)."),
        ],
        responses={
            200: inline_serializer(
                name="VenditeLottiListResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeLottiListData",
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
    # Scopo: Restituisce via GET l'elenco paginato dei lotti fatturazione con filtri opzionali.
    def get(self, request: Request) -> JsonResponse:
        try:
            raw_competenza = request.query_params.get("competenza_mese")
            competenza_mese = optional_iso_date({"competenza_mese": raw_competenza}, "competenza_mese")

            raw_utility = request.query_params.get("utility_id")
            utility_id = optional_int({"utility_id": raw_utility}, "utility_id") if raw_utility is not None else None

            stato_lotto_raw = request.query_params.get("stato_lotto")
            stato_lotto = stato_lotto_raw.strip() or None if stato_lotto_raw is not None else None

            raw_area = request.query_params.get("area_geografica_id")
            area_geografica_id = optional_int({"area_geografica_id": raw_area}, "area_geografica_id") if raw_area is not None else None

            raw_tipo_doc = request.query_params.get("tipo_doc_fiscale_id")
            tipo_doc_fiscale_id = optional_int({"tipo_doc_fiscale_id": raw_tipo_doc}, "tipo_doc_fiscale_id") if raw_tipo_doc is not None else None

            raw_emittente = request.query_params.get("emittente_soggetto_ruolo_id")
            emittente_soggetto_ruolo_id = optional_int({"emittente_soggetto_ruolo_id": raw_emittente}, "emittente_soggetto_ruolo_id") if raw_emittente is not None else None

            page = optional_int({"page": request.query_params.get("page", "1")}, "page")
            page_size = optional_int({"page_size": request.query_params.get("page_size", "50")}, "page_size")

            data = fn_list_lotti(
                competenza_mese=competenza_mese,
                utility_id=utility_id,
                stato_lotto=stato_lotto,
                area_geografica_id=area_geografica_id,
                tipo_doc_fiscale_id=tipo_doc_fiscale_id,
                emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
                page=page,
                page_size=page_size,
            )
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiLottiListV1(ApiLottiList):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiLottoFattureList(APIView):
    is_search_endpoint = True

    # Scopo: Restituisce via GET l'elenco paginato delle fatture di un lotto con filtri e ordinamento.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        try:
            raw_stato_esecuzione = request.query_params.get("stato_esecuzione")
            stato_esecuzione = raw_stato_esecuzione.strip() or None if raw_stato_esecuzione is not None else None

            raw_esclusa = request.query_params.get("esclusa")
            esclusa = optional_bool({"esclusa": raw_esclusa}, "esclusa") if raw_esclusa is not None else None

            sort_by = request.query_params.get("sort_by", "fattura_id").strip() or "fattura_id"
            sort_dir = request.query_params.get("sort_dir", "asc").strip() or "asc"
            page = optional_int({"page": request.query_params.get("page", "1")}, "page")
            page_size = optional_int({"page_size": request.query_params.get("page_size", "50")}, "page_size")

            data = fn_list_lotto_fatture(
                lotto_id=lotto_id,
                stato_esecuzione=stato_esecuzione,
                esclusa=esclusa,
                sort_by=sort_by,
                sort_dir=sort_dir,
                page=page,
                page_size=page_size,
            )
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiLottoFattureListV1(ApiLottoFattureList):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


# ================================================================== #
# Commesse — push orchestrator + stato + attivita                     #
# ================================================================== #


class ApiRunCommessePush(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Chiave idempotenza obbligatoria per endpoint write.",
            )
        ],
        request=inline_serializer(
            name="VenditeRunCommessePushRequest",
            fields={
                "source_types": serializers.ListField(
                    child=serializers.CharField(),
                    required=True,
                    help_text="Codici sorgente da processare (es. PREVENTIVO, ORDINE_VENDITA, CONTRATTO, DDT_VENDITA, ATTIVITA_CONSUMI).",
                ),
                "dry_run": serializers.BooleanField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeRunCommessePushResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeRunCommessePushData",
                        fields={
                            "stato": serializers.CharField(),
                            "dry_run": serializers.BooleanField(),
                            "push_log_id": serializers.IntegerField(allow_null=True),
                            "durata_ms": serializers.IntegerField(allow_null=True),
                            "handlers": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP POST per lanciare il push commesse.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            source_types = payload.get("source_types") or None
            return pr_run_commesse_push(
                source_types=source_types,
                dry_run=optional_bool(payload, "dry_run", default=False),
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRunCommessePushV1(ApiRunCommessePush):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiCommessePushLog(APIView):
    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeCommessePushLogResponse",
                fields={
                    "data": serializers.DictField(),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il dettaglio di un push log commesse.
    def get(self, request: Request, push_log_id: int) -> JsonResponse:
        try:
            data = fn_get_commesse_push_log(push_log_id=push_log_id)
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiCommessePushLogV1(ApiCommessePushLog):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiCommessaStato(APIView):
    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeCommessaStatoResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeCommessaStatoData",
                        fields={
                            "commessa_id": serializers.IntegerField(),
                            "total_attivita": serializers.IntegerField(),
                            "total_approvate": serializers.IntegerField(),
                            "total_emesse": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET stato e contatori di una commessa.
    def get(self, request: Request, commessa_id: int) -> JsonResponse:
        try:
            data = fn_get_commessa_stato(commessa_id=commessa_id)
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiCommessaStatoV1(ApiCommessaStato):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ApiCommessaAttivita(APIView):
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato_emissione", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato emissione (es. NON_EMESSA, EMESSA)."),
            OpenApiParameter(name="stato_approvazione", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato approvazione (es. BOZZA, APPROVATA)."),
            OpenApiParameter(name="competenza_mese", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro mese di competenza (YYYY-MM-DD)."),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False, description="Righe per pagina (default 50, max 200)."),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False, description="Offset paginazione (default 0)."),
        ],
        responses={
            200: inline_serializer(
                name="VenditeCommessaAttivitaResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeCommessaAttivitaData",
                        fields={
                            "commessa_id": serializers.IntegerField(),
                            "count": serializers.IntegerField(),
                            "rows": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET la lista paginata delle attivita di una commessa.
    def get(self, request: Request, commessa_id: int) -> JsonResponse:
        try:
            stato_emissione = request.query_params.get("stato_emissione") or None
            stato_approvazione = request.query_params.get("stato_approvazione") or None
            competenza_mese = request.query_params.get("competenza_mese") or None
            limit = optional_int({"limit": request.query_params.get("limit", "50")}, "limit")
            offset = optional_int({"offset": request.query_params.get("offset", "0")}, "offset")
            data = fn_list_commessa_attivita(
                commessa_id=commessa_id,
                stato_emissione=stato_emissione,
                stato_approvazione=stato_approvazione,
                competenza_mese=competenza_mese,
                limit=limit,
                offset=offset,
            )
            return success_response(data)
        except Exception as exc:
            return exception_to_error_response(exc)


class ApiCommessaAttivitaV1(ApiCommessaAttivita):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
