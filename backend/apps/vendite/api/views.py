from typing import Any
from datetime import date

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.api.constants import DEFAULT_LIMIT, DEFAULT_LIMIT_EVENTI, MAX_LIMIT
from apps.core.api.base_views import DomainAPIView
from apps.core.api.permissions import PassaggioDocumento

from apps.core.api.endpoint_helpers import (
    UnitaDiLavoro,
    get_scope_user_id,
    handle_post_json,
)
from apps.core.services.coda_lavori.repository import (
    ORIGINE_API,
    RUN_AS_OPERATORE,
    CodaLavoriRepository,
)
from apps.core.services.coda_lavori.scope import (
    scope_key_da_emittenti,
    scope_operatore_da_request,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.db.vendite_repository import VenditeRepository
from apps.core.api.payload_validators import (
    corpo_oggetto,
    pagina_da_query,
    optional_bool,
    optional_int,
    optional_iso_date,
    optional_uuid,
    parse_list_params,
    qp_bool_optional,
    qp_int_strict,
    qp_int_optional,
    qp_iso_date_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.openapi_params import parametri_finestra, descrizione_order_by
from apps.vendite.db.vendite_repository import (
    GIORNALE_GRAVITA,
    GIORNALE_ORDINE_DEFAULT,
    GIORNALE_SORT_COLUMNS,
)
from apps.vendite.api._giornale_params import (
    EMITTENTE_PARAM_GIORNALE_ENTITA,
    PARAMS_LISTA_GIORNALE_ENTITA,
    parametri_lista_giornale_entita,
)
from apps.core.api.success_responses import success_response
from apps.core.services.service_errors import E_VALIDATION_INPUT
from apps.vendite.services._fatturazione_job_helpers import (
    JOB_TYPE_FATTURAZIONE_GIRO,
    JOB_TYPE_FATTURAZIONE_NUMERA,
    chiave_idempotenza_giro,
    corsia_del_giro,
    insieme_digest,
    parse_lotti,
    parse_gruppi,
)
from apps.vendite.services.commesse_service import (
    aggiorna_commessa_testata,
    aggiungi_onere_commessa,
    annulla_attivita_manuale,
    approva_attivita_competenza,
    approva_commessa_attivita,
    cambia_stato_commessa,
    fn_get_commessa_stato,
    fn_get_commesse_push_log,
    fn_commessa_registro,
    fn_list_commessa_attivita,
    fn_riallinea_prezzo,
    fn_sblocca_prezzo,
    fn_variazione_prezzo_eccezionale,
    pr_run_commesse_push,
)
from apps.vendite.db.commesse_repository import TESTATA_COMMESSE
from apps.vendite.db.pipeline_repository import LOTTO_LISTE_PAGINA_MAX
from apps.vendite.services.pipeline_service import (
    finestra_numerazione,
    esiti_fatturazione,
    fn_get_lotto_segnalazioni_summary,
    fn_get_lotto_task_runs,
    fn_list_lotto_segnalazioni,
    fn_annulla_lotto_da_draft,
    fn_riporta_lotto_a_draft,
    fn_elimina_fattura_da_lotto,
    fn_escludi_documenti_da_giro,
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
    fn_list_lotto_gruppi,
    fn_lotti_mensile,
    get_lotto_giornale,
    get_giornale_trasversale,
)
from apps.vendite.types import AnnullaLottoDaDraftResult, EliminaFatturaDaLottoResult

# View API vendite: espone endpoint HTTP per avviare pipeline lotto.


# Scopo: Estrae i kwargs comuni della pipeline lotto dal payload JSON. Condiviso da
#        ApiRunLottoPipeline (single step) e ApiRunLottoPipelineUntilDone (driver),
#        per evitare duplicazione/disallineamento dei parametri.
def _run_lotto_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
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


# Scopo: I campi dell'ESITO del driver di pipeline, per i due endpoint che lo
#        ritornano (avanza fino in fondo, numera lotto).
#
# ⚠️ IL FALLIMENTO E' DENTRO IL PAYLOAD, NON NELLO STATUS. Questi endpoint
#    rispondono **200 anche quando la catena si ferma**, perche' puo' aver
#    eseguito qualche step prima di fermarsi e quel lavoro va raccontato: chi
#    legge DEVE guardare `motivo_stop`. Un 200 non e' un successo — difetto
#    misurato in-app il 2026-08-21, il toast verde su un lotto che il database
#    aveva rifiutato.
#
# ⭐ `errore` porta gli STESSI nomi dell'envelope d'errore — `code`, `message`,
#    `detail`, `hint`, `fields`, `targets` — cosi' che a video il gesto lo
#    disegni un consumatore solo.
#
# ⚠️ Definito UNA volta: i due `@extend_schema` lo chiamano. Erano due copie
#    identiche, cioe' due punti in cui divergere sul contratto di una risposta.
#
# ⛔ ED E' UNA FUNZIONE, NON UNA COSTANTE — misurato, non supposto. Con un dict
#    a livello di modulo i due `inline_serializer` condividerebbero le STESSE
#    ISTANZE di campo, e un campo DRF si lega al proprio serializer: il secondo
#    componente esce dallo schema **senza nemmeno la chiave `data`**. Verificato
#    con `manage.py spectacular`: `VenditeNumeraLottoResponse` conteneva il solo
#    `meta`. Non fallisce niente e nessun test lo vede — il contratto pubblicato
#    e' semplicemente sbagliato, che e' il modo peggiore di romperlo.
def _esito_runner_fields() -> dict[str, serializers.Field]:
    return {
        "lotto_id": serializers.IntegerField(allow_null=True),
        "stato_lotto": serializers.CharField(allow_null=True),
        "stato_doc_fiscale_id": serializers.IntegerField(allow_null=True),
        "step_eseguiti": serializers.IntegerField(),
        "motivo_stop": serializers.CharField(),
        "errore": serializers.DictField(required=False, allow_null=True),
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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            lotto_id = run_lotto_pipeline(**_run_lotto_kwargs(payload))
            return {"lotto_id": lotto_id, "status": "ok"}

        # Pattern condiviso: JSON parse + envelope errori centralizzato.
        # ⭐ A_PASSI (brief-be-verifica-documentazione-api §I.7.2): il lotto nasce in una transazione sua e l'errore si scrive fuori dall'atomic dello step (D-12).
        #    Una key orfana non si riprende, e niente `atomic` esterno.
        return handle_post_json(
            request, handler=_handler, require_idempotency_key=True,
            unita_di_lavoro=UnitaDiLavoro.A_PASSI,
        )


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
                        fields=_esito_runner_fields(),
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Gestisce la richiesta HTTP POST: esegue il driver fino a conclusione.
    def post(self, request: Request) -> JsonResponse:
        # Scopo: Gestisce la logica interna del caso d'uso richiamato dall'endpoint.
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return run_lotto_pipeline_until_done(**_run_lotto_kwargs(payload))

        # Pattern condiviso: JSON parse + envelope errori centralizzato.
        # ⭐ A_PASSI (brief-be-verifica-documentazione-api §I.7.2): concatena gli step, ognuno col suo commit; risponde 200 anche con lavoro parziale.
        #    Una key orfana non si riprende, e niente `atomic` esterno.
        return handle_post_json(
            request, handler=_handler, require_idempotency_key=True,
            unita_di_lavoro=UnitaDiLavoro.A_PASSI,
        )


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
    # Scopo: Restituisce via GET il RIEPILOGO segnalazioni del lotto (conteggi
    #        + blocco avanzamento). Alimenta il banner di testata.
    # ⚠️ Le RIGHE stanno su un endpoint suo (`/segnalazioni/rows/`): questo lo
    #    chiede il drawer a ogni apertura, e portarsi dietro l'elenco per
    #    mostrarne un numero sarebbe lavoro a ogni giro.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        return success_response(fn_get_lotto_segnalazioni_summary(
            lotto_id=lotto_id, auth_user_id=get_scope_user_id(request),
        ))




class ApiLottoSegnalazioniRows(DomainAPIView):
    """GET /api/v1/vendite/lotti/<id>/segnalazioni/rows/ — elenco PAGINATO delle
    segnalazioni del lotto (`vendite.fn_list_lotto_segnalazioni`): le due origini
    — log di fattura e log di lotto — in un elenco solo, col documento e
    l'importo gia' composti.

    Filtri opzionali: `livello` (C/W/I), `origine` (FATTURA/LOTTO),
    `solo_attive` (default true: le ritirate non si mostrano), `solo_job_corrente`
    (default false). `fuori_job_count` dice quante restano fuori dall'ultima
    corsa: senza, un elenco filtrato e uno vuoto si leggono uguali."""

    area_funzionale = "vendite"
    # Lista configurabile 47.
    lista_codice = "vendite.lotto_segnalazioni"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="livello", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="origine", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="solo_attive", type=bool, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="solo_job_corrente", type=bool, location=OpenApiParameter.QUERY),
            *parametri_finestra(max_limit=LOTTO_LISTE_PAGINA_MAX),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY),
        ],
        responses={200: inline_serializer(
            name="LottoSegnalazioniRowsResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: elenco paginato delle segnalazioni del lotto.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        q = request.query_params
        limit, offset = pagina_da_query(q, max_limit=LOTTO_LISTE_PAGINA_MAX)
        data = fn_list_lotto_segnalazioni(
            lotto_id=lotto_id,
            auth_user_id=get_scope_user_id(request),
            livello=(q.get("livello") or None),
            origine=(q.get("origine") or None),
            solo_attive=qp_bool_optional(q.get("solo_attive"), "solo_attive", default=True),
            solo_job_corrente=qp_bool_optional(q.get("solo_job_corrente"), "solo_job_corrente", default=False),
            limit=limit,
            offset=offset,
            order_by=(q.get("order_by") or None),
            order_dir=(q.get("order_dir") or "desc"),
        )
        return success_response(data)


class ApiLottoSegnalazioniExport(DomainAPIView):
    """GET /api/v1/vendite/lotti/<id>/segnalazioni/export/?formato=csv|xlsx

    Esporta la STESSA lista di segnalazioni della scheda, con gli STESSI filtri
    e lo STESSO ordinamento: il file rispecchia cio' che l'operatore sta
    guardando, non una seconda lista che gli somiglia.

    Le colonne le decide il catalogo `vendite.lotto_segnalazioni` attraverso
    `UiService.get_lista_config`: nascoste escluse, ordine e permessi rispettati.

    NB: il parametro si chiama `formato` e NON `format`, che DRF intercetta
    come magic parameter prima della view.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.lotto_segnalazioni"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="livello", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="origine", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={(200, "text/csv"): bytes},
    )
    # Scopo: file CSV/XLSX delle segnalazioni del lotto.
    def get(self, request: Request, lotto_id: int) -> HttpResponse:
        # Formato PRIMA della query: su formato invalido non si paga il fetch.
        fmt = parse_export_format(request)
        q = request.query_params
        filtri: dict[str, Any] = {"livello": q.get("livello") or None, "origine": q.get("origine") or None}
        data = fn_list_lotto_segnalazioni(
            lotto_id=lotto_id,
            auth_user_id=get_scope_user_id(request),
            **filtri,
            solo_attive=qp_bool_optional(q.get("solo_attive"), "solo_attive", default=True),
            solo_job_corrente=qp_bool_optional(q.get("solo_job_corrente"), "solo_job_corrente", default=False),
            order_by=(q.get("order_by") or None),
            order_dir=(q.get("order_dir") or "desc"),
            # ⚠️ `max_rows` e non `page_size`: l'export salta la paginazione
            # invece di violarne il tetto. Il `+1` non tronca — serve al guard
            # di `build_export_response`, che confronta il `count` ESATTO.
            max_rows=EXPORT_MAX_ROWS + 1,
        )
        return build_export_response(
            request,
            lista_codice="vendite.lotto_segnalazioni",
            results=data["results"],
            total=data["count"],
            filtri_applicati={
                "lotto_id": str(lotto_id),
                **{k: str(v) for k, v in filtri.items() if v is not None},
            },
            fmt=fmt,
        )


# Scopo: normalizza il filtro multi-valore `task_stato` della scheda Task del
#        drawer lotto. Accetta sia la ripetizione (`?task_stato=A&task_stato=B`,
#        forma naturale di DRF) sia l'elenco separato da virgole
#        (`?task_stato=A,B`, quello che manda il client): un solo lettore per
#        entrambe, invece di due contratti da tenere allineati.
# ⚠️ MAIUSCOLO come ogni filtro a vocabolario del progetto (cfr. `qp_str_upper`).
# ⛔ L'elenco degli stati AMMESSI non si dichiara qui: lo possiede
#    `vendite.fn_list_lotto_task_runs`, e uno stato che non conosce non aggiunge
#    e non toglie nulla. Ricopiarlo sarebbe la seconda verita' sullo stesso
#    vocabolario — la stessa ragione per cui `order_by` passa intatto.
def _qp_task_stato(query_params) -> list[str] | None:
    grezzi: list[str] = []
    for valore in query_params.getlist("task_stato"):
        grezzi.extend(valore.split(","))
    stati = [v.strip().upper() for v in grezzi if v.strip()]
    return stati or None


class ApiLottoTaskRunsExport(DomainAPIView):
    """GET /api/v1/vendite/lotti/<id>/task-runs/export/?formato=csv|xlsx

    I tentativi dei task del lotto, colonne dal catalogo
    `vendite.lotto_task_runs`."""

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.lotto_task_runs"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="task_stato", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="solo_giro_corrente", type=bool, location=OpenApiParameter.QUERY, required=False
            ),
        ],
        responses={(200, "text/csv"): bytes},
    )
    # Scopo: file CSV/XLSX dei tentativi dei task del lotto.
    # ⚠️ I due filtri viaggiano anche qui, ed e' il punto: il file E' la lista.
    #    Un export che ignorasse lo stato scelto conterrebbe le 90 righe mentre
    #    a video se ne vedono 10 — e finirebbero in mano a qualcuno come «i
    #    task di quel lotto».
    def get(self, request: Request, lotto_id: int) -> HttpResponse:
        fmt = parse_export_format(request)
        q = request.query_params
        task_stato = _qp_task_stato(q)
        solo_giro_corrente = qp_bool_optional(q.get("solo_giro_corrente"), "solo_giro_corrente", default=False)
        data = fn_get_lotto_task_runs(
            lotto_id=lotto_id,
            auth_user_id=get_scope_user_id(request),
            order_by=(q.get("order_by") or None),
            order_dir=(q.get("order_dir") or "desc"),
            task_stato=task_stato,
            solo_giro_corrente=solo_giro_corrente,
            max_rows=EXPORT_MAX_ROWS + 1,
        )
        # I filtri finiscono nell'intestazione del file: chi lo riapre fra un
        # mese deve poter sapere di quale fetta si tratta.
        filtri_applicati: dict[str, str] = {"lotto_id": str(lotto_id)}
        if task_stato:
            filtri_applicati["task_stato"] = ",".join(task_stato)
        if solo_giro_corrente:
            filtri_applicati["solo_giro_corrente"] = "true"
        return build_export_response(
            request,
            lista_codice="vendite.lotto_task_runs",
            results=data["results"],
            total=data["count"],
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


class ApiLottoTaskRuns(DomainAPIView):
    area_funzionale = "vendite"
    # Lista configurabile 46.
    lista_codice = "vendite.lotto_task_runs"
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=f"Numero massimo task run restituiti (default {DEFAULT_LIMIT_EVENTI}, max {LOTTO_LISTE_PAGINA_MAX}).",
            ),
            OpenApiParameter(
                name="offset", type=int, location=OpenApiParameter.QUERY, required=False,
                description="Righe da saltare (default 0).",
            ),
            OpenApiParameter(
                name="task_stato",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro sullo stato del tentativo. Multi-valore: ripetibile "
                    "(`task_stato=ERRORE&task_stato=COMPLETATO`) oppure separato da "
                    "virgole (`task_stato=ERRORE,COMPLETATO`). Assente = nessun filtro. "
                    "Il vocabolario ammesso lo possiede la funzione DB: uno stato che non "
                    "conosce non aggiunge e non toglie nulla."
                ),
            ),
            OpenApiParameter(
                name="solo_giro_corrente",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Limita all'ultima PASSATA della pipeline (ancora: l'ultimo "
                    "`PIPELINE_STARTED`). ⚠️ Passata, NON azione dell'operatore: "
                    "`run_lotto_pipeline_until_done` ne incatena piu' d'una, quindi un solo "
                    "click puo' restare tagliato a meta'. Leggere sempre `esclusi_count` "
                    "insieme al risultato."
                ),
            ),
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
                            "esclusi_count": serializers.IntegerField(),
                            "task_runs": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET i task run del lotto — elenco PAGINATO e
    #        ordinabile (BE-2, 2026-08-22): la sorgente e'
    #        `vendite.fn_list_lotto_task_runs`, che porta anche il totale.
    # ⛔ `limit`/`offset` come ogni lista offset-based (decisione Tid
    #    2026-10-21, §A4: nomi allineati, BE e FE nello stesso giro, senza
    #    alias). Fino a quel giorno si leggeva `page_size` con `limit` come
    #    sinonimo, accanto a un `offset`: un dialetto ibrido che nessun'altra
    #    lista parlava. `page`/`page_size` ora sono un 400.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        q = request.query_params
        limit, offset = pagina_da_query(
            q, default_limit=DEFAULT_LIMIT_EVENTI, max_limit=LOTTO_LISTE_PAGINA_MAX,
        )
        data = fn_get_lotto_task_runs(
            lotto_id=lotto_id,
            auth_user_id=get_scope_user_id(request),
            limit=limit,
            offset=offset,
            order_by=(q.get("order_by") or None),
            order_dir=(q.get("order_dir") or "desc"),
            # ⭐ I due filtri del `20260824-11`. ⚠️ Nessuno dei due ha un default
            #    che nasconde righe: chi chiama senza vede quello che vedeva
            #    prima. La scelta di quale fetta mostrare all'apertura e' del
            #    client, non dell'endpoint.
            task_stato=_qp_task_stato(q),
            solo_giro_corrente=qp_bool_optional(q.get("solo_giro_corrente"), "solo_giro_corrente", default=False),
        )
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
        def _handler(_payload: dict[str, Any]) -> AnnullaLottoDaDraftResult:
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
        def _handler(_payload: dict[str, Any]) -> dict[str, Any]:
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
        def _handler(_payload: dict[str, Any]) -> EliminaFatturaDaLottoResult:
            result = fn_elimina_fattura_da_lotto(lotto_id=lotto_id, fattura_id=fattura_id)
            return result

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)




class ApiEscludiDocumentiDaGiro(DomainAPIView):
    """Toglie N documenti dal giro, cosi' che il lotto riparta con gli altri.

    ⭐ Un giro prende in carico N documenti; se uno e' rotto il lotto si ferma e
    gli altri N-1, che hanno gia' le loro bozze, non vengono emessi. Prima
    l'unica azione su un lotto fermo era ANNULLARLO — buttare via il giro
    intero, bozze sane comprese.

    ⚠️ **Il consuntivo va mostrato, non ingoiato.** Una bozza puo' coprire piu'
    documenti: togliere A puo' portare via anche B, che torna «da emettere» e si
    fattura al giro dopo. `gruppi_riaperti` porta le CHIAVI proprio perche' la
    conferma deve poterli nominare (D-2b del brief).

    ⛔ Nessuna regola qui: il verdetto e' della funzione MADRE, che chiama
    `script.fn_check_documento_escludibile_da_giro` — la stessa da cui la lista
    documenti prende il motivo del pulsante spento. Un rifiuto arriva come 409
    con il codice del PRIMO motivo.

    ⚠️ **Permesso RIUSATO e non coniato**: `reset_lotto_fattura_draft`. Il potere
    e' lo stesso — cancellare bozze pre-fiscali di un lotto, una alla volta — e
    questo verbo quella primitiva la COMPONE. Un codename nuovo sarebbe un seed
    a catalogo (`config.azioni_processo`) per dire che e' un'altra facolta',
    e non lo e'.
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
            name="VenditeEscludiDocumentiDaGiroRequest",
            fields={
                # ⭐ Una LISTA anche per un documento solo: un endpoint solo, e
                #    la riga singola è una lista di uno. Due superfici per lo
                #    stesso verbo divergerebbero su permessi, conferme e forma
                #    dell'esito.
                "gruppo_keys": serializers.ListField(child=serializers.CharField()),
                # ⚠️ Obbligatorio, e la regola la tiene il database (D-5): un
                #    documento che esce senza motivo e' una riga che fra un mese
                #    nessuno sa spiegare.
                # ⚠️ UNO per il giro, non uno per riga: chi toglie cinque
                #    documenti li toglie per la stessa ragione, e chiederne
                #    cinque renderebbe il gesto di massa più lento della somma
                #    dei singoli.
                "motivo": serializers.CharField(),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeEscludiDocumentiDaGiroResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeEscludiDocumentiDaGiroData",
                        fields={
                            # ⭐ Un REPORT a tre stati, e torna 200 anche quando
                            #    falliscono tutti: il verbo non produce un atto
                            #    fiscale, lascia documenti che tornano in
                            #    competenza. Sollevare sul «tutti falliti»
                            #    darebbe due forme da leggere per la stessa
                            #    domanda.
                            "esito": serializers.CharField(),
                            "totale": serializers.IntegerField(),
                            "ok": serializers.IntegerField(),
                            "usciti": serializers.ListField(
                                child=serializers.DictField(),
                            ),
                            # ⚠️ Il CODICE per riga, non solo la frase: è ciò su
                            #    cui il frontend instrada — «già uscito» si legge
                            #    diverso da «non è in errore».
                            "falliti": serializers.ListField(
                                child=serializers.DictField(),
                            ),
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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            # ⛔ NESSUNA NORMALIZZAZIONE, e nemmeno un `str()` di comodo: il
            #    `CHECK` di tabella rifiuta anche i soli spazi, e sistemarlo qui
            #    trasformerebbe un rifiuto in un motivo vuoto scritto. Il TIPO
            #    lo controlla il service; il CONTENUTO e' del database (D-5).
            return fn_escludi_documenti_da_giro(
                lotto_id=lotto_id,
                gruppo_keys=payload.get("gruppo_keys"),
                motivo=payload.get("motivo"),
            )

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
        # `nullable`: la direzione assente resta assente, e la decide il BB
        # della lista (date DESC). Fino al 2026-10-20 qui si scriveva
        # `order_dir or "asc"`, e la regola non arrivava al repository (§6.1).
        order_by, order_dir = validate_order_params(
            order_by,
            order_dir,
            allowed_columns=_ORDER_BY_LOTTI,
            error_code="E_SEARCH_VALIDATION",
            function_name=function_name,
            nullable=True,
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
        # ⭐ Il perimetro della scheda «Recuperi del mese» sta QUI, insieme agli
        #    altri filtri, e non piu' solo nella view della lista.
        # 🔴 Difetto corretto il 2026-09-03: l'export lo riceveva dal frontend
        #    (`recuperi_mese: true`, con tanto di commento «il file E' la lista»)
        #    e NESSUNO lo leggeva — questa funzione non lo estraeva e
        #    `fn_export_lotti` non aveva il parametro. Esportando dalla seconda
        #    scheda usciva l'elenco ORDINARIO del mese: non un file incompleto,
        #    un insieme DISGIUNTO da quello a video. Niente falliva.
        # ⚠️ E' la specie «campo dichiarato e non letto»: sembrava presidiato
        #    perche' il parametro partiva davvero.
        "solo_recuperi_mese": qp_bool_optional(qp.get("recuperi_mese"), "recuperi_mese", default=False),
        # ⭐ `?annullati=1` mostra anche i lotti col fiscale ABORTITO (2026-09-12).
        #    Di default restano fuori — da lista, chip ed export insieme, perche'
        #    il parser e' uno — e la risposta dice quanti sono (`annullati_count`).
        "includi_annullati": qp_bool_optional(qp.get("annullati"), "annullati", default=False),
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
            OpenApiParameter(name="annullati", type=bool, location=OpenApiParameter.QUERY, required=False, description="`1` mostra anche i lotti col fiscale ABORTITO (`config.stati_doc_fiscale.is_abortito`, oggi ANNULLATA). Default: nascosti — lista, chip per stato ed export insieme — e la risposta dichiara quanti sono in `annullati_count`."),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False, description="Colonna di ordinamento: `campo_sorgente` del catalogo lista `vendite.lotti`. Whitelist autoritativa: `VenditeRepository.LOTTI_SORT_COLUMNS` — codice, competenza_mese, data_documento, tipo_lotto, tipo_doc_fiscale_descrizione, utility_descrizione, area_geografica_descrizione, emittente_ragione_sociale, stato_lotto, stato_operativo, stato_doc_fiscale_descrizione, n_fatture, totale_documenti, data_insert, user_insert."),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False, description="Direzione ordinamento: asc | desc (default asc)."),
            *parametri_finestra(),
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
                            # Ripartizione per stato del perimetro corrente
                            # (mese/recuperi compresi, filtro `stato_lotto`
                            # ESCLUSO): alimenta i pulsanti-filtro della lista.
                            # Solo gli stati presenti — uno stato a zero non
                            # diventa un pulsante.
                            "stati": serializers.ListField(child=serializers.DictField()),
                            # Quanti lotti annullati il perimetro sta NASCONDENDO
                            # (0 con `?annullati=1`): il numero accanto
                            # all'interruttore che li mostra.
                            "annullati_count": serializers.IntegerField(),
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

        # La finestra dal BB: dal 2026-10-21 un dialetto solo, `limit`/`offset`.
        limit, offset = pagina_da_query(request.query_params)

        data = fn_list_lotti(
            **filtri,
            auth_user_id=get_scope_user_id(request),
            limit=limit,
            offset=offset,
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
            OpenApiParameter(name="annullati", type=bool, required=False, description="`1` esporta anche i lotti annullati (stesso interruttore della lista)."),
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
                # ⭐ Dichiarato nell'intestazione del file solo quando e' vero:
                #    due export dello stesso mese con perimetri disgiunti
                #    sarebbero altrimenti indistinguibili aprendoli.
                (
                    "recuperi_mese",
                    True if filtri["solo_recuperi_mese"] else None,
                ),
                # Stessa ragione: un file con gli annullati dentro e uno senza
                # sono due perimetri, e aprendoli devono dirlo.
                ("annullati", True if filtri["includi_annullati"] else None),
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
    stato: il badge conta i lotti generati, non quelli dello stato filtrato).
    ⭐ Ma SENZA gli annullati, come la lista (2026-09-12): un guscio non e' un
    lotto generato che chieda lavoro — `?annullati=1` li rimette dentro."""

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
            OpenApiParameter(
                name="annullati",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description="`1` conta anche i lotti annullati (stesso interruttore della lista).",
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
        anno = qp_int_strict(request.query_params.get("anno"), "anno", oggi_aziendale().year)
        auth_user_id = get_scope_user_id(request)
        data = fn_lotti_mensile(
            anno=anno,
            auth_user_id=auth_user_id,
            includi_annullati=qp_bool_optional(request.query_params.get("annullati"), "annullati", default=False),
        )
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
                            # Segnale di un giro solo: il prossimo run RIFA' lo
                            # step corrente invece di avanzare (vedi types.py).
                            "riaperto": serializers.BooleanField(),
                            # Blob capability (script.fn_available_actions_lotto),
                            # SOTTO la sua chiave (api.md §«Il blob sta SOTTO
                            # `capabilities`»): `available_actions`,
                            # `can_change_state`, `stato_codice`, `tipo_lotto`.
                            # Vuoto se il capability layer e' rotto (fallback
                            # graceful nel service), mai assente.
                            "capabilities": serializers.DictField(),
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


class ApiLottoFattureExport(DomainAPIView):
    """GET /api/v1/vendite/lotti/<id>/fatture/export/?formato=csv|xlsx

    I documenti del lotto (fatture E note di credito), colonne dal catalogo
    `vendite.lotto_fatture`: nascoste escluse, ordine e permessi rispettati."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "fattura")
    is_search_endpoint = True
    lista_codice = "vendite.lotto_fatture"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="stato_esecuzione", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={(200, "text/csv"): bytes},
    )
    # Scopo: file CSV/XLSX dei documenti del lotto.
    def get(self, request: Request, lotto_id: int) -> HttpResponse:
        fmt = parse_export_format(request)
        q = request.query_params
        stato = q.get("stato_esecuzione") or None
        data = fn_list_lotto_fatture(
            lotto_id=lotto_id,
            stato_esecuzione=stato,
            auth_user_id=get_scope_user_id(request),
            order_by=qp_str(q.get("order_by")),
            order_dir=qp_str(q.get("order_dir")),
            max_rows=EXPORT_MAX_ROWS + 1,
        )
        return build_export_response(
            request,
            lista_codice="vendite.lotto_fatture",
            results=data["results"],
            total=data["count"],
            filtri_applicati={
                "lotto_id": str(lotto_id),
                **({"stato_esecuzione": stato} if stato else {}),
            },
            fmt=fmt,
        )


class ApiLottoFattureList(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "fattura")
    # Lista configurabile 45: il codice dichiara da quale catalogo arrivano le colonne (e per chi ha piu' emittenti, da quale perimetro le righe).
    lista_codice = "vendite.lotto_fatture"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato_esecuzione", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato esecuzione fattura."),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False, description="Colonna di ordinamento (default fattura_id). Fino al 2026-10-20 si chiamava `sort_by`."),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False, description="Direzione ordinamento: asc/desc (assente: la decide la lista, date DESC). Fino al 2026-10-20 si chiamava `sort_dir`."),
            *parametri_finestra(),
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

        # ⛔ `order_by`/`order_dir` come ogni altra lista (decisione Tid
        #    2026-10-20, brief-be-verifica-documentazione-api §A4): fino a quel
        #    giorno questa sola si ordinava con `sort_by`/`sort_dir`. Assenti
        #    restano assenti: colonna e verso li decide la lista (§6.1).
        order_by = qp_str(request.query_params.get("order_by"))
        order_dir = qp_str(request.query_params.get("order_dir"))
        limit, offset = pagina_da_query(request.query_params)

        auth_user_id = get_scope_user_id(request)

        data = fn_list_lotto_fatture(
            lotto_id=lotto_id,
            stato_esecuzione=stato_esecuzione,
            auth_user_id=auth_user_id,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiLottoGruppiList(DomainAPIView):
    """GET /api/v1/vendite/lotti/<id>/gruppi/

    I DOCUMENTI che il lotto ha preso in carico, con l'esito di ciascuno.

    ⭐ Non e' un doppione di `/fatture/`, ed e' la ragione per cui esiste
    (brief-db-esito-gruppo-lotto). Quella lista si aggancia a `fattura_id`:
    descrive i documenti che una fattura l'hanno prodotta. Un documento che
    cade PRIMA — al pull delle attivita' dalla commessa — non ha nessuna
    fattura a cui appendersi e finora spariva dal racconto: sul lotto
    LTF-0009578 se ne vedevano due su tre, e il terzo era nominato solo da una
    segnalazione, per giunta con l'identificativo della COMMESSA.

    ⚠️ Le due liste NON sono in corrispondenza 1:1 nemmeno quando tutto va
    bene: `fn_build_fattura_key` puo' raccogliere piu' gruppi nello stesso
    documento. Sono due domande diverse, non due viste della stessa.

    ⭐ La riga e' l'UNIONE di due fatti (rev DB 2026-09-07): il PERIMETRO
    (`fatturazione_lotti_gruppi`, che dichiarano i soli giri mirati) e l'ESITO
    (`fatturazione_lotti_esiti`, che c'e' su entrambi i tipi di giro). Nessuno
    dei due da solo risponde: il primo lascia muti i giri di massa, il secondo
    perde i documenti dichiarati e non ancora tentati.

    🔒 Il cancello di scope e' la TESTATA: le due tabelle figlie non hanno RLS,
    `vendite.fatturazione_lotti` si'. Lotto fuori perimetro o inesistente ->
    404 (BB `lotto_visibile`, dal 2026-10-20: prima elenco vuoto), mai le
    righe di un lotto altrui.
    """

    area_funzionale = "vendite"
    # Lista configurabile 67: il codice dichiara da quale catalogo arrivano le colonne.
    lista_codice = "vendite.lotto_gruppi"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="stato_esecuzione", type=str, location=OpenApiParameter.QUERY, required=False,
                description=(
                    "Filtro esito: PENDING | RUNNING | COMPLETED | ERRORE. "
                    "Assente = tutti, compresi i gruppi mai tentati (esito NULL)."
                ),
            ),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False,
                description="Verso: asc (default) o desc.",
            ),
            *parametri_finestra(),
        ],
        responses={
            200: inline_serializer(
                name="VenditeLottoGruppiListResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeLottoGruppiListData",
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
    # Scopo: Restituisce via GET l'elenco paginato dei documenti presi in carico
    #        dal lotto, con l'esito di ciascuno.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        q = request.query_params
        limit, offset = pagina_da_query(q)
        data = fn_list_lotto_gruppi(
            lotto_id=lotto_id,
            auth_user_id=get_scope_user_id(request),
            stato_esecuzione=qp_str(q.get("stato_esecuzione")),
            order_by=qp_str(q.get("order_by")),
            # ⚠️ Il valore GREZZO, non un default `"asc"` scritto qui: il
            #    repository ha un ordine di default suo — i falliti in cima —
            #    e un verso dichiarato lo annullerebbe (api.md §parse_list_params).
            order_dir=qp_str(q.get("order_dir")),
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiLottoGruppiExport(DomainAPIView):
    """GET /api/v1/vendite/lotti/<id>/gruppi/export/?formato=csv|xlsx

    I documenti presi in carico dal lotto, colonne dal catalogo
    `vendite.lotto_gruppi`."""

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.lotto_gruppi"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="stato_esecuzione", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={(200, "text/csv"): bytes},
    )
    # Scopo: file CSV/XLSX dei documenti presi in carico dal lotto.
    # ⚠️ Il filtro viaggia anche qui: il file E' la lista. Un export che
    #    ignorasse l'esito scelto conterrebbe tutti i documenti mentre a video
    #    se ne vede una fetta.
    def get(self, request: Request, lotto_id: int) -> HttpResponse:
        fmt = parse_export_format(request)
        q = request.query_params
        stato_esecuzione = qp_str(q.get("stato_esecuzione"))
        data = fn_list_lotto_gruppi(
            lotto_id=lotto_id,
            auth_user_id=get_scope_user_id(request),
            stato_esecuzione=stato_esecuzione,
            order_by=qp_str(q.get("order_by")),
            order_dir=qp_str(q.get("order_dir")),
            max_rows=EXPORT_MAX_ROWS + 1,
        )
        # I filtri finiscono nell'intestazione del file: chi lo riapre fra un
        # mese deve poter sapere di quale fetta si tratta.
        filtri_applicati: dict[str, str] = {"lotto_id": str(lotto_id)}
        if stato_esecuzione:
            filtri_applicati["stato_esecuzione"] = stato_esecuzione
        return build_export_response(
            request,
            lista_codice="vendite.lotto_gruppi",
            results=data["results"],
            total=data["count"],
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )




# ================================================================== #
# Commesse — push orchestrator + stato + attivita                     #
# ================================================================== #



# I filtri del giornale trasversale, dichiarati UNA volta per la lista e per
# il suo export.
_PARAMS_FILTRI_GIORNALE = [
    OpenApiParameter(
        name="gravita", type=str, location=OpenApiParameter.QUERY, required=False,
        description=(
            f"Gravita' (csv) fra {' | '.join(GIORNALE_GRAVITA)}; default `ERROR`. "
            "⚠️ Con `ERROR` si INCLUDE la gravita' NULL — la riga che dichiara "
            "un difetto. Fuori vocabolario -> 400."
        ),
    ),
    OpenApiParameter(
        name="registro", type=str, location=OpenApiParameter.QUERY, required=False,
        description=(
            "Registro (csv): `codice_interno` di `config.registri_giornale` — il "
            "catalogo che il lookup generico serve con `rel=config.registri_giornale` "
            "(EVENT_LOG, LOTTO_LOG, TASK_RUN, FATTURA_LOG al 2026-09-19); default "
            "tutti. Fuori catalogo -> 400."
        ),
    ),
    OpenApiParameter(
        name="entity_type", type=str, location=OpenApiParameter.QUERY, required=False,
        description="Codice di `config.tipi_entita` (LOTTO, FATTURA, COMMESSA, TASK_RUN, ...), esatto.",
    ),
    OpenApiParameter(name="data_da", type=str, location=OpenApiParameter.QUERY, required=False,
                     description="Data inizio (YYYY-MM-DD) su `quando`."),
    OpenApiParameter(name="data_a", type=str, location=OpenApiParameter.QUERY, required=False,
                     description="Data fine inclusa (YYYY-MM-DD) su `quando`."),
    OpenApiParameter(
        name="filo", type=str, location=OpenApiParameter.QUERY, required=False,
        description=(
            "UUID del FILO: `tx_id` oppure `correlation_id`. Tiene `EVENT_LOG` e "
            "`TASK_RUN` e butta le righe scritte per una persona (R-2): il "
            "default non filtra per filo."
        ),
    ),
    OpenApiParameter(
        name="solo_vive", type=bool, location=OpenApiParameter.QUERY, required=False,
        description="Default true: esclude le segnalazioni RITIRATE; `ritirate_count` dice quante.",
    ),
    OpenApiParameter(
        name="order_by", type=str, location=OpenApiParameter.QUERY, required=False,
        description=descrizione_order_by(
            GIORNALE_SORT_COLUMNS,
            "Default `quando DESC`; `gravita` ordina il rango e, dentro, il tempo dal piu' recente.",
        ),
    ),
    OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False,
                     description="asc | desc."),
]


# Scopo: i filtri del giornale trasversale dalla query string, normalizzati:
#        csv -> liste, date ISO strict (400 se malformate), `filo` uuid (400 se
#        non lo e'), `solo_vive` bool. Una sede per la lista e per l'export.
def _filtri_giornale(qp) -> dict[str, Any]:
    def _csv(raw: str | None) -> list[str] | None:
        valori = [v.strip().upper() for v in (raw or "").split(",") if v.strip()]
        return valori or None

    filo = optional_uuid({"filo": qp_str(qp.get("filo"))}, "filo")
    return {
        "gravita": _csv(qp.get("gravita")),
        "registri": _csv(qp.get("registro")),
        "entity_type": qp_str_upper(qp.get("entity_type")),
        "data_da": qp_iso_date_optional(qp.get("data_da"), "data_da"),
        "data_a": qp_iso_date_optional(qp.get("data_a"), "data_a"),
        "filo": str(filo) if filo is not None else None,
        # ⛔ Strict, come ogni bool opzionale dal 2026-06-04 (api.md §Query
        #    params): `?solo_vive=banana` e' un 400, non un `True` per caso.
        #    Assente = `True` (le ritirate si nascondono di default).
        "solo_vive": qp_bool_optional(qp.get("solo_vive"), "solo_vive") is not False,
    }


class ApiGiornale(DomainAPIView):
    """GET /api/v1/vendite/giornale/ — il GIORNALE TRASVERSALE degli eventi.

    «Cosa e' andato storto, su tutto, nell'ultimo periodo»: la Storia di tutte
    le entita' insieme, filtrata per gravita' — la «vista errori trasversale,
    con salto al lotto e al documento» del Passo B dell'osservabilita' (pezzo
    G, 2026-09-19). Terzo lettore di `script.vw_giornale_entita`, sullo STESSO
    corpo dei due lettori per entita': non un aggregato nuovo.

    ⛔ Niente `context`/`payload`: espone le colonne della Storia e basta. Gli
    appunti forensi restano nella Storia dell'entita' (vincolo del Passo A).
    ⚠️ Il perimetro emittente lo applica la vista (`security_invoker`) riga per
    riga e nei conteggi; la lista sta dietro il cancello di perimetro
    (`lista_codice`), come ogni lista di dominio.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.giornale"

    @extend_schema(
        parameters=[
            *_PARAMS_FILTRI_GIORNALE,
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: inline_serializer(
                name="VenditeGiornaleResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeGiornaleData",
                        fields={
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "ritirate_count": serializers.IntegerField(),
                            "results": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il giornale trasversale, paginato.
    # ⭐ `order_dir` assente = `None`: decide il default `quando DESC`.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order=GIORNALE_ORDINE_DEFAULT)
        return success_response(get_giornale_trasversale(
            **_filtri_giornale(qp),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        ))


class ApiGiornaleExport(DomainAPIView):
    """GET /api/v1/vendite/giornale/export/ — CSV/XLSX del giornale trasversale."""

    area_funzionale = "vendite"
    # ⭐ LO STESSO `lista_codice` della lista, letto da lei: colonne del file =
    #    colonne a video, e il cancello di perimetro vale anche sulla porta
    #    larga (`test_export_lista_codice_pari`).
    lista_codice = ApiGiornale.lista_codice

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, location=OpenApiParameter.QUERY,
                             required=True, description="csv | xlsx."),
            *_PARAMS_FILTRI_GIORNALE,
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Il file del giornale, con gli stessi filtri della lista.
    # ⚠️ `limit=EXPORT_MAX_ROWS + 1`: l'export esporta il DATASET, e il `+1`
    #    fa scattare il guard di `build_export_response` prima di serializzare.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        filtri = _filtri_giornale(qp)
        dati = get_giornale_trasversale(
            **filtri,
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
        )
        return build_export_response(
            request,
            lista_codice=self.lista_codice,
            results=dati["results"],
            total=dati["count"],
            filtri_applicati={
                k: (v.isoformat() if isinstance(v, date) else v)
                for k, v in filtri.items() if v is not None
            } or None,
            fmt=fmt,
        )


class ApiLottoGiornale(DomainAPIView):
    """La STORIA di un lotto: il lotto PIU' le sue fatture, di default senza INFO.

    Secondo consumatore di `script.vw_giornale_entita`, la vista che cuce i
    registri di evento del progetto in una forma normalizzata. Sul lotto i
    registri che rispondono sono **tre** — `EVENT_LOG`, `LOTTO_LOG`,
    `TASK_RUN` — piu' `FATTURA_LOG` per i documenti che contiene.

    ⭐ «Il lotto piu' le sue fatture» e' una DECISIONE (Tid, 2026-08-24), non una
    scelta di schermata: un pannello limitato all'entita' LOTTO ripeterebbe
    «Esito fatture lotto · WARN» e **non conterrebbe il motivo**, che sta sulla
    fattura perche' la sua entita' e' la fattura (rilievo R-3). Per la stessa
    ragione le colonne Entita'/Riferimento della lista servono: la Storia del
    lotto mescola due entita'.

    ⭐ Dal 2026-09-27 e' la lista a catalogo `vendite.giornale` (la stessa del
    trasversale e della Storia della fattura): contratto di lista standard
    (`_giornale_params`), piu' il filtro che e' solo suo, `info`.

    ⛔ Non e' la lista delle segnalazioni (`/segnalazioni/`), che elenca i
    problemi APERTI da risolvere: qui si risponde a *«cosa e' successo, in che
    ordine»* — comprese le cose andate bene e i tentativi superati.

    Lotto inesistente **o fuori scope emittente** → 404 identico. ⚠️ E il 404 lo
    decide la TESTATA: la vista risponderebbe zero righe, cioe' «non e' successo
    niente» invece di «non lo vedi».
    """

    area_funzionale = "vendite"
    lista_codice = "vendite.giornale"
    lista_emittente_param = EMITTENTE_PARAM_GIORNALE_ENTITA

    @extend_schema(
        parameters=[
            *PARAMS_LISTA_GIORNALE_ENTITA,
            OpenApiParameter(
                name="info", type=bool, location=OpenApiParameter.QUERY, required=False,
                description=(
                    "Include anche le righe di routine (`INFO`), di default "
                    "nascoste. Quante ne sono state nascoste lo dice "
                    "`info_count`. ⚠️ «Non-INFO» comprende la gravita' NULL, che "
                    "e' il segnale di un vincolo allargato e non un dato "
                    "mancante: resta visibile anche col filtro attivo."
                ),
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeLottoGiornaleResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeLottoGiornaleData",
                        fields={
                            "lotto_id": serializers.IntegerField(),
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "ritirate_count": serializers.IntegerField(),
                            "info_count": serializers.IntegerField(),
                            "results": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il giornale paginato del lotto.
    # ⚠️ `info` strict (`qp_bool_optional`): `?info=banana` e' un 400. Assente
    #    = `False`, cioe' «solo problemi» — il default della scheda.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        q = request.query_params
        data = get_lotto_giornale(
            lotto_id=lotto_id,
            **parametri_lista_giornale_entita(q),
            includi_info=qp_bool_optional(q.get("info"), "info") is True,
            auth_user_id=get_scope_user_id(request),
        )
        return success_response(data)

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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
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

        # ⭐ A_PASSI (brief-be-verifica-documentazione-api §I.7.2): il registro del giro (`commesse_push_log`) e l'`except` sull'handler senza savepoint.
        #    Una key orfana non si riprende, e niente `atomic` esterno.
        return handle_post_json(
            request, handler=_handler, require_idempotency_key=True,
            unita_di_lavoro=UnitaDiLavoro.A_PASSI,
        )




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
    # L'azione del passaggio (stato corrente -> `nuovo_stato`) dalla riga della
    # matrice (M-3, brief-modello-documento-vendita §14.6 punto 2): «rendi
    # pronta», «riapri», «chiudi» e l'annullo di una commessa non in bozza
    # chiedono `cambia_stato_commessa`; l'annullo della bozza il solo livello
    # sul documento (C-1, M-4). Prima un `post_permission` su ogni passaggio.
    # NB: il GET di lettura stato resta libero nell'area.
    post_passaggio = PassaggioDocumento(
        testata=TESTATA_COMMESSE, documento_kwarg="commessa_id", campo_stato="nuovo_stato",
    )
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
            fields={
                "nuovo_stato": serializers.CharField(),
                # Solo verso ANNULLATA, alla conferma: quanti legami
                # l'operatore ha visto (`GET .../legami/`).
                "legami_confermati": serializers.IntegerField(required=False),
            },
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
    # Scopo: Azione di stato utente (rendi pronta/riapri/chiudi/annulla) sulla
    #        commessa. L'annullo con righe NON_EMESSA si conferma: la seconda
    #        richiesta porta `legami_confermati` (brief-db-annullo-a-valle-
    #        riapre-a-monte).
    def post(self, request: Request, commessa_id: int) -> JsonResponse:
        # Scopo: applica la transizione richiesta dal verbo del DB.
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return cambia_stato_commessa(
                commessa_id=commessa_id,
                nuovo_stato=payload.get("nuovo_stato"),
                legami_confermati=payload.get("legami_confermati"),
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiCommessaDetail(DomainAPIView):
    """PATCH /api/v1/vendite/commesse/<id>/ — la testata leggibile.

    `descrizione` e `responsabile_risorsa_umana_id` (Blocco C di
    brief-db-modifiche-certe-ciclo-vendita-e-articolo); `data_apertura` e' in
    sola lettura e viaggia nel dettaglio. ⚠️ Il DETTAGLIO resta su `/stato/`
    (`ApiCommessaStato.get`), che e' la rotta storica del drawer e porta gia'
    anche questi tre campi: qui c'e' il solo verbo di scrittura, sulla risorsa
    come vuole la grammatica URL (PATCH /{risorsa}/{id}/). Permesso = livello
    d'area `vendite` (`change`), come le testate degli altri documenti.
    """

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="VenditeCommessaTestataRequest",
            fields={
                "descrizione": serializers.CharField(
                    required=False, allow_null=True, max_length=255,
                ),
                "responsabile_risorsa_umana_id": serializers.IntegerField(
                    required=False, allow_null=True,
                    help_text="Risorsa umana ATTIVA; null toglie il responsabile.",
                ),
            },
        ),
        responses={200: inline_serializer(
            name="VenditeCommessaTestataResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Aggiorna via PATCH la testata leggibile e risponde col dettaglio
    #        aggiornato (lo stesso payload di `/stato/`).
    def patch(self, request: Request, commessa_id: int) -> JsonResponse:
        return success_response(aggiorna_commessa_testata(commessa_id, corpo_oggetto(request)))


class ApiCommessaRegistro(DomainAPIView):
    """GET /api/v1/vendite/commesse/<id>/registro/ — il registro delle righe.

    Gli eventi che il database scrive su `vendite.commesse_attivita_log`: oneri
    aggiunti, righe annullate a mano, ritirate alla chiusura del documento di
    origine, riportate da emettere, accrediti. Risponde a «perche' questa riga
    e' cosi'» — chi, quando, con quale motivo.

    ⛔ Lo scope sta sulla RIGA DI COMMESSA, non sul log: quella tabella non ha
    row level security, `vendite.commesse_attivita` si'. Il repository legge
    passando dal `JOIN`, che e' il cancello — leggere il log da solo mostrerebbe
    i motivi di commesse fuori perimetro.

    ⚠️ Il vocabolario degli eventi e' del database ed e' aperto: qui non se ne
    nomina nessuno e non si filtra, cosi' un evento nuovo compare da se'.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="commessa_attivita_id", type=int, location=OpenApiParameter.QUERY,
                required=False,
                description="Restringe a una riga sola (il caso d'uso del kebab di riga). "
                            "Assente = tutti gli eventi della commessa.",
            ),
            OpenApiParameter(
                name="limit", type=int, location=OpenApiParameter.QUERY, required=False,
                description=f"Eventi per pagina (default {DEFAULT_LIMIT_EVENTI}, max {MAX_LIMIT}).",
            ),
            OpenApiParameter(
                name="offset", type=int, location=OpenApiParameter.QUERY, required=False,
                description="Offset paginazione (default 0).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeCommessaRegistroResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeCommessaRegistroData",
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
    # Scopo: Restituisce via GET il registro paginato di una commessa.
    def get(self, request: Request, commessa_id: int) -> JsonResponse:
        qp = request.query_params
        limit, offset = pagina_da_query(qp, default_limit=DEFAULT_LIMIT_EVENTI)
        return success_response(
            fn_commessa_registro(
                commessa_id=commessa_id,
                commessa_attivita_id=optional_int(
                    {"v": qp.get("commessa_attivita_id")}, "v",
                ),
                limit=limit,
                offset=offset,
            )
        )


class ApiCommessaAttivita(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.commesse_attivita"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato_emissione", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato emissione (es. NON_EMESSA, EMESSA)."),
            OpenApiParameter(name="stato_approvazione", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro stato approvazione (es. BOZZA, APPROVATA)."),
            OpenApiParameter(name="competenza_mese", type=str, location=OpenApiParameter.QUERY, required=False, description="Filtro mese di competenza (YYYY-MM-DD)."),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False, description=f"Righe per pagina (default {DEFAULT_LIMIT}, max {MAX_LIMIT})."),
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
                            "results": serializers.ListField(child=serializers.DictField()),
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
        limit, offset = pagina_da_query(request.query_params)
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

        filtri: dict[str, Any] = {
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
            results=data["results"],
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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
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
        request=inline_serializer(
            name="VenditeNumeraLottoRequest",
            fields={
                "data_documento": serializers.DateField(
                    required=False,
                    allow_null=True,
                    help_text=(
                        "Data documento dichiarata per l'atto: riscrive la data "
                        "delle fatture non ancora numerate del lotto e ne "
                        "rigenera i piani rate, PRIMA di numerare. Assente = "
                        "nessuna dichiarazione, valgono le date che i documenti "
                        "gia' portano. La data minima ammessa e' quella esposta "
                        "dalla finestra di numerazione del perimetro."
                    ),
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeNumeraLottoResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeNumeraLottoData",
                        fields=_esito_runner_fields(),
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Numera (Rendi definitive) il lotto: guard scope+EMESSA, dichiarazione
    #        opzionale della data documento, poi step DEFINITIVA.
    def post(self, request: Request, lotto_id: int) -> JsonResponse:
        # Scopo: delega al service (guard fiscale + data + esecuzione step DEFINITIVA).
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return numera_lotto(
                lotto_id=int(lotto_id),
                auth_user_id=get_scope_user_id(request),
                data_documento=optional_iso_date(payload, "data_documento"),
            )

        # ⭐ A_PASSI (brief-be-verifica-documentazione-api §I.7.2): `numera_lotto` committa per passi: non si avvolge in un atomic (pipeline_service).
        #    Una key orfana non si riprende, e niente `atomic` esterno.
        return handle_post_json(
            request, handler=_handler, require_idempotency_key=True,
            unita_di_lavoro=UnitaDiLavoro.A_PASSI,
        )


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
        def _handler(_payload: dict[str, Any]) -> dict[str, Any]:
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


class ApiFatturazioneFinestraNumerazione(DomainAPIView):
    """BE-5: la FINESTRA DI NUMERAZIONE di un perimetro — con quale data si
    puo' numerare, e da quale data i documenti partono adesso. E' la TARGA del
    cancello di
    `vendite.fn_get_next_progressivo`, che rifiuta un documento la cui data e'
    anteriore all'ultimo numero gia' emesso sul sezionale.

    Due perimetri, una domanda sola: `?lotto_id=` (dialog «Rendi definitive»
    del drawer lotto) oppure `?competenza_mese=` (atto di perimetro, che tocca
    N lotti e vuole la data che li accontenta tutti). Esattamente uno dei due.

    `data_minima` a `null` = nessun pavimento: su quei sezionali non e' ancora
    stato emesso nessun numero, e qualunque data va bene.

    ⚠️ E' un SUGGERIMENTO per il DatePicker, non una garanzia: la lettura e'
    fail-open sotto RLS (una fattura fuori perimetro non entra nel massimo).
    Il rifiuto vero resta del cancello, che legge il contatore."""

    area_funzionale = "vendite"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="lotto_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Perimetro «un lotto». Alternativo a competenza_mese.",
            ),
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Perimetro «atto sul mese» (YYYY-MM-DD): il pavimento piu' "
                    "restrittivo fra i lotti EMESSA di quel mese."
                ),
            ),
            OpenApiParameter(
                name="lotti",
                type=int,
                many=True,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Perimetro «selezione» — parametro RIPETUTO "
                    "(`?lotti=12&lotti=15`): il pavimento piu' restrittivo fra i "
                    "lotti indicati. Serve al dialog per ricalcolare il limite "
                    "mentre l'operatore spunta, perche' il pavimento e' di ogni "
                    "SEZIONALE e un lotto di un altro registro puo' spostarlo in "
                    "avanti."
                ),
            ),
        ],
        # ⛔ I tre perimetri sono ALTERNATIVI, esattamente uno: senza perimetro
        #    la domanda non ha risposta, con due ne avrebbe due e non si saprebbe
        #    quale si e' ottenuta. Fuori dai tre -> 400.
        responses={
            200: inline_serializer(
                name="VenditeFinestraNumerazioneResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFinestraNumerazioneData",
                        fields={
                            "lotto_id": serializers.IntegerField(allow_null=True),
                            "competenza_mese": serializers.CharField(allow_null=True),
                            "n_lotti": serializers.IntegerField(allow_null=True),
                            "data_documento": serializers.CharField(allow_null=True),
                            "data_corrente": serializers.CharField(allow_null=True),
                            "data_minima": serializers.CharField(allow_null=True),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce la data minima numerabile del perimetro richiesto.
    def get(self, request: Request) -> JsonResponse:
        # ⚠️ `qp_int_optional` e non un guard sul positivo qui: uno zero o un
        #    negativo non e' un parametro malformato, e' un lotto che non
        #    esiste — e la risposta giusta e' il 404 unificato del service, non
        #    un 400 che dice una cosa diversa dagli altri verbi per-lotto.
        lotto_id = qp_int_optional(request.query_params.get("lotto_id"), "lotto_id")
        competenza_mese = qp_iso_date_optional(
            request.query_params.get("competenza_mese"), "competenza_mese",
        )
        # ⭐ Il terzo perimetro: la SELEZIONE della lista lotti, ripetuta
        #    (`?lotti=12&lotti=15`). Serve al dialog per ricalcolare il limite
        #    MENTRE si spunta — il pavimento e' di ogni sezionale, e aggiungere
        #    un lotto di un altro registro puo' spostarlo in avanti.
        # ⚠️ `getlist` e non `get`: con `get` arriverebbe il solo ULTIMO valore,
        #    e il limite verrebbe calcolato su un lotto invece che su tutti —
        #    piu' basso del vero, cioe' una data che il DB poi rifiuta.
        lotti_ids = _query_lotti_ids(request)
        return success_response(
            finestra_numerazione(
                lotto_id=lotto_id,
                competenza_mese=competenza_mese,
                lotti_ids=lotti_ids,
                auth_user_id=get_scope_user_id(request),
            ),
        )


# Scopo: gli id dei lotti dalla query string (`?lotti=12&lotti=15`), validati.
# ⚠️ Il parametro ASSENTE e la lista VUOTA sono due cose diverse: assente = «non
#    sto chiedendo per selezione» (None), mentre una lista vuota qui non e'
#    rappresentabile — `getlist` la restituisce vuota anche quando il parametro
#    non c'e'. Per questo il ripiego e' `None`: e' l'unica forma che il servizio
#    interpreta come «perimetro non richiesto».
# ⛔ E LA REGOLA SUGLI ID E' LA STESSA DELLA POST (`parse_lotti`), non una
#    seconda scritta qui. Quando erano due, divergevano: la POST rifiutava
#    `lotti=[0]` mentre la GET lo accettava e rispondeva `data_minima: null` —
#    cioe' «niente da numerare», un errore di chiamante travestito da dato
#    tranquillo. Misurato il 2026-08-26 su `?lotti=0` e `?lotti=-3`.
# ⚠️ Prima si converte (un non-numero e' un errore di FORMA, `lotti_invalid`),
#    poi si valida il dominio (un id <= 0 e' un errore di VALORE): due errori
#    diversi meritano due messaggi diversi.
def _query_lotti_ids(request: Request) -> list[int] | None:
    grezzi = request.query_params.getlist("lotti")
    if not grezzi:
        return None
    numeri = [qp_int_strict(v, "lotti", 0) for v in grezzi]
    validati = parse_lotti(numeri, error_code=E_VALIDATION_INPUT)
    return list(validati) if validati else None


# Scopo: Normalizza `data_documento` nel payload di un job di fatturazione:
#        assente -> payload invariato; presente -> validata e riscritta in ISO
#        `YYYY-MM-DD`.
# ⭐ Estratto alla 2ª occorrenza (regola del 2): lo usano il giro (BE-1) e la
#    numerazione di perimetro (BE-2).
# ⚠️ Validata QUI e non solo nel worker: una data malformata deve tornare 400 a
#    chi preme il pulsante, non diventare un job fallito da leggere nei log un
#    minuto dopo.
# ⚠️ E RISCRITTA, non solo controllata: `optional_iso_date` accetta piu' forme
#    di quante il worker ne rilegga, e nel payload della coda deve finire una
#    sola forma — quella che `parse_data_iso` sa rileggere.
def _payload_con_data_documento(payload: dict[str, Any]) -> dict[str, Any]:
    data_documento = optional_iso_date(payload, "data_documento")
    if data_documento is None:
        return payload
    return {**payload, "data_documento": data_documento.isoformat()}


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
#
#        `accetta_lotti=True` (numerazione su SELEZIONE, solo «Rendi
#        definitive»): stessa identica meccanica con la lista dei lotti
#        spuntati. ⛔ I due flag sono ALTERNATIVI per verbo — si fattura per
#        gruppi, si numera per lotti — e non si combinano: sono due atti
#        diversi, e un verbo che accettasse entrambi non saprebbe quale
#        perimetro sta applicando.
def _accoda_job_fatturazione(
    request: Request,
    payload: dict[str, Any],
    *,
    job_type: str,
    extra_payload_keys: tuple[str, ...] = (),
    accetta_gruppi: bool = False,
    accetta_lotti: bool = False,
) -> dict[str, Any]:
    competenza = optional_iso_date(payload, "competenza_mese")
    ErrorManager.require(
        competenza is not None,
        code=E_VALIDATION_INPUT,
        message="`competenza_mese` obbligatoria.",
    )
    assert competenza is not None
    # Normalizza al 1° del mese PRIMA di comporre payload+chiave business: la
    # dedup dei job vivi è per-MESE, non per-giorno.
    competenza = competenza.replace(day=1)
    # Lo scope dell'operatore che accoda — terna dal JWT, emittente attivo
    # congelato, whitelist e `scope_key` — catturato dal BB `coda_lavori.scope`
    # (dal 2026-09-15 e' la sede unica: la stessa cattura serve a «Esegui ora»
    # dal drawer dei processi). ⚠️ Senza `identita_id` rifiuta PRIMA di
    # accodare, con lo stesso codice che il drenatore solleverebbe un minuto
    # dopo (`E_CODA_SCOPE_OPERATORE_INVALIDO`): fino a quel giorno qui era
    # `E_VALIDATION_INPUT` — stesso 400, ma un codice che non diceva DI CHE
    # COSA fosse l'errore.
    scope = scope_operatore_da_request(request)
    # Whitelist e chiave dello scope servono anche QUI, alla chiave di
    # business: dedup dei job vivi per (competenza, scope[, perimetro]).
    scope_key = str(scope["scope_key"])
    job_payload: dict[str, Any] = {"competenza_mese": competenza.isoformat()}
    for key in extra_payload_keys:
        value = payload.get(key)
        if value:
            job_payload[key] = value

    # Perimetro dell'emissione mirata: validato QUI (400 parlante al chiamante)
    # e non solo nel worker, dove diventerebbe un job fallito da leggere nei log.
    gruppi = (
        parse_gruppi(payload.get("gruppi"), error_code=E_VALIDATION_INPUT)
        if accetta_gruppi
        else None
    )
    if gruppi:
        job_payload["gruppi"] = list(gruppi)

    # Perimetro della numerazione su SELEZIONE (lista lotti). Stessa disciplina
    # dei gruppi: validato qui, 400 parlante, mai un perimetro che degenera.
    lotti = (
        parse_lotti(payload.get("lotti"), error_code=E_VALIDATION_INPUT)
        if accetta_lotti
        else None
    )
    if lotti:
        job_payload["lotti"] = list(lotti)

    # Chiave di BUSINESS (competenza + scope [+ perimetro mirato]), NON l'header
    # HTTP: dedup dei job VIVI (due click sullo stesso mese/scope → stesso job).
    # ⛔ Il digest COPRE il perimetro mirato, qualunque esso sia: senza, due
    #    selezioni DIVERSE sullo stesso mese sarebbero lo stesso job e la
    #    seconda verrebbe assorbita in silenzio — «accodato», e non succede
    #    niente. Vuoto sui giri di massa, cosi' la loro chiave resta quella
    #    storica.
    # ⚠️ Un verbo accetta gruppi OPPURE lotti, mai entrambi (sono due atti
    #    diversi): l'insieme che alimenta il digest e' quello dei due che c'e'.
    digest = insieme_digest(gruppi or lotti)
    # ⭐ La CORSIA entra nella chiave (2026-09-05, opzione A): qui il valore e'
    #    determinato dal perimetro — «mirata» quando l'operatore ha scelto dei
    #    gruppi, «differita» sul giro di massa — cioe' lo stesso che l'handler
    #    userebbe. ⇒ la chiave cambia forma e NON cambia comportamento; serve al
    #    secondo produttore, il batch, che le corsie le fa entrambe.
    # ⛔ Il valore NON si ricalcola qui con un `if`: si chiede al modulo che
    #    possiede la regola, o al primo cambio le due copie divergono.
    corsia = corsia_del_giro(job_type, gruppi=gruppi)
    idempotency_key = chiave_idempotenza_giro(
        job_type=job_type, competenza=competenza, scope_key=scope_key,
        corsia=corsia, digest=digest,
    )

    job_id = CodaLavoriRepository().accoda(
        job_type=job_type,
        payload=job_payload,
        run_as=RUN_AS_OPERATORE,
        scope=scope,
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
                "data_documento": serializers.DateField(
                    required=False,
                    allow_null=True,
                    help_text=(
                        "Data documento dichiarata per i lotti che il giro "
                        "creera'. Assente = la decide la politica del registro "
                        "(OGGI / FINE_MESE_COMPETENZA): non e' un sinonimo di "
                        "«oggi»."
                    ),
                ),
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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return _accoda_job_fatturazione(
                request, _payload_con_data_documento(payload),
                job_type=JOB_TYPE_FATTURAZIONE_GIRO,
                extra_payload_keys=("fino_a_stato", "data_documento"),
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
        emittente_ids = PermissionResolver.get_emittenti_pk_ids(request.user)
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
                "lotti": serializers.ListField(
                    child=serializers.IntegerField(),
                    required=False,
                    help_text=(
                        "Perimetro SELEZIONATO: gli id dei lotti da numerare. "
                        "Assente = tutti i lotti EMESSA della competenza (atto "
                        "di mese). Lista vuota -> 400, mai «tutti»: su un atto "
                        "fiscale non si indovina. ⚠️ Lo stato EMESSA si applica "
                        "comunque: un lotto selezionato ma non emesso non viene "
                        "numerato."
                    ),
                ),
                "data_documento": serializers.DateField(
                    required=False,
                    allow_null=True,
                    help_text=(
                        "Una data per l'INTERO atto (decisione 5 del brief "
                        "numerazione): vale per tutti i lotti che l'atto "
                        "numera. Assente = nessuna dichiarazione, ogni "
                        "documento tiene la data che ha."
                    ),
                ),
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
        # Scopo: enqueue comune + la data documento dell'atto (facoltativa).
        # ⚠️ Validata QUI e non solo nel worker: una data malformata deve
        #    tornare 400 a chi preme il pulsante, non diventare un job fallito
        #    da leggere nei log un minuto dopo.
        # ⚠️ NON entra nella chiave di BUSINESS della coda (competenza+scope):
        #    due «Rendi definitive» vivi sullo stesso mese e scope restano un
        #    doppione anche con date diverse — la dedup difende l'atto fiscale,
        #    non il parametro.
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return _accoda_job_fatturazione(
                request, _payload_con_data_documento(payload),
                job_type=JOB_TYPE_FATTURAZIONE_NUMERA,
                extra_payload_keys=("data_documento",),
                accetta_lotti=True,
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
