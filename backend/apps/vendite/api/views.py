from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView

from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.services.error_manager import ErrorManager
from apps.core.api.payload_validators import optional_bool, optional_int, optional_iso_date, optional_uuid
from apps.core.api.success_responses import success_response
from apps.vendite.services.commesse_service import (
    cambia_stato_commessa,
    fn_get_commessa_stato,
    fn_get_commesse_push_log,
    fn_list_commessa_attivita,
    fn_riallinea_prezzo,
    fn_sblocca_prezzo,
    fn_variazione_prezzo_eccezionale,
    pr_run_commesse_push,
)
from apps.vendite.services.pipeline_service import (
    fn_get_lotto_segnalazioni_summary,
    fn_get_lotto_task_runs,
    fn_reset_lotto_draft,
    fn_reset_lotto_fattura_draft,
    run_lotto_pipeline,
    run_lotto_pipeline_until_done,
)
from apps.vendite.services.vendite_service import fn_list_lotti, fn_list_lotto_fatture

# View API vendite: espone endpoint HTTP per avviare pipeline lotto.


# Scopo: Estrae i kwargs comuni della pipeline lotto dal payload JSON. Condiviso da
#        ApiRunLottoPipeline (single step) e ApiRunLottoPipelineUntilDone (driver),
#        per evitare duplicazione/disallineamento dei parametri.
def _run_lotto_kwargs(payload: dict[str, object]) -> dict[str, object]:
    return {
        "lotto_id": optional_int(payload, "lotto_id", zero_as_none=True),
        "competenza_mese": optional_iso_date(payload, "competenza_mese"),
        "tipo_doc_fiscale_id": optional_int(payload, "tipo_doc_fiscale_id", zero_as_none=True),
        "utility_id": optional_int(payload, "utility_id", zero_as_none=True),
        "billing_account_id": optional_int(payload, "billing_account_id", zero_as_none=True),
        "emittente_soggetto_ruolo_id": optional_int(
            payload, "emittente_soggetto_ruolo_id", zero_as_none=True
        ),
        "lock_batch_id": optional_uuid(payload, "lock_batch_id"),
        "meta": payload.get("meta"),
        "dry_run": optional_bool(payload, "dry_run", default=False),
        "tipo_lotto": payload.get("tipo_lotto", "MASSIVO"),
    }


