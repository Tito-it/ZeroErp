from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView

from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.services.coda_lavori.repository import (
    ORIGINE_API,
    RUN_AS_OPERATORE,
    CodaLavoriRepository,
)
from apps.core.services.coda_lavori.scope import scope_key_da_emittenti
from apps.core.services.auth_helpers import (
    extract_emittente_attivo_from_request,
    extract_identita_id_from_request,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.db.vendite_repository import VenditeRepository
from apps.core.api.payload_validators import (
    optional_bool,
    optional_int,
    optional_iso_date,
    optional_uuid,
    qp_int_strict,
    qp_iso_date_optional,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.vendite.services._fatturazione_job_helpers import (
    JOB_TYPE_FATTURAZIONE_GIRO,
    JOB_TYPE_FATTURAZIONE_NUMERA,
    gruppi_digest,
    parse_gruppi,
)
from apps.vendite.services.commesse_service import (
    aggiungi_onere_commessa,
    annulla_attivita_manuale,
    approva_attivita_competenza,
    approva_commessa_attivita,
    cambia_stato_commessa,
    fn_get_commessa_stato,
    fn_get_commesse_push_log,
    fn_list_commessa_attivita,
    fn_riallinea_prezzo,
    fn_sblocca_prezzo,
    fn_variazione_prezzo_eccezionale,
    pr_run_commesse_push,
)
from apps.vendite.services.lotto_segnalazioni_service import LIVELLO_CRITICO
from apps.vendite.services.pipeline_service import (
    esiti_fatturazione,
    fn_get_lotto_segnalazioni_summary,
    fn_get_lotto_task_runs,
    fn_annulla_lotto_da_draft,
    fn_riporta_lotto_a_draft,
    fn_elimina_fattura_da_lotto,
    numera_lotto,
    ristampa_lotto,
    run_lotto_pipeline,
    run_lotto_pipeline_until_done,
)
from apps.vendite.services.vendite_service import (
    fn_get_lotto,
    fn_export_lotti,
    fn_list_lotti,
    fn_list_lotto_fatture,
    fn_lotti_mensile,
)

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
    # Scopo: Restituisce via GET il riepilogo segnalazioni del lotto + l'ELENCO
    #        del livello richiesto (default: le critiche, che sono quelle che
    #        fermano il lotto e quindi la domanda con cui si apre la scheda).
    # ⚠️ `livello` e non `severity`/`status`: nome italiano come il resto dei
    #    query param di dominio, e comunque MAI `format` o altri nomi che DRF
    #    intercetta (memoria feedback_drf_format_magic_param).
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        livello = (request.query_params.get("livello") or LIVELLO_CRITICO).strip().upper()
        data = fn_get_lotto_segnalazioni_summary(lotto_id=lotto_id, livello=livello)
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
            result = fn_annulla_lotto_da_draft(lotto_id=lotto_id)
            return result

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)




class ApiRiportaLottoADraft(DomainAPIView):
    # Fase 6 — ritorno del lotto a bozza. E' un'AZIONE DELL'OPERATORE, non un
    # task di pipeline: sta qui come endpoint e NON in `ALLOWED_TASK_FUNCTIONS`
    # (raccomandazione del team DB nel brief §4), esattamente come le due
    # funzioni di reset che le stanno accanto.
    # Gate: riusa `reset_lotto_draft`, l'azione di processo dell'annullamento.
    # E' la stessa classe di potere — cancellare fatture pre-fiscali di un
    # lotto — e chi puo' annullare un lotto puo' a maggior ragione rimetterlo
    # in lavorazione. Se un domani si volesse separare, serve un codename nuovo
    # a catalogo: non si inventa qui.
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
            name="VenditeRiportaLottoADraftRequest",
            fields={},
        ),
        responses={
            200: inline_serializer(
                name="VenditeRiportaLottoADraftResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeRiportaLottoADraftData",
                        fields={
                            "updated_lotti": serializers.IntegerField(),
                            "updated_attivita": serializers.IntegerField(),
                            "deleted_fatture": serializers.IntegerField(),
                            "deleted_righe": serializers.IntegerField(),
                            "riemesse_attivita": serializers.IntegerField(),
                            "annullati_task_run": serializers.IntegerField(),
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
            return dict(fn_riporta_lotto_a_draft(lotto_id=lotto_id))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiResetLottoFatturaDraft(DomainAPIView):
    """Elimina UNA fattura pre-fiscale dal lotto, liberandone le attivita'.

    ⚠️ Il perimetro del LOTTO e' passato da DRAFT a pre-fiscale (DRAFT o
    EMESSA) con la slice 6-B del 2026-08-04: e' lo stesso confine delle due
    azioni sul lotto intero, ed e' quello che il drawer applicava gia' — prima
    la chiamata su un lotto EMESSA falliva. URL e permesso NON seguono la
    rinomina della funzione DB: sono contratti verso client e catalogo permessi.
    """

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
                            # Quarto contatore dal 2026-08-04 (slice 6-B):
                            # attivita' di commessa tornate NON_EMESSA.
                            "riemesse_attivita": serializers.IntegerField(),
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
            result = fn_elimina_fattura_da_lotto(lotto_id=lotto_id, fattura_id=fattura_id)
            return result

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)




# Whitelist di ordinamento della lista lotti: derivata dalla mappa del
# repository invece che ricopiata, cosi' le due non possono divergere (stesso
# accorgimento di `_ORDER_BY_CONTRATTI` in contratti_service). La mappa e'
# l'unica fonte di verita': chi aggiunge una colonna ordinabile la tocca una
# volta sola.
_ORDER_BY_LOTTI: frozenset[str] = frozenset(VenditeRepository.LOTTI_SORT_COLUMNS)

# Codice del catalogo colonne: lista e export devono citare LA STESSA stringa,
# altrimenti l'export esporta le colonne di un'altra lista senza accorgersene.
_LISTA_CODICE_LOTTI = "vendite.lotti"


# Scopo: parsing unico di filtri e ordinamento della lista lotti, condiviso fra
#        lista (ApiLottiList) ed export (ApiLottiExportView). Un solo punto di
#        verita': il contratto dell'export e' «stessi filtri della lista», e due
#        parser separati lo romperebbero in silenzio al primo filtro aggiunto da
#        una parte sola.
#
#        `order_by` e' il `campo_sorgente` del catalogo (e' cio' che
#        <ListaConfigurabile> emette come sortField, montando le Column con
#        :field="col.campo_sorgente"), validato contro la whitelist del
#        repository: una chiave sconosciuta e' un errore esplicito, non un
#        ordinamento ignorato — la freccia a video direbbe una cosa e i dati
#        un'altra.
# Risultato: dict pronto per il **kwargs di fn_list_lotti / fn_export_lotti.
def _parse_lotti_query(qp, *, function_name: str) -> dict:
    raw_competenza = qp.get("competenza_mese")
    raw_utility = qp.get("utility_id")
    stato_lotto_raw = qp.get("stato_lotto")
    raw_area = qp.get("area_geografica_id")
    raw_tipo_doc = qp.get("tipo_doc_fiscale_id")
    raw_emittente = qp.get("emittente_soggetto_ruolo_id")

    raw_order_by = qp.get("order_by")
    order_by = raw_order_by.strip() or None if raw_order_by is not None else None
    order_dir = qp.get("order_dir")
    if order_by is not None:
        order_by, order_dir = validate_order_params(
            order_by,
            (order_dir or "asc").lower(),
            allowed_columns=_ORDER_BY_LOTTI,
            error_code="E_SEARCH_VALIDATION",
            function_name=function_name,
        )

    return {
        "competenza_mese": optional_iso_date({"competenza_mese": raw_competenza}, "competenza_mese"),
        "utility_id": optional_int({"utility_id": raw_utility}, "utility_id") if raw_utility is not None else None,
        "stato_lotto": stato_lotto_raw.strip() or None if stato_lotto_raw is not None else None,
        "area_geografica_id": optional_int({"area_geografica_id": raw_area}, "area_geografica_id") if raw_area is not None else None,
        "tipo_doc_fiscale_id": optional_int({"tipo_doc_fiscale_id": raw_tipo_doc}, "tipo_doc_fiscale_id") if raw_tipo_doc is not None else None,
        "emittente_soggetto_ruolo_id": optional_int({"emittente_soggetto_ruolo_id": raw_emittente}, "emittente_soggetto_ruolo_id") if raw_emittente is not None else None,
        "order_by": order_by,
        "order_dir": order_dir,
    }


class ApiLottiList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.lotti"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="competenza_mese", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro mese di competenza (YYYY-MM-DD)."),
            OpenApiParameter(name="utility_id", type=int, location=OpenApiParameter.QUERY, required=False, description="Filtro per utility."),
            OpenApiParameter(name="stato_lotto", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato lotto (es. DRAFT, COMPLETATO)."),
            OpenApiParameter(name="area_geografica_id", type=int, location=OpenApiParameter.QUERY, required=False, description="Filtro per area geografica fatturazione."),
            OpenApiParameter(name="tipo_doc_fiscale_id", type=int, location=OpenApiParameter.QUERY, required=False, description="Filtro per tipo documento fiscale."),
            OpenApiParameter(name="emittente_soggetto_ruolo_id", type=int, location=OpenApiParameter.QUERY, required=False, description="Filtro per emittente fiscale (soggetto_ruolo_id)."),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False, description="Colonna di ordinamento: `campo_sorgente` del catalogo lista `vendite.lotti` (codice, competenza_mese, tipo_lotto, tipo_doc_fiscale_descrizione, utility_descrizione, area_geografica_descrizione, stato_lotto, stato_operativo, stato_doc_fiscale_descrizione, data_insert, user_insert)."),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False, description="Direzione ordinamento: asc | desc (default asc)."),
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
        filtri = _parse_lotti_query(
            request.query_params, function_name="vendite.views.ApiLottiList.get",
        )

        page = optional_int({"page": request.query_params.get("page", "1")}, "page")
        page_size = optional_int({"page_size": request.query_params.get("page_size", "50")}, "page_size")

        data = fn_list_lotti(
            **filtri,
            auth_user_id=get_scope_user_id(request),
            page=page,
            page_size=page_size,
        )
        return success_response(data)