class ApiRunLottoPipeline(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "genera_fatture_lotti"
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
            lotto_id = run_lotto_pipeline(**_run_lotto_kwargs(payload))
            return {"lotto_id": lotto_id, "status": "ok"}

        # Pattern condiviso: JSON parse + envelope errori centralizzato.
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRunLottoPipelineUntilDone(DomainAPIView):
    """Avvio on-demand del driver: esegue la pipeline del lotto fino in fondo
    (più step concatenati), restituendo l'esito strutturato (motivo di stop)."""

    area_funzionale = "vendite"
    post_permission = "genera_fatture_lotti"
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
            name="VenditeRunLottoPipelineUntilDoneRequest",
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
                name="VenditeRunLottoPipelineUntilDoneResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeRunLottoPipelineUntilDoneData",
                        fields={
                            "lotto_id": serializers.IntegerField(allow_null=True),
                            "stato_lotto": serializers.CharField(allow_null=True),
                            "stato_doc_fiscale_id": serializers.IntegerField(allow_null=True),
                            "step_eseguiti": serializers.IntegerField(),
                            "motivo_stop": serializers.CharField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP POST: esegue il driver fino a conclusione.
    def post(self, request: Request) -> JsonResponse:
        # Scopo: Gestisce la logica interna del caso d'uso richiamato dall'endpoint.
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return run_lotto_pipeline_until_done(**_run_lotto_kwargs(payload))

        # Pattern condiviso: JSON parse + envelope errori centralizzato.
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiLottoSegnalazioniSummary(DomainAPIView):
    area_funzionale = "vendite"
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
        data = fn_get_lotto_segnalazioni_summary(lotto_id=lotto_id)
        return success_response(data)




class ApiLottoTaskRuns(DomainAPIView):
    area_funzionale = "vendite"
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
        limit = optional_int({"limit": request.query_params.get("limit", "100")}, "limit")
        data = fn_get_lotto_task_runs(lotto_id=lotto_id, limit=limit)
        return success_response(data)




class ApiResetLottoDraft(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "reset_lotto_draft"
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




class ApiResetLottoFatturaDraft(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "reset_lotto_fattura_draft"
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
            return result

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)




class ApiLottiList(DomainAPIView):
    area_funzionale = "vendite"
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

        auth_user_id = get_scope_user_id(request)

        data = fn_list_lotti(
            competenza_mese=competenza_mese,
            utility_id=utility_id,
            stato_lotto=stato_lotto,
            area_geografica_id=area_geografica_id,
            tipo_doc_fiscale_id=tipo_doc_fiscale_id,
            emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            auth_user_id=auth_user_id,
            page=page,
            page_size=page_size,
        )
        return success_response(data)




class ApiLottoFattureList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato_esecuzione", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato esecuzione fattura."),
            OpenApiParameter(name="esclusa", type=bool, location=OpenApiParameter.QUERY, required=False, description="Filtro fatture escluse (true/false)."),
            OpenApiParameter(name="sort_by", type=str, location=OpenApiParameter.QUERY, required=False, description="Colonna di ordinamento (default fattura_id)."),
            OpenApiParameter(name="sort_dir", type=str, location=OpenApiParameter.QUERY, required=False, description="Direzione ordinamento: asc/desc (default asc)."),
            OpenApiParameter(name="page", type=int, location=OpenApiParameter.QUERY, required=False, description="Numero pagina (default 1)."),
            OpenApiParameter(name="page_size", type=int, location=OpenApiParameter.QUERY, required=False, description="Dimensione pagina (default 50, max 200)."),
        ],
        responses={
            200: inline_serializer(
                name="VenditeLottoFattureListResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeLottoFattureListData",
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
    # Scopo: Restituisce via GET l'elenco paginato delle fatture di un lotto con filtri e ordinamento.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        raw_stato_esecuzione = request.query_params.get("stato_esecuzione")
        stato_esecuzione = raw_stato_esecuzione.strip() or None if raw_stato_esecuzione is not None else None

        raw_esclusa = request.query_params.get("esclusa")
        esclusa = optional_bool({"esclusa": raw_esclusa}, "esclusa") if raw_esclusa is not None else None

        sort_by = request.query_params.get("sort_by", "fattura_id").strip() or "fattura_id"
        sort_dir = request.query_params.get("sort_dir", "asc").strip() or "asc"
        page = optional_int({"page": request.query_params.get("page", "1")}, "page")
        page_size = optional_int({"page_size": request.query_params.get("page_size", "50")}, "page_size")

        auth_user_id = get_scope_user_id(request)

        data = fn_list_lotto_fatture(
            lotto_id=lotto_id,
            stato_esecuzione=stato_esecuzione,
            esclusa=esclusa,
            auth_user_id=auth_user_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            page_size=page_size,
        )
        return success_response(data)




# ================================================================== #
# Commesse — push orchestrator + stato + attivita                     #
# ================================================================== #


class ApiRunCommessePush(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "run_commesse_push"
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
            source_types_raw = payload.get("source_types")
            source_types: list[str] | None = None
            if source_types_raw is not None:
                if not isinstance(source_types_raw, list) or not all(
                    isinstance(s, str) for s in source_types_raw
                ):
                    ErrorManager.raise_error(
                        code="E_COMMESSA_VALIDATION",
                        message="Parametri non validi.",
                        detail="source_types deve essere una lista di stringhe o null",
                        context={"source_types": source_types_raw},
                        function_name="vendite.api.ApiRunCommessePush.post",
                    )
                source_types = source_types_raw if source_types_raw else None
            return pr_run_commesse_push(
                source_types=source_types,
                dry_run=optional_bool(payload, "dry_run", default=False),
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)




class ApiCommessePushLog(DomainAPIView):
    area_funzionale = "vendite"
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
        data = fn_get_commesse_push_log(push_log_id=push_log_id)
        return success_response(data)




class ApiCommessaStato(DomainAPIView):
    area_funzionale = "vendite"
    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeCommessaStatoResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeCommessaStatoData",
                        fields={
                            "commessa_id": serializers.IntegerField(),
                            "stato_codice_interno": serializers.CharField(allow_null=True),
                            "stato_commessa_id": serializers.IntegerField(),
                            "stato_commessa": serializers.CharField(),
                            "chiude_commessa": serializers.BooleanField(),
                            "emittibile": serializers.BooleanField(),
                            "modificabile": serializers.BooleanField(),
                            "policy_fatturazione": serializers.CharField(allow_null=True),
                            "fatturazione_immediata": serializers.BooleanField(allow_null=True),
                            "priorita_operativa": serializers.IntegerField(allow_null=True),
                            "billing_account_id": serializers.IntegerField(allow_null=True),
                            "utility_id": serializers.IntegerField(allow_null=True),
                            "emittente_soggetto_ruolo_id": serializers.IntegerField(allow_null=True),
                            "total_attivita": serializers.IntegerField(),
                            "total_approvate": serializers.IntegerField(),
                            "total_non_approvate": serializers.IntegerField(),
                            "total_emesse": serializers.IntegerField(),
                            "total_non_emesse": serializers.IntegerField(),
                            "total_prezzo_da_riallineare": serializers.IntegerField(),
                            "last_update": serializers.CharField(allow_null=True),
                            "capabilities": serializers.DictField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET stato, contatori e capability di una commessa.
    def get(self, request: Request, commessa_id: int) -> JsonResponse:
        data = fn_get_commessa_stato(commessa_id=commessa_id)
        return success_response(data)

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
            name="VenditeCommessaStatoRequest",
            fields={"nuovo_stato": serializers.CharField()},
        ),
        responses={
            200: inline_serializer(
                name="VenditeCommessaStatoChangeResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeCommessaStatoChangeData",
                        fields={
                            "commessa_id": serializers.IntegerField(),
                            "stato_da": serializers.CharField(),
                            "stato_a": serializers.CharField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Azione di stato utente (chiudi/riapri/annulla) sulla commessa.
    def post(self, request: Request, commessa_id: int) -> JsonResponse:
        # Scopo: applica la transizione richiesta con difesa applicativa nel service.
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            user = getattr(request.user, "username", None) or None
            return cambia_stato_commessa(
                commessa_id=commessa_id,
                nuovo_stato=str(payload.get("nuovo_stato", "")),
                user=user,
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)




class ApiCommessaAttivita(DomainAPIView):
    area_funzionale = "vendite"
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


_VARIAZIONE_PREZZO_REQUEST = inline_serializer(
    name="VenditeVariazionePrezzoRequest",
    fields={
        "prezzo": serializers.DecimalField(required=True, max_digits=22, decimal_places=10),
        "motivo": serializers.CharField(required=True),
    },
)
_RIALLINEA_PREZZO_REQUEST = inline_serializer(
    name="VenditeRiallineaPrezzoRequest",
    fields={
        "conferma_versione_diversa": serializers.BooleanField(required=False),
    },
)
_SBLOCCA_PREZZO_REQUEST = inline_serializer(
    name="VenditeSbloccaPrezzoRequest",
    fields={
        "motivo": serializers.CharField(required=True),
    },
)


class ApiCommessaAttivitaRiallineaPrezzo(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_RIALLINEA_PREZZO_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeRiallineaPrezzoResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: N5 — Riallinea prezzo attivita` non fatturata dal resolver listino.
    def post(self, request: Request, commessa_id: int, att_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: fn_riallinea_prezzo(commessa_id, att_id, payload),
        )


class ApiCommessaAttivitaVariazionePrezzoEccezionale(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_VARIAZIONE_PREZZO_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeVariazionePrezzoEccezionaleResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: N7 — Override manuale prezzo su attivita` commessa LIBERA/CONFERMATA.
    def post(self, request: Request, commessa_id: int, att_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: fn_variazione_prezzo_eccezionale(commessa_id, att_id, payload),
        )


class ApiCommessaAttivitaSbloccaPrezzo(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_SBLOCCA_PREZZO_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeSbloccaPrezzoResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: N7 sblocco — Sblocca prezzo bloccato e ricalcola dal resolver.
    def post(self, request: Request, commessa_id: int, att_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: fn_sblocca_prezzo(commessa_id, att_id, payload),
        )