class ApiLottiExportView(DomainAPIView):
    """GET /api/v1/vendite/lotti/export/?formato=csv|xlsx

    Esporta i lotti filtrati dalla query string — **stessi parametri e stesso
    ordinamento del list endpoint**, così il file rispecchia ciò che
    l'operatore sta guardando.

    Le colonne le decide il catalogo `vendite.lotti` attraverso
    `UiService.get_lista_config`: colonne nascoste escluse, ordine e permessi
    dell'utente rispettati. L'export non ha una lista di colonne propria, che
    divergerebbe dalla tabella al primo cambio di configurazione.

    Hard cap `EXPORT_MAX_ROWS`: oltre, `E_UI_EXPORT_LIMIT_EXCEEDED` (422) —
    meglio un errore che un file troncato senza dirlo.

    NB: il parametro si chiama `formato` (italiano) e NON `format`, che DRF
    intercetta come magic parameter di content-negotiation prima della view.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.lotti"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False, description="csv (default) | xlsx"),
            OpenApiParameter(name="competenza_mese", type=str, required=False, description="Filtro mese di competenza (YYYY-MM-DD)."),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="stato_lotto", type=str, required=False),
            OpenApiParameter(name="area_geografica_id", type=int, required=False),
            OpenApiParameter(name="tipo_doc_fiscale_id", type=int, required=False),
            OpenApiParameter(name="emittente_soggetto_ruolo_id", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False, description="`campo_sorgente` del catalogo `vendite.lotti` (stessa whitelist della lista)."),
            OpenApiParameter(name="order_dir", type=str, required=False, description="asc | desc"),
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Genera il file CSV/XLSX dei lotti secondo il catalogo colonne della lista.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)
        filtri = _parse_lotti_query(
            request.query_params, function_name="vendite.views.ApiLottiExportView.get",
        )

        results, total = fn_export_lotti(
            **filtri,
            auth_user_id=get_scope_user_id(request),
            max_rows=EXPORT_MAX_ROWS + 1,
        )

        # Filtri riportati nell'intestazione del file: solo quelli valorizzati,
        # così chi riapre l'export sa che fotografia stava guardando.
        filtri_applicati = {
            chiave: str(valore)
            for chiave, valore in (
                ("competenza_mese", filtri["competenza_mese"]),
                ("stato_lotto", filtri["stato_lotto"]),
                ("utility_id", filtri["utility_id"]),
                ("area_geografica_id", filtri["area_geografica_id"]),
                ("tipo_doc_fiscale_id", filtri["tipo_doc_fiscale_id"]),
            )
            if valore is not None
        }

        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_LOTTI,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati or None,
            fmt=fmt,
        )


class ApiLottiMensile(DomainAPIView):
    """Conteggio lotti generati per mese di un anno — alimenta il badge della
    sidebar anno/mese del registro lotti (stile Lente Competenza). Read-only,
    scope emittente DB-side come la lista. Fotografia completa (nessun filtro
    stato: il badge conta i lotti generati, non quelli dello stato filtrato)."""

    area_funzionale = "vendite"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="anno",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Anno di competenza (default: anno corrente). 2000-2100.",
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeLottiMensileResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeLottiMensileData",
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
    # Scopo: Restituisce i 12 conteggi lotti/mese dell'anno per la sidebar.
    def get(self, request: Request) -> JsonResponse:
        anno = qp_int_strict(request.query_params.get("anno"), "anno", timezone.localdate().year)
        auth_user_id = get_scope_user_id(request)
        data = fn_lotti_mensile(anno=anno, auth_user_id=auth_user_id)
        return success_response(data)




class ApiLottoDetail(DomainAPIView):
    """Dettaglio testata di un singolo lotto (cockpit Fase B, drawer diagnostico).
    Le sotto-risorse (fatture / task-runs / segnalazioni) restano endpoint
    separati. Scope emittente in repo → 404 su lotto fuori scope/inesistente."""

    area_funzionale = "vendite"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeLottoDetailResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeLottoDetailData",
                        fields={
                            "id": serializers.IntegerField(),
                            "codice": serializers.CharField(),
                            "competenza_mese": serializers.CharField(allow_null=True),
                            "tipo_lotto": serializers.CharField(),
                            "utility_id": serializers.IntegerField(allow_null=True),
                            "utility_descrizione": serializers.CharField(allow_null=True),
                            "stato_lotto": serializers.CharField(),
                            "stato_operativo": serializers.CharField(),
                            "stato_doc_fiscale_id": serializers.IntegerField(allow_null=True),
                            "stato_doc_fiscale_descrizione": serializers.CharField(allow_null=True),
                            "tipo_doc_fiscale_id": serializers.IntegerField(),
                            "tipo_doc_fiscale_descrizione": serializers.CharField(allow_null=True),
                            "area_geografica_id": serializers.IntegerField(allow_null=True),
                            "area_geografica_descrizione": serializers.CharField(allow_null=True),
                            "emittente_soggetto_ruolo_id": serializers.IntegerField(allow_null=True),
                            "data_insert": serializers.CharField(allow_null=True),
                            "user_insert": serializers.CharField(),
                            # Blob capability (script.fn_available_actions_lotto):
                            # assente se il capability layer e' rotto (fallback
                            # graceful nel service) → required=False.
                            "available_actions": serializers.ListField(
                                child=serializers.DictField(), required=False,
                            ),
                            "can_change_state": serializers.BooleanField(required=False),
                            "stato_codice": serializers.CharField(
                                required=False, allow_null=True,
                            ),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET la testata del lotto + capability (scope emittente).
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        auth_user_id = get_scope_user_id(request)
        data = fn_get_lotto(lotto_id=lotto_id, auth_user_id=auth_user_id)
        return success_response(data)


class ApiLottoFattureList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato_esecuzione", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato esecuzione fattura."),
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

        sort_by = request.query_params.get("sort_by", "fattura_id").strip() or "fattura_id"
        sort_dir = request.query_params.get("sort_dir", "asc").strip() or "asc"
        page = optional_int({"page": request.query_params.get("page", "1")}, "page")
        page_size = optional_int({"page_size": request.query_params.get("page_size", "50")}, "page_size")

        auth_user_id = get_scope_user_id(request)

        data = fn_list_lotto_fatture(
            lotto_id=lotto_id,
            stato_esecuzione=stato_esecuzione,
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
    # Il POST cambia lo stato della commessa: CHIUSA e ANNULLATA sono terminali
    # irreversibili (nessun arco uscente in matrice, emittibile=false) → la
    # commessa esce per sempre dal giro di fatturazione. Prima era protetto dal
    # solo controllo d'area, mentre azioni reversibili della stessa entita'
    # (prezzo, oneri, approvazione) erano gia' gated: asimmetria chiusa dal
    # 2026-07-27 (brief-db-permesso-cambio-stato-commessa). Un solo codename per
    # i tre verbi chiudi/riapri/annulla — post_permission gatta l'ENDPOINT, non
    # la action_key; stesso schema di `cambia_stato_preventivi`. Ortogonale alle
    # capability DB (enabled/reasons dicono se l'azione e' eseguibile ORA, il
    # permesso dice se quell'operatore puo' eseguirla): i due gate si sommano.
    # NB: il GET di lettura stato resta libero nell'area.
    post_permission = "cambia_stato_commessa"
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
                            "priorita_operativa": serializers.CharField(allow_null=True),
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
    lista_codice = "vendite.commesse_attivita"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato_emissione", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato emissione (es. NON_EMESSA, EMESSA)."),
            OpenApiParameter(name="stato_approvazione", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato approvazione (es. BOZZA, APPROVATA)."),
            OpenApiParameter(name="competenza_mese", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro mese di competenza (YYYY-MM-DD)."),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False, description="Righe per pagina (default 50, max 200)."),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False, description="Offset paginazione (default 0)."),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False, description="Colonna di ordinamento (id, data_attivita, competenza_mese, segment_key, quantita, prezzo_snapshot, stato_approvazione, stato_emissione). Assente = ordine storico per id."),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False, description="Direzione ordinamento: asc | desc (default asc)."),
            OpenApiParameter(name="tipo_movimento", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro natura della riga: NORMALE | RETTIFICA | ONERE. Assente o vuoto = tutti. Un valore fuori vocabolario e' rifiutato (400), non filtra a vuoto."),
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
        # order_by/order_dir passano al service, che li valida contro la
        # whitelist ATTIVITA_SORT_COLUMNS (specchio della fn DB).
        data = fn_list_commessa_attivita(
            commessa_id=commessa_id,
            stato_emissione=stato_emissione,
            stato_approvazione=stato_approvazione,
            competenza_mese=competenza_mese,
            limit=limit,
            offset=offset,
            order_by=qp_str(request.query_params.get("order_by")),
            order_dir=qp_str(request.query_params.get("order_dir")),
            tipo_movimento=qp_str(request.query_params.get("tipo_movimento")),
        )
        return success_response(data)


class ApiCommessaAttivitaExport(DomainAPIView):
    """GET /api/v1/vendite/commesse/<id>/attivita/export/?formato=csv|xlsx

    Esporta la STESSA lista di attivita' del drawer commessa, con gli STESSI
    filtri e lo STESSO ordinamento: il file rispecchia cio' che l'operatore sta
    guardando, non una seconda lista che gli somiglia.

    Le colonne le decide il catalogo `vendite.commesse_attivita` attraverso
    `UiService.get_lista_config`: colonne nascoste escluse, ordine e permessi
    dell'utente rispettati (DEF-1). L'export non ha una lista di colonne propria,
    che divergerebbe dalla tabella al primo cambio di configurazione.

    Hard cap `EXPORT_MAX_ROWS`: oltre, `E_UI_EXPORT_LIMIT_EXCEEDED` (422) —
    meglio un errore che un file troncato senza dirlo.

    NB: il parametro si chiama `formato` (italiano) e NON `format`, che DRF
    intercetta come magic parameter di content-negotiation prima della view.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.commesse_attivita"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, location=OpenApiParameter.QUERY, required=False, description="csv (default) | xlsx"),
            OpenApiParameter(name="stato_emissione", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="stato_approvazione", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="competenza_mese", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="tipo_movimento", type=str, location=OpenApiParameter.QUERY, required=False, description="NORMALE | RETTIFICA | ONERE. Assente = tutti."),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False, description="Stessa whitelist della lista."),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False, description="asc | desc"),
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Genera il file CSV/XLSX delle attivita' di UNA commessa.
    def get(self, request: Request, commessa_id: int) -> HttpResponse:
        # Formato PRIMA della query: su formato invalido non si paga il fetch.
        fmt = parse_export_format(request)
        qp = request.query_params

        filtri = {
            "stato_emissione": qp.get("stato_emissione") or None,
            "stato_approvazione": qp.get("stato_approvazione") or None,
            "competenza_mese": qp.get("competenza_mese") or None,
            "tipo_movimento": qp_str(qp.get("tipo_movimento")),
        }
        # ⚠️ `max_rows` e non `limit`: l'export salta la paginazione invece di
        # violarne il tetto. Il `+1` non serve a troncare — il guard di
        # `build_export_response` confronta il `count` ESATTO della lista.
        data = fn_list_commessa_attivita(
            commessa_id=commessa_id,
            **filtri,
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            max_rows=EXPORT_MAX_ROWS + 1,
        )

        # Filtri riportati nell'intestazione del file: solo quelli valorizzati,
        # cosi' chi riapre l'export sa che fotografia stava guardando.
        filtri_applicati = {
            "commessa_id": str(commessa_id),
            **{k: str(v) for k, v in filtri.items() if v is not None},
        }

        return build_export_response(
            request,
            lista_codice="vendite.commesse_attivita",
            results=data["rows"],
            total=data["count"],
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


class ApiCommessaAttivitaApprova(DomainAPIView):
    """Azione APPROVA sulle attivita' di una commessa (cockpit Fase A, A-1):
    righe_ids assente = tutte le righe NON_EMESSA in BOZZA; altrimenti solo le
    righe indicate (selezione dal drawer). Idempotente (fn DB)."""

    area_funzionale = "vendite"
    post_permission = "approva_attivita_commessa"

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
            name="VenditeCommessaAttivitaApprovaRequest",
            fields={
                "righe_ids": serializers.ListField(
                    child=serializers.IntegerField(), required=False, allow_null=True,
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeCommessaAttivitaApprovaResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeCommessaAttivitaApprovaData",
                        fields={
                            "commessa_id": serializers.IntegerField(),
                            "approvate": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Approva le attivita' della commessa (tutte o selezione righe_ids).
    def post(self, request: Request, commessa_id: int) -> JsonResponse:
        # Scopo: delega al service la validazione input + esistenza + approvazione.
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            user = getattr(request.user, "username", None) or None
            return approva_commessa_attivita(
                commessa_id=commessa_id,
                righe_ids=payload.get("righe_ids"),  # type: ignore[arg-type]
                user=user,
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiCommessaOneri(DomainAPIView):
    """Porta oneri (brief-db-immutabilita-quantita-e-porta-oneri §4c): crea sulla
    commessa una riga di PURO VALORE (qta=1, `tipo_movimento=ONERE`, sourceless)
    gia' APPROVATA — causale, unita' di misura e IVA derivate dall'articolo-onere
    dalla madre DB.

    Presidio ALL'INGRESSO, non a valle (decisione Tid §4c.5): niente approvazione
    a due passi, il gate e' l'azione di processo `carica_voce_manuale` — chi
    carica oneri e' responsabile di quello che fa. L'audit resta pieno (causale +
    motivo + la riga stessa + `commesse_attivita_log`)."""

    area_funzionale = "vendite"
    post_permission = "carica_voce_manuale"

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
            name="VenditeCommessaOnereRequest",
            fields={
                "articolo_onere_id": serializers.UUIDField(required=True),
                "importo": serializers.DecimalField(
                    required=True, max_digits=22, decimal_places=10,
                ),
                "tipo_doc_fiscale_id": serializers.IntegerField(required=True),
                "istanza_utility_id": serializers.IntegerField(required=False, allow_null=True),
                "motivo": serializers.CharField(required=False, allow_null=True),
                "data_attivita": serializers.DateField(required=False, allow_null=True),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeCommessaOnereResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeCommessaOnereData",
                        fields={
                            "commessa_id": serializers.IntegerField(),
                            "attivita_id": serializers.IntegerField(),
                            "importo": serializers.CharField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Carica un onere sulla commessa (riga di valore, qta=1, APPROVATA).
    def post(self, request: Request, commessa_id: int) -> JsonResponse:
        # Scopo: estrae il payload e delega al service; guard di dominio a DB.
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return aggiungi_onere_commessa(
                commessa_id=commessa_id,
                # Grezzo: la forma (UUID) e la sua assenza le valida il service,
                # con messaggio parlante — `str(None)` darebbe "None" all'utente.
                articolo_onere_id=payload.get("articolo_onere_id"),  # type: ignore[arg-type]
                importo=payload.get("importo"),
                tipo_doc_fiscale_id=optional_int(
                    payload, "tipo_doc_fiscale_id", zero_as_none=True,
                ),
                istanza_utility_id=optional_int(
                    payload, "istanza_utility_id", zero_as_none=True,
                ),
                motivo=payload.get("motivo"),  # type: ignore[arg-type]
                data_attivita=optional_iso_date(payload, "data_attivita"),
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiFatturazioneApprovaCompetenza(DomainAPIView):
    """Azione APPROVA massiva per mese di competenza (cockpit Fase A, A-2):
    approva le attivita' in stadio DA_APPROVARE del mese — la popolazione della
    card della Dashboard Competenza (stessa vista, scope emittente in-vista).
    All-or-nothing in una transazione; idempotente (retry innocuo)."""

    area_funzionale = "vendite"
    post_permission = "approva_attivita_commessa"

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
            name="VenditeApprovaCompetenzaRequest",
            fields={
                "competenza_mese": serializers.DateField(required=True),
                "commessa_ids": serializers.ListField(
                    child=serializers.IntegerField(), required=False, allow_null=True,
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeApprovaCompetenzaResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeApprovaCompetenzaData",
                        fields={
                            "competenza_mese": serializers.CharField(),
                            "commesse": serializers.IntegerField(),
                            "approvate": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Approva in massa le attivita' DA_APPROVARE del mese di competenza.
    def post(self, request: Request) -> JsonResponse:
        # Scopo: parsing payload + delega al service (validazioni e transazione).
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            user = getattr(request.user, "username", None) or None
            return approva_attivita_competenza(
                competenza_mese=optional_iso_date(payload, "competenza_mese"),  # type: ignore[arg-type]
                commessa_ids=payload.get("commessa_ids"),  # type: ignore[arg-type]
                user=user,
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiFatturazioneNumeraLotto(DomainAPIView):
    """C-4: numerazione «Rendi definitive» di un singolo lotto EMESSA. Esegue lo
    step DEFINITIVA (numera_fatture + stampa_documenti_lotto che ACCODA, I-2):
    l'endpoint NON chiama la stampa. Gate fiscale separato (I-7): permesso
    `numera_fatture_lotti`, distinto da `genera_fatture_lotti`. Scope operatore:
    lotto fuori scope/inesistente → 404; non EMESSA → errore parlante."""

    area_funzionale = "vendite"
    post_permission = "numera_fatture_lotti"

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
        request=None,
        responses={
            200: inline_serializer(
                name="VenditeNumeraLottoResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeNumeraLottoData",
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
    # Scopo: Numera (Rendi definitive) il lotto: guard scope+EMESSA, poi step DEFINITIVA.
    def post(self, request: Request, lotto_id: int) -> JsonResponse:
        # Scopo: delega al service (guard fiscale + esecuzione step DEFINITIVA).
        def _handler(_payload: dict[str, object]) -> dict[str, object]:
            return numera_lotto(
                lotto_id=int(lotto_id),
                auth_user_id=get_scope_user_id(request),
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiFatturazioneRistampaLotto(DomainAPIView):
    """C-8: ristampa MASSIVA di un lotto DEFINITIVA. Accoda in
    `vendite.fatture_stampa_coda` una riga per ogni fattura del lotto
    (idempotente sui vivi); il worker `draina_coda_stampa` le renderizza (async,
    stato via pannello esiti C-5). Accodamento SINCRONO (INSERT veloce), non un
    job con polling. Stampa = lettura (I-4): nessun `post_permission` (come la
    stampa singola), gate readonly a carico del FE. Scope operatore: lotto fuori
    scope/inesistente → 404; non DEFINITIVA → 409 parlante (I-7: niente
    numerazione backdoor)."""

    area_funzionale = "vendite"

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
        request=None,
        responses={
            200: inline_serializer(
                name="VenditeRistampaLottoResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeRistampaLottoData",
                        fields={
                            "lotto_id": serializers.IntegerField(),
                            "accodate": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Accoda le stampe del lotto (guard scope+DEFINITIVA), ritorna il conteggio.
    def post(self, request: Request, lotto_id: int) -> JsonResponse:
        # Scopo: delega al service (guard fiscale + fn_accoda_stampe_lotto).
        def _handler(_payload: dict[str, object]) -> dict[str, object]:
            return ristampa_lotto(
                lotto_id=int(lotto_id),
                auth_user_id=get_scope_user_id(request),
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiFatturazioneEsiti(DomainAPIView):
    """C-5: esiti dei giri di fatturazione (riassunto per corsia da
    `maintenance.job_run_log`) + stato della coda stampa (conteggi per stato,
    scope emittente dell'operatore via JOIN fatture). Sola lettura (I-5: nessuna
    tabella nuova).

    `?competenza_mese=YYYY-MM-DD` (opzionale): restringe i giri a quelli
    lanciati PER quel mese di competenza — allinea il pannello al filtro della
    lista lotti. Senza il parametro i giri sono i totali da sempre."""

    area_funzionale = "vendite"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Mese di competenza (YYYY-MM-DD, normalizzato al 1° del "
                    "mese): filtra i giri lanciati per quel mese."
                ),
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeFatturazioneEsitiResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFatturazioneEsitiData",
                        fields={
                            "giri": serializers.ListField(child=serializers.DictField()),
                            "coda_stampa": serializers.DictField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce esiti giri (opz. filtrati per mese di competenza) +
    #        stato coda stampa (scope operatore).
    def get(self, request: Request) -> JsonResponse:
        competenza_mese = qp_iso_date_optional(
            request.query_params.get("competenza_mese"), "competenza_mese",
        )
        return success_response(
            esiti_fatturazione(
                auth_user_id=get_scope_user_id(request),
                competenza_mese=competenza_mese,
                # Serve allo scope dei lavori accodati dall'app (scope_key):
                # l'operatore conta i propri giri, non quelli altrui.
                user=request.user,
            ),
        )


# Scopo: Enqueue comune dei job di fatturazione OPERATORE su dbops.coda_lavori
#        (C-3 giro, C-4 numerazione di perimetro — regola del 2, ok Tid
#        2026-07-21): valida+normalizza `competenza_mese` al 1° del mese,
#        cattura l'identità COMPLETA dell'operatore (id vero anche per
#        superuser + username + identita_id dal JWT — il worker la riproporrà
#        per intero, 5 GUC, RLS come nel web) e lo scope emittente, compone la
#        chiave di BUSINESS `{job_type}:{mese}:{scope}` (dedup dei job VIVI) e
#        accoda. `extra_payload_keys`: chiavi opzionali del payload HTTP da
#        propagare al payload del job (es. `fino_a_stato` del giro). Ritorna
#        l'handle `{job_id, stato}` per la risposta.
#
#        `accetta_gruppi=True` (emissione mirata, solo il giro): valida la
#        lista dei gruppi fatturabili e la porta nel payload del job. ⚠️ In quel
#        caso la chiave di business include un DIGEST dei gruppi: senza,
#        due emissioni mirate sullo stesso mese e scope con gruppi diversi
#        cadrebbero sullo stesso job vivo e la seconda verrebbe assorbita in
#        silenzio (l'operatore vede «accodato» e non succede nulla). Senza
#        gruppi il digest e' vuoto → chiave IDENTICA a prima per il giro di
#        massa (nessuna regressione sulla dedup esistente).
def _accoda_job_fatturazione(
    request: Request,
    payload: dict[str, object],
    *,
    job_type: str,
    extra_payload_keys: tuple[str, ...] = (),
    accetta_gruppi: bool = False,
) -> dict[str, object]:
    competenza = optional_iso_date(payload, "competenza_mese")
    ErrorManager.require(
        competenza is not None,
        code="E_VALIDATION_INPUT",
        message="`competenza_mese` obbligatoria.",
    )
    assert competenza is not None
    # Normalizza al 1° del mese PRIMA di comporre payload+chiave business: la
    # dedup dei job vivi è per-MESE, non per-giorno.
    competenza = competenza.replace(day=1)
    # Identità dell'operatore che accoda: id VERO (`user.id`, anche per
    # superuser — NON `get_scope_user_id`, che per superuser è None e
    # bloccherebbe l'admin globale) + username + identita_id dal JWT.
    user = request.user
    identita_id = extract_identita_id_from_request(request)
    ErrorManager.require(
        identita_id is not None,
        code="E_VALIDATION_INPUT",
        message="Identità operatore non risolta dal token.",
    )
    # Emittente ATTIVO congelato ora: il worker esegue minuti dopo, senza
    # token, e senza questo valore girerebbe in modalità globale — un giro
    # chiesto «dentro A» toccherebbe anche B. Va catturato PRIMA dello scope,
    # perché lo scope stesso ne risente: dal 2026-08-04 le funzioni di scope
    # intersecano con l'emittente attivo, quindi `emittente_ids` (e con esso
    # `scope_key`, che governa dedup e ownership del polling) riflette già
    # l'impersonazione. Le due cose devono raccontare la stessa storia.
    emittente_attivo_id = extract_emittente_attivo_from_request(request)
    # Scope emittente CATTURATO ora (None = admin globale): serve al vincolo
    # DB run_as↔scope, all'idempotenza di business e all'audit.
    emittente_ids = PermissionResolver.get_emittenti_ids(user)
    # Chiave canonica dello scope (BB core `coda_lavori.scope` — fonte unica
    # del formato, condivisa con polling/liste/badge della UI code).
    scope_key = scope_key_da_emittenti(emittente_ids)
    job_payload: dict[str, object] = {"competenza_mese": competenza.isoformat()}
    for key in extra_payload_keys:
        value = payload.get(key)
        if value:
            job_payload[key] = value

    # Perimetro dell'emissione mirata: validato QUI (400 parlante al chiamante)
    # e non solo nel worker, dove diventerebbe un job fallito da leggere nei log.
    gruppi = (
        parse_gruppi(payload.get("gruppi"), error_code="E_VALIDATION_INPUT")
        if accetta_gruppi
        else None
    )
    if gruppi:
        job_payload["gruppi"] = list(gruppi)

    # Chiave di BUSINESS (competenza + scope [+ gruppi]), NON l'header HTTP:
    # dedup dei job VIVI (due click sullo stesso mese/scope → stesso job).
    # Il digest e' vuoto senza gruppi: la chiave del giro di massa resta quella
    # storica, quella mirata cambia con il perimetro selezionato.
    digest = gruppi_digest(gruppi)
    idempotency_key = f"{job_type}:{competenza.isoformat()}:{scope_key}"
    if digest:
        idempotency_key = f"{idempotency_key}:{digest}"

    job_id = CodaLavoriRepository().accoda(
        job_type=job_type,
        payload=job_payload,
        run_as=RUN_AS_OPERATORE,
        scope={
            "auth_user_id": int(user.id),
            "username": str(user.username),
            "identita_id": identita_id,
            "emittente_attivo_id": emittente_attivo_id,
            "emittente_ids": emittente_ids,
            # Token di ownership del polling: scope-based (chi condivide lo
            # scope vede il job condiviso via dedup). Vedi scope_key_da_emittenti.
            "scope_key": scope_key,
        },
        idempotency_key=idempotency_key,
        origine=ORIGINE_API,
    )
    return {"job_id": job_id, "stato": "PENDING"}


class ApiFatturazioneRun(DomainAPIView):
    """C-3: avvia un GIRO di fatturazione on-demand, NON bloccante (I-3).
    Accoda un job `FATTURAZIONE_GIRO` in `dbops.coda_lavori` con lo scope
    emittente CATTURATO dell'operatore (run_as=OPERATORE) e risponde subito con
    l'handle del job (id + stato); il worker lo esegue poi con i permessi
    dell'operatore (RLS). Idempotenza a DUE layer: header HTTP (`handle_post_json`
    + `dbops.idempotency_keys`, replay della risposta) e chiave di BUSINESS
    della coda (competenza+scope[+gruppi], dedup dei giri VIVI).

    **Due perimetri, un solo verbo** (BF-2, emissione mirata): senza `gruppi` e'
    il giro di massa del mese, esattamente come prima; con `gruppi` e' una
    EMISSIONE MIRATA sui soli gruppi fatturabili indicati (un documento
    sorgente, oppure gli oneri di una commessa). Entrambi si fermano a EMESSA:
    la numerazione resta l'atto separato «Rendi definitive» (gate I-7).
    Le chiavi di gruppo sono quelle esposte da
    `GET /vendite/dashboard-competenza/gruppi/` — non si costruiscono a mano."""

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
            name="VenditeFatturazioneRunRequest",
            fields={
                "competenza_mese": serializers.DateField(required=True),
                "fino_a_stato": serializers.CharField(required=False, allow_null=True),
                "gruppi": serializers.ListField(
                    child=serializers.CharField(),
                    required=False,
                    allow_null=True,
                    help_text=(
                        "Emissione mirata: chiavi dei gruppi fatturabili da "
                        "fatturare (da dashboard-competenza/gruppi/). Assente = "
                        "giro di massa del mese."
                    ),
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeFatturazioneRunResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFatturazioneRunData",
                        fields={
                            "job_id": serializers.IntegerField(),
                            "stato": serializers.CharField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Accoda il giro (transazionale) e ritorna l'handle del job.
    def post(self, request: Request) -> JsonResponse:
        # Scopo: enqueue comune + `fino_a_stato` opzionale e `gruppi` (mirata).
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return _accoda_job_fatturazione(
                request, payload,
                job_type=JOB_TYPE_FATTURAZIONE_GIRO,
                extra_payload_keys=("fino_a_stato",),
                accetta_gruppi=True,
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiFatturazioneRunStato(DomainAPIView):
    """C-3: stato di un giro accodato (polling NON bloccante). Ownership:
    l'operatore vede solo i giri che HA accodato (un giro altrui → 404,
    indistinguibile da inesistente)."""

    area_funzionale = "vendite"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeFatturazioneRunStatoResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFatturazioneRunStatoData",
                        fields={
                            "id": serializers.IntegerField(),
                            "job_type": serializers.CharField(),
                            "stato": serializers.CharField(),
                            "tentativi": serializers.IntegerField(),
                            "max_tentativi": serializers.IntegerField(),
                            "result": serializers.DictField(allow_null=True),
                            "ultimo_errore": serializers.DictField(allow_null=True),
                            "job_run_id": serializers.IntegerField(allow_null=True),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce lo stato del job, con ownership SCOPE-based (non
    #        per-enqueuer): l'operatore vede i job della propria scope_key —
    #        così due operatori con la STESSA whitelist che condividono un giro
    #        via dedup ne seguono entrambi l'avanzamento (fix cross-operatore).
    #        Admin globale (whitelist None) → nessun filtro (vede ogni job).
    def get(self, request: Request, job_id: int) -> JsonResponse:
        emittente_ids = PermissionResolver.get_emittenti_ids(request.user)
        owner_scope_key = (
            None if emittente_ids is None
            else scope_key_da_emittenti(emittente_ids)
        )
        stato = CodaLavoriRepository().get_stato(
            int(job_id), owner_scope_key=owner_scope_key,
        )
        ErrorManager.require(
            stato is not None,
            code="E_JOB_NON_TROVATO",
            message="Giro di fatturazione non trovato.",
            detail=f"job_id={job_id}",
        )
        assert stato is not None
        return success_response(stato)


class ApiFatturazioneNumera(DomainAPIView):
    """C-4: «Rendi definitive competenza» — numerazione di PERIMETRO, NON
    bloccante (I-3). Accoda un job `FATTURAZIONE_NUMERA` in `dbops.coda_lavori`
    con l'identità operatore CATTURATA (run_as=OPERATORE) e risponde subito con
    l'handle del job; il worker esegue lo step DEFINITIVA (numera + accoda
    stampa) sui lotti EMESSA del mese, sotto RLS operatore. Atto fiscale
    SEPARATO dalla fatturazione (gate I-7): endpoint e permesso dedicati.
    Polling: `GET /vendite/fatturazione/run/<job_id>/` (stato job generico,
    ownership operatore). Idempotenza a DUE layer: header HTTP + chiave di
    BUSINESS della coda (competenza+scope, dedup dei numera VIVI)."""

    area_funzionale = "vendite"
    post_permission = "numera_fatture_lotti"

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
            name="VenditeFatturazioneNumeraRequest",
            fields={
                "competenza_mese": serializers.DateField(required=True),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeFatturazioneNumeraResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFatturazioneNumeraData",
                        fields={
                            "job_id": serializers.IntegerField(),
                            "stato": serializers.CharField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Accoda la numerazione di perimetro e ritorna l'handle del job.
    def post(self, request: Request) -> JsonResponse:
        # Scopo: enqueue comune (nessuna chiave extra: solo competenza_mese).
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return _accoda_job_fatturazione(
                request, payload, job_type=JOB_TYPE_FATTURAZIONE_NUMERA,
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


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
_ANNULLA_RIGA_REQUEST = inline_serializer(
    name="VenditeAnnullaRigaCommessaRequest",
    fields={
        "motivo": serializers.CharField(required=True),
    },
)


class ApiCommessaAttivitaRiallineaPrezzo(DomainAPIView):
    """N5 — riallineo prezzo da listino. Gate `prezzo_override_manuale` (T2 del
    brief porta-oneri): toccare il prezzo di una riga di commessa e' l'azione
    su cui l'autorizzazione conta di piu', e finora bastava la scrittura d'area.
    Stesso codename gia' vivo sui gate prezzo di preventivi/contratti/DDT."""

    area_funzionale = "vendite"
    post_permission = "prezzo_override_manuale"

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
    """N7 — override manuale del prezzo. Gate `prezzo_override_manuale` (T2)."""

    area_funzionale = "vendite"
    post_permission = "prezzo_override_manuale"

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
    """N7-sblocco — rimuove il blocco e ricalcola dal resolver. Stesso gate
    `prezzo_override_manuale` (T2): sbloccare cambia il prezzo della riga."""

    area_funzionale = "vendite"
    post_permission = "prezzo_override_manuale"

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


class ApiCommessaAttivitaAnnulla(DomainAPIView):
    """Annulla una riga MANUALE di commessa caricata per errore
    (brief-annullamento-righe-manuali-commessa §5). Non cancella: porta
    `stato_emissione` ad `ANNULLATA` — valore che tutte le porte verso fattura e
    cockpit gia' filtrano — e traccia il motivo nell'evento di log.

    Gate `carica_voce_manuale` (decisione Tid §5): chi puo' caricare una voce
    manuale puo' annullarla, nessun permesso dedicato. Perimetro chiuso dai
    guard del service + della madre DB: righe sourceless, non ancora emesse,
    su commessa modificabile."""

    area_funzionale = "vendite"
    post_permission = "carica_voce_manuale"

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
        request=_ANNULLA_RIGA_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeAnnullaRigaCommessaResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeAnnullaRigaCommessaData",
                        fields={
                            "commessa_id": serializers.IntegerField(),
                            "attivita_id": serializers.IntegerField(),
                            "stato_emissione": serializers.CharField(),
                            "motivo": serializers.CharField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Annulla una riga manuale (onere) non ancora emessa della commessa.
    def post(self, request: Request, commessa_id: int, att_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: annulla_attivita_manuale(commessa_id, att_id, payload),
            require_idempotency_key=True,
        )
