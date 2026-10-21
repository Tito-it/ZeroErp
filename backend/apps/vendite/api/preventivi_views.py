# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per preventivi vendita (lista, dettaglio, righe, stato, integrazione).
# ------------------------------------------------------------

from typing import Any
from datetime import date

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_actor_user_id, get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    optional_bool,
    optional_int,
    optional_iso_date,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api.indirizzi_documento_views import (
    build_indirizzi_documento_views,
)
from apps.vendite.api.riepilogo_iva_views import build_riepilogo_iva_view
from apps.vendite.services import preventivi_service
from apps.ui.api.lista_figlia_views import EMITTENTE_DOCUMENTO_PARAM, build_lista_figlia_views
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.core.api.openapi_params import param_ricerca_full
from apps.vendite.api._date_consegna_schema import DATE_CONSEGNA_REQUEST, DATE_CONSEGNA_RESPONSE
from apps.vendite.api._schema_da_contratto import schema_da_contratto
from apps.vendite.api._componenti_schema import (
    COMPONENTE_PATCH_REQUEST,
    COMPONENTI_LIST_PARAMETERS,
    COMPONENTI_LIST_RESPONSE,
    PREVIEW_COMPONENTI_REQUEST,
    PREVIEW_COMPONENTI_RESPONSE,
)

# Codice lista configurabile (catalogo ui.lista_definizione id=5). Usato
# dall'export per risolvere colonne visibili/ordine/permessi dell'utente.
_LISTA_CODICE_PREVENTIVI = "vendite.preventivi"


# Scopo: normalizza `righe_ids` dal body degli endpoint di smistamento
#        selettivo (genera-ordine, push-commessa). Assente/null = tutte le
#        righe eleggibili (None). Lista vuota = errore esplicito: NON deve
#        degradare silenziosamente a "tutte" (un client che intende "nessuna
#        riga" otterrebbe il push completo).
def _parse_righe_ids(payload: dict[str, Any]) -> list[int] | None:
    righe_ids = payload.get("righe_ids")
    if righe_ids is None:
        return None
    ErrorManager.require(
        isinstance(righe_ids, list) and len(righe_ids) > 0,
        code="E_PREV_VALIDAZIONE",
        message="righe_ids non valido: lista non vuota di id riga, "
                "oppure omettere il campo per smistare tutte le righe.",
        detail=f"righe_ids={righe_ids!r}",
        function_name="apps.vendite.api.preventivi_views._parse_righe_ids",
    )
    assert isinstance(righe_ids, list)
    return [int(r) for r in righe_ids]


# Il corpo che `_parse_righe_ids` legge — push in commessa e genera ordine: una
# sede sola accanto al parser, che e' il contratto.
_RIGHE_IDS_REQUEST = inline_serializer(
    name="PreventivoRigheIdsReq",
    fields={"righe_ids": serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_null=True,
        help_text="Omessa: tutte le righe eleggibili. Una lista vuota e' un errore.",
    )},
)


# ── Schemi OpenAPI dei corpi: le chiavi dal contratto del service ──────────
# ⭐ Dal 2026-09-26: gli schemi scritti a mano pubblicavano `iva_id` (chiuso da
#    `I6`) e `quantita` (la calcola il trigger), che il service ignorava, e ne
#    tacevano altre che il service legge.
_PREVENTIVO_CREATE_REQUEST = schema_da_contratto(
    "PreventivoCreateRequest", preventivi_service.CREATE_KEYS_PREVENTIVO,
    obbligatorie=("utility_id",),
)
_PREVENTIVO_UPDATE_REQUEST = schema_da_contratto(
    "PreventivoUpdateRequest", preventivi_service.UPDATE_KEYS_PREVENTIVO,
)
_PREVENTIVO_RIGA_CREATE_REQUEST = schema_da_contratto(
    "PreventivoRigaCreateRequest", preventivi_service.CREATE_KEYS_RIGA,
    obbligatorie=("articolo_id",),
)
# In modifica: le colonne scritte in blocco + le due chiavi lette a parte.
_PREVENTIVO_RIGA_UPDATE_REQUEST = schema_da_contratto(
    "PreventivoRigaUpdateRequest",
    preventivi_service.UPDATE_KEYS_RIGA | preventivi_service.UPDATE_RIGA_LETTE_A_PARTE,
)


# ── Lista + Creazione ──


class ApiPreventiviList(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")
    is_search_endpoint = True
    lista_codice = "vendite.preventivi"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False, description="ISO date"),
            OpenApiParameter(name="data_al", type=str, required=False, description="ISO date"),
            param_ricerca_full(),
            OpenApiParameter(
                name="solo_ultima_revisione", type=bool, required=False,
                description="Default true: mostra solo l'ultima revisione per numero. "
                            "Passare false per includere lo storico revisioni superseded.",
            ),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="campo_sorgente colonna (default 'data')"),
            OpenApiParameter(name="order_dir", type=str, required=False,
                             description="asc | desc (default desc)"),
        ],
        responses={200: inline_serializer(
            name="PreventiviListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET l'elenco paginato dei preventivi vendita.
    #        Paginazione standard limit/offset via parse_list_params (allineata
    #        a clienti/contratti/offerte/ordini; il vecchio page/page_size era
    #        l'unico outlier del dominio). order_dir assente -> il default 'desc'
    #        di dominio, scritto qui. Usa direttamente
    #        list_preventivi_rows + paginated_envelope (mirror views_ordini); il
    #        wrapper list_preventivi(limit/offset, envelope) resta per AI tool + test.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        auth_user_id = get_scope_user_id(request)
        p = parse_list_params(qp, default_order="data")
        order_dir = qp_str(qp.get("order_dir")) or "desc"
        results, total = preventivi_service.list_preventivi_rows(
            stato_codice=qp_str(qp.get("stato")),
            billing_account_id=optional_int({"v": qp.get("billing_account_id")}, "v"),
            utility_id=optional_int({"v": qp.get("utility_id")}, "v"),
            data_da=optional_iso_date({"v": qp.get("data_da")}, "v"),
            data_al=optional_iso_date({"v": qp.get("data_al")}, "v"),
            search=qp_str(qp.get("search")),
            # Default true: lista pulita senza storico revisioni. Il FE
            # passa "false" esplicito col toggle "Mostra storico".
            solo_ultima_revisione=qp_bool_optional(qp.get("solo_ultima_revisione"), "solo_ultima_revisione", default=True),
            auth_user_id=auth_user_id,
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=order_dir,
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=_PREVENTIVO_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="PreventivoCreateResponse",
            fields={
                "data": inline_serializer(name="PreventivoCreateData", fields={
                    "id": serializers.IntegerField(),
                    "uid": serializers.CharField(),
                    "numero": serializers.CharField(),
                }),
            },
        )},
    )
    # Scopo: Crea un nuovo preventivo vendita via POST.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return preventivi_service.crea_preventivo(payload)
        return handle_post_json(request, handler=_handler)


class ApiPreventiviExportView(DomainAPIView):
    """GET /api/v1/vendite/preventivi/export/?formato=csv|xlsx

    Genera un file CSV o Excel con i preventivi filtrati dalla query string
    (stessi parametri del list endpoint). Hard cap EXPORT_MAX_ROWS righe — sopra
    solleva E_UI_EXPORT_LIMIT_EXCEEDED (422). Usa il renderer generico
    `ListaExportService` (DEF-1) e il catalogo colonne `vendite.preventivi` per
    coerenza con la DataTable a video (colonne nascoste escluse, ordine utente
    rispettato).

    NB: il parametro si chiama `formato` (italiano), NON `format` — magic
    parameter DRF (content-negotiation) che intercetterebbe la chiamata prima
    della view (memoria feedback_drf_format_magic_param).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")
    is_search_endpoint = True
    lista_codice = "vendite.preventivi"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
            OpenApiParameter(name="stato", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_al", type=str, required=False),
            OpenApiParameter(name="solo_ultima_revisione", type=bool, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Export CSV/XLSX della lista preventivi. Riusa la coda invariante
    #        `build_export_response` (DEF-1). Scope emittente + filtri identici
    #        al list endpoint; fetcha fino a EXPORT_MAX_ROWS+1 per intercettare
    #        l'overflow.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)
        auth_user_id = get_scope_user_id(request)

        stato_codice = qp_str(qp.get("stato"))
        billing_account_id = optional_int({"v": qp.get("billing_account_id")}, "v")
        utility_id = optional_int({"v": qp.get("utility_id")}, "v")
        data_da = optional_iso_date({"v": qp.get("data_da")}, "v")
        data_al = optional_iso_date({"v": qp.get("data_al")}, "v")
        search = qp_str(qp.get("search"))
        solo_ultima_revisione = qp_bool_optional(qp.get("solo_ultima_revisione"), "solo_ultima_revisione", default=True)

        results, total = preventivi_service.list_preventivi_rows(
            stato_codice=stato_codice,
            billing_account_id=billing_account_id,
            utility_id=utility_id,
            data_da=data_da,
            data_al=data_al,
            search=search,
            solo_ultima_revisione=solo_ultima_revisione,
            auth_user_id=auth_user_id,
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=qp_str(qp.get("order_by")) or "data",
            order_dir=qp_str(qp.get("order_dir")) or "desc",
            max_limit=EXPORT_MAX_ROWS + 1,
        )
        filtri_applicati = preventivi_service.resolve_filtri_export_label(
            stato_codice=stato_codice,
            billing_account_id=billing_account_id,
            utility_id=utility_id,
            data_da=data_da,
            data_al=data_al,
            solo_ultima_revisione=solo_ultima_revisione,
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_PREVENTIVI,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


# ── Dettaglio + Aggiornamento ──


class ApiPreventivoDetail(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoDetailResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET il dettaglio completo di un preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.get_preventivo(preventivo_id)
        return success_response(data)

    @extend_schema(
        request=_PREVENTIVO_UPDATE_REQUEST,
        responses={200: inline_serializer(
            name="PreventivoUpdateResponse",
            fields={"data": inline_serializer(name="PreventivoUpdateData", fields={
                "status": serializers.CharField(),
                "preventivo_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Aggiorna un preventivo via PATCH.
    def patch(self, request: Request, preventivo_id: int) -> JsonResponse:
        result = preventivi_service.aggiorna_preventivo(preventivo_id, corpo_oggetto(request))
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoDeleteResponse",
            fields={"data": inline_serializer(name="PreventivoDeleteData", fields={
                "status": serializers.CharField(),
                "preventivo_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Hard-delete preventivo BOZZA orfano (zero righe, zero pratiche).
    #        Supporto al pattern "abbandono bozza" del drawer FE.
    #        Per preventivi gia' propagati o con stato avanzato, usare invece
    #        POST /preventivi/<id>/stato/ con nuovo_stato=ANNULLATO.
    def delete(self, request: Request, preventivo_id: int) -> JsonResponse:
        del request
        result = preventivi_service.elimina_preventivo(preventivo_id)
        return success_response(result)


# ── Cambio stato ──


# Scopo: parsing condiviso del payload cambio-stato preventivo (EMESSO→ACCETTATO,
#        *→ANNULLATO/RIFIUTATO, ...). `fatturazione_immediata`: None ("non passato",
#        ignora il gate accettazione) ≠ False esplicito (richiede competenza) →
#        `optional_bool(default=False)` non distingue, quindi lookup raw. Estratto
#        (regola del 2) da ApiPreventivoStato + ApiPreventivoStatoDaPratica.
def _parse_cambio_stato_payload(
    payload: dict[str, Any],
) -> tuple[str, bool | None, date | None]:
    nuovo_stato = str(payload.get("nuovo_stato", ""))
    raw_fi = payload.get("fatturazione_immediata")
    fatturazione_immediata = (
        None if raw_fi is None else optional_bool(payload, "fatturazione_immediata")
    )
    competenza_mese = optional_iso_date(payload, "competenza_mese")
    return nuovo_stato, fatturazione_immediata, competenza_mese


class ApiPreventivoStato(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "cambia_stato_preventivi"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoStatoRequest",
            fields={
                "nuovo_stato": serializers.CharField(),
                # Obbligatori solo su transizione EMESSO/ACCETTATO → ACCETTATO
                # (modalita' fatturazione del preventivo accettato). Ignorati
                # sulle altre transizioni.
                "fatturazione_immediata": serializers.BooleanField(
                    required=False, allow_null=True,
                ),
                "competenza_mese": serializers.DateField(
                    required=False, allow_null=True,
                ),
                # Verso ANNULLATO: quanti legami l'operatore ha visto nella
                # finestra di conferma (assente al primo tentativo).
                "legami_confermati": serializers.IntegerField(
                    required=False, allow_null=True,
                ),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoStatoResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Cambia stato preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            nuovo_stato, fatturazione_immediata, competenza_mese = (
                _parse_cambio_stato_payload(payload)
            )
            return preventivi_service.cambia_stato(
                preventivo_id, nuovo_stato,
                fatturazione_immediata=fatturazione_immediata,
                competenza_mese=competenza_mese,
                # user serve al hook atomico EMESSO per scope emittente +
                # audit `generato_da_user_id` su documenti_generati.
                user=request.user,
                legami_confermati=payload.get("legami_confermati"),
            )
        return handle_post_json(request, handler=_handler)


class ApiPreventivoStatoDaPratica(DomainAPIView):
    """GUIDA (D4): «Accetta/Rifiuta» in-pratica → cambio stato del preventivo ROOT
    della pratica (inversione handler→proiezione). Il documento e' sovrano; il
    milestone avanza da solo via trigger DB `fn_reconcile_sorgente`. Stesso payload
    di `ApiPreventivoStato`, ma la view risolve il preventivo dal `pratica_id`."""

    area_funzionale = "vendite"
    post_permission = "cambia_stato_preventivi"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoStatoDaPraticaRequest",
            fields={
                "nuovo_stato": serializers.CharField(),
                "fatturazione_immediata": serializers.BooleanField(
                    required=False, allow_null=True,
                ),
                "competenza_mese": serializers.DateField(
                    required=False, allow_null=True,
                ),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoStatoDaPraticaResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Cambia stato del preventivo ROOT della pratica via POST.
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            nuovo_stato, fatturazione_immediata, competenza_mese = (
                _parse_cambio_stato_payload(payload)
            )
            return preventivi_service.cambia_stato_da_pratica(
                pratica_id, nuovo_stato,
                fatturazione_immediata=fatturazione_immediata,
                competenza_mese=competenza_mese,
                user=request.user,
            )
        return handle_post_json(request, handler=_handler)


# ── Revisione ──


class ApiPreventivoRevisione(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        request=None,
        responses={200: inline_serializer(
            name="PreventivoRevisioneResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea nuova revisione preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return preventivi_service.crea_revisione(preventivo_id)
        return handle_post_json(request, handler=_handler)


class ApiPreventivoGeneraOrdine(DomainAPIView):
    """`POST /api/v1/vendite/preventivi/<id>/genera-ordine/` — smistamento
    MERCE → ordine (modello split D8). Body opzionale `{righe_ids: [..]}` per lo
    smistamento selettivo; assente = tutte le righe merce residue."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        request=_RIGHE_IDS_REQUEST,
        responses={200: inline_serializer(
            name="PreventivoGeneraOrdineResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Smista a un ordine DRAFT le righe MERCE di un preventivo ACCETTATO
    #        (natura destinazione ORDINE), via fn_push_preventivo_a_ordine
    #        (snapshot prezzi + BoM + link di riga, niente servizi). Delega a
    #        ordini_service (stesso app vendite). Ritorna {ordine_id, numero, ...}.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        from apps.vendite.services import ordini_service

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return ordini_service.crea_ordine_da_preventivo(
                preventivo_id, righe_ids=_parse_righe_ids(payload),
            )
        return handle_post_json(request, handler=_handler)


class ApiPreventivoRigheSmistabiliOrdine(DomainAPIView):
    """`GET /api/v1/vendite/preventivi/<id>/righe-smistabili-ordine/` — righe
    MERCE (natura destinazione ORDINE) non ancora allocate. Alimenta il dialog
    di smistamento riga-per-riga preventivo→ordine."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigheSmistabiliOrdineResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Righe merce smistabili a ordine (per il dialog "Genera ordine").
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.list_righe_smistabili_ordine(preventivo_id)
        return success_response(data)


class ApiPreventivoCollegaPratica(DomainAPIView):
    """`POST /api/v1/vendite/preventivi/<id>/collega-pratica/`: aggancia il
    preventivo come ROOT a una pratica (pratiche_sorgenti). Usato a PREVENTIVAZIONE
    sul percorso pratica-first. Idempotente."""

    area_funzionale = "vendite"
    post_permission = "cambia_stato_preventivi"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoCollegaPraticaRequest",
            fields={"pratica_id": serializers.IntegerField()},
        ),
        responses={200: inline_serializer(
            name="PreventivoCollegaPraticaResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        # Dal BB: `payload["pratica_id"]` assente era un KeyError, cioe' un 500.
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            v = PayloadValidator(validation_code="E_PREV_VALIDAZIONE")
            return preventivi_service.collega_pratica(
                preventivo_id,
                pratica_id=v.require_positive_int(payload, "pratica_id"),
                flusso_id=v.optional_positive_int(payload, "flusso_id"),
            )
        return handle_post_json(request, handler=_handler)


class ApiPreventivoRootPerFlusso(DomainAPIView):
    """`GET /api/v1/vendite/preventivi/root-per-flusso/?flusso_id=<id>`:
    risolve il preventivo ROOT agganciato a un flusso (pratiche_sorgenti,
    aggancio per-flusso). Alimenta la RIAPERTURA dal percorso: l'attivita' UI
    "apri preventivo" apre il ROOT esistente di quel flusso in edit invece di
    crearne uno nuovo. Ritorna `{"preventivo_id": <id|null>}`. Lettura libera."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="flusso_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
        ],
        responses={200: inline_serializer(
            name="PreventivoRootPerFlussoResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    def get(self, request: Request) -> JsonResponse:
        flusso_id = optional_int({"v": request.query_params.get("flusso_id")}, "v")
        ErrorManager.require(
            flusso_id is not None,
            code="E_FLUSSO_ID_OBBLIGATORIO",
            message="flusso_id obbligatorio.",
        )
        assert flusso_id is not None
        return success_response(preventivi_service.get_root_per_flusso(flusso_id))


class ApiPreventivoRootPerPratica(DomainAPIView):
    """`GET /api/v1/vendite/preventivi/root-per-pratica/?pratica_id=<id>`:
    risolve il preventivo ROOT della PRATICA (non per-flusso). Alimenta gli step
    a valle del percorso (es. SMISTAMENTO) che operano sul preventivo gia'
    agganciato a monte. Ritorna `{"preventivo_id": <id|null>}`. Lettura libera."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="pratica_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
        ],
        responses={200: inline_serializer(
            name="PreventivoRootPerPraticaResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    def get(self, request: Request) -> JsonResponse:
        pratica_id = optional_int({"v": request.query_params.get("pratica_id")}, "v")
        ErrorManager.require(
            pratica_id is not None,
            code="E_PRATICA_ID_OBBLIGATORIO",
            message="pratica_id obbligatorio.",
        )
        assert pratica_id is not None
        return success_response(preventivi_service.get_root_per_pratica(pratica_id))


class ApiPreventivoRevisioniList(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")
    lista_codice = "vendite.preventivo_revisioni"
    # ⭐ Il tab vive DENTRO il drawer di un preventivo, che ha gia' il suo
    #    emittente: la lista a catalogo e' `perimetro_emittente = t` e
    #    `multi_emittente = f`, quindi senza questa riga chi vede piu'
    #    emittenti (il super admin su «Tutti») riceverebbe
    #    E_UI_LISTA_EMITTENTE_DA_SCEGLIERE a drawer gia' aperto — gli si
    #    chiederebbe di scegliere l'emittente del documento che sta guardando.
    #    E' la PK (`emittenti_fiscali.id`), come `v.emittente_fiscale_id`.
    lista_emittente_param = "emittente_fiscale_id"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="emittente_fiscale_id", type=int, required=False,
                description=(
                    "Emittente del documento (PK). Lo legge SOLO il cancello di "
                    "perimetro, per chi vede più emittenti: non filtra le righe "
                    "(la catena è di un emittente solo) e non allarga niente — "
                    "la visibilità resta allo scope e alla RLS."
                ),
            ),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="rev (default) | data | totale_documento"),
            OpenApiParameter(name="order_dir", type=str, required=False,
                             description="asc | desc (assente: asc; desc sulle date)"),
        ],
        responses={200: inline_serializer(
            name="PreventivoRevisioniListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista PAGINATA della catena revisioni che condividono lo stesso
    #        `numero` del preventivo passato (default `rev` ASC). Mirror di
    #        `ApiOffertaRevisioni`: stesso envelope, stesse colonne gemelle a
    #        catalogo. Lettura libera in ogni stato.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="rev")
        results, total = preventivi_service.list_revisioni(
            preventivo_id,
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


# ── Righe: lista + creazione ──


class ApiPreventivoRigheList(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigheListResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET le righe del preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.list_righe(preventivo_id)
        return success_response(data)

    @extend_schema(
        request=_PREVENTIVO_RIGA_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="PreventivoRigaCreateResponse",
            fields={"data": inline_serializer(name="PreventivoRigaCreateData", fields={
                "id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Aggiunge riga al preventivo via POST.
    #        Auto-fill prezzo da resolver v5 + check L1 override: vedi
    #        sviluppo-autorizzazioni-prezzi.md §3. auth_user_id e' passato
    #        al service per risolvere emittente + verificare permesso.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return preventivi_service.gestisci_riga(
                preventivo_id, payload, auth_user_id=auth_user_id,
            )
        return handle_post_json(request, handler=_handler)


# ── Righe: aggiornamento + eliminazione ──


class ApiPreventivoRigaDetail(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        request=_PREVENTIVO_RIGA_UPDATE_REQUEST,
        responses={200: inline_serializer(
            name="PreventivoRigaUpdateResponse",
            fields={"data": inline_serializer(name="PreventivoRigaUpdateData", fields={
                "status": serializers.CharField(),
                "riga_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Aggiorna riga preventivo via PATCH.
    #        Se il payload tocca `prezzo_unitario`, scatta il check L1
    #        (permesso prezzo_override_manuale se diverso dal resolver).
    def patch(self, request: Request, preventivo_id: int, riga_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        result = preventivi_service.aggiorna_riga(
            preventivo_id, riga_id, corpo_oggetto(request), auth_user_id=auth_user_id,
        )
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigaDeleteResponse",
            fields={"data": inline_serializer(name="PreventivoRigaDeleteData", fields={
                "status": serializers.CharField(),
                "riga_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Elimina (soft delete) riga preventivo via DELETE.
    def delete(self, request: Request, preventivo_id: int, riga_id: int) -> JsonResponse:
        result = preventivi_service.elimina_riga(preventivo_id, riga_id)
        return success_response(result)


class ApiPreventivoRigheDateConsegna(DomainAPIView):
    """POST /api/v1/vendite/preventivi/<preventivo_id>/righe/date-consegna/.

    «Aggiorna date di consegna»: la data richiesta dal cliente su piu' righe,
    TUTTE o SOLO_VUOTE (brief-db-date-consegna-righe-in-blocco). Il lock delle
    righe la ammette solo in bozza.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(request=DATE_CONSEGNA_REQUEST, responses={200: DATE_CONSEGNA_RESPONSE})
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: preventivi_service.aggiorna_date_consegna(
                int(preventivo_id), payload,
            ),
        )


# ── Componenti BoM CASO A (refactor componenti 2026-05-11) ──
#
# Endpoint nidificati sotto riga padre:
#   GET    /preventivi/<id>/righe/<riga_id>/componenti/
#   PATCH  /preventivi/<id>/righe/<riga_id>/componenti/<componente_id>/
#   DELETE /preventivi/<id>/righe/<riga_id>/componenti/<componente_id>/
# Init e' implicito post-create_riga via `gestisci_riga` — niente POST
# pubblico dedicato. Vedi `refactor-componenti.md`.
#
# Form atomic 2026-05-12: nuovo endpoint preview pre-save:
#   POST /preventivi/<id>/righe/preview-componenti/
# Restituisce la lista dei componenti esposti del padre con prezzi
# suggeriti (NULL + reason se resolver fail). Consumato dal drawer riga FE
# per pre-popolare la tabella editabile prima del save.


class ApiPreventivoRigaPreviewComponenti(DomainAPIView):
    """POST /api/v1/vendite/preventivi/<id>/righe/preview-componenti/

    Preview componenti BoM CASO A per il drawer riga (form atomic). Read-only:
    no side-effect. Per ogni componente esposto del padre ritorna prezzo
    suggerito + origine, oppure NULL + resolver_error_reason se manca listino.
    Il FE pre-popola la tabella editabile dei componenti, l'operatore
    valorizza eventuali NULL prima del save (con autorizzazione
    `prezzo_override_manuale`).

    Payload: `{articolo_id: uuid, uom_operativa_id: int, quantita: number}`
    Risposta: `{data: [{componente_id, codice, prezzo_suggerito, ...}]}`
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")
    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

    @extend_schema(
        request=PREVIEW_COMPONENTI_REQUEST,
        responses={200: PREVIEW_COMPONENTI_RESPONSE},
    )
    # Scopo: Restituisce via POST la preview componenti CASO A per drawer riga.
    def post(
        self, request: Request, preventivo_id: int,
    ) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> list[dict[str, Any]]:
            auth_user_id = get_actor_user_id(request)
            articolo_id = str(payload.get("articolo_id") or "")
            uom_id = optional_int(payload, "uom_operativa_id")
            quantita_raw = payload.get("quantita")
            return preventivi_service.preview_componenti_riga(
                preventivo_id,
                articolo_id=articolo_id,
                uom_operativa_id=uom_id,
                quantita=quantita_raw,
                auth_user_id=auth_user_id,
            )

        return handle_post_json(request, handler=_handler)


class ApiPreventivoRigaComponentiList(DomainAPIView):
    """GET /api/v1/vendite/preventivi/<id>/righe/<riga_id>/componenti/

    Lista i componenti BoM CASO A di una riga padre composita.
    Restituisce array vuoto se la riga non e' CASO A (no componenti).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")
    is_search_endpoint = True

    @extend_schema(
        parameters=COMPONENTI_LIST_PARAMETERS,
        responses={200: COMPONENTI_LIST_RESPONSE},
    )
    # Scopo: Restituisce via GET la lista componenti di una riga padre.
    #        Query param `solo_attivi` (default true) controlla se includere
    #        gli opzionali disattivati.
    def get(
        self, request: Request, preventivo_id: int, riga_id: int,
    ) -> JsonResponse:
        # Il BB dei flag di trasporto (§A6), come i gemelli DDT e ordini.
        solo_attivi = qp_bool_optional(request.query_params.get("solo_attivi"), "solo_attivi", default=True)
        result = preventivi_service.list_componenti_riga(
            preventivo_id, riga_id, solo_attivi=solo_attivi,
        )
        return success_response(result)


class ApiPreventivoRigaComponenteDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/preventivi/<id>/righe/<riga_id>/componenti/<componente_id>/

    Modifica fine (prezzo override, ecc.) e soft delete del singolo
    componente. Il trigger DB di ricalcolo aggiorna automaticamente il
    `prezzo_unitario` della riga padre come SUM(componenti × coeff_qta).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        request=COMPONENTE_PATCH_REQUEST,
        responses={200: inline_serializer(
            name="PreventivoRigaComponenteUpdateResponse",
            fields={"data": inline_serializer(
                name="PreventivoRigaComponenteUpdateData", fields={
                    "status": serializers.CharField(),
                    "componente_id": serializers.IntegerField(),
                },
            )},
        )},
    )
    # Scopo: Aggiorna componente via PATCH. Solo i campi del contratto
    #        operatore `COMPONENTE_PATCH_OPERATORE`: gli altri sono un 400
    #        (`E_PREV_VALIDAZIONE`, dal 2026-09-26 — prima ignorati in silenzio).
    #        `riga_id` URL passato al service per check anti-tampering
    #        (deve matchare la riga padre reale del componente).
    def patch(
        self,
        request: Request,
        preventivo_id: int,
        riga_id: int,
        componente_id: int,
    ) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        result = preventivi_service.update_componente(
            preventivo_id, riga_id, componente_id, corpo_oggetto(request),
            auth_user_id=auth_user_id,
        )
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigaComponenteDeleteResponse",
            fields={"data": inline_serializer(
                name="PreventivoRigaComponenteDeleteData", fields={
                    "status": serializers.CharField(),
                    "componente_id": serializers.IntegerField(),
                    "deleted": serializers.BooleanField(),
                },
            )},
        )},
    )
    # Scopo: Soft delete componente via DELETE. `riga_id` URL passato al
    #        service per check anti-tampering (deve matchare la riga padre
    #        reale del componente).
    def delete(
        self,
        request: Request,  # DRF richiede signature
        preventivo_id: int,
        riga_id: int,
        componente_id: int,
    ) -> JsonResponse:
        result = preventivi_service.delete_componente(
            preventivo_id, riga_id, componente_id,
        )
        return success_response(result)


# ── Suggerimento prezzo riga via pricing resolver v5 ──


class ApiPreventivoRigaSuggerisciPrezzo(DomainAPIView):
    """POST /api/v1/vendite/preventivi/<id>/righe/suggerisci-prezzo/

    Wrappa `preventivi_service.suggerisci_prezzo_riga`. Non modifica nulla:
    legge testata preventivo (BA, utility, data) + articolo + UoM dal
    payload, deriva emittente dal JWT operatore, delega al pricing
    resolver v5. Usato dal FE per pre-compilare il campo prezzo
    all'apertura del drawer riga.

    Area `vendite` livello LETTURA sufficiente (no scrittura).
    Vedi docs/it/dev/work-in-progress/sviluppo-autorizzazioni-prezzi.md.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")
    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoRigaSuggerisciPrezzoRequest",
            fields={
                "articolo_id": serializers.UUIDField(),
                "uom_id": serializers.IntegerField(),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoRigaSuggerisciPrezzoResponse",
            fields={"data": inline_serializer(
                name="PreventivoRigaSuggerisciPrezzoData",
                fields={
                    "prezzo_finale": serializers.DecimalField(max_digits=22, decimal_places=10),
                    "prezzo_base_snapshot": serializers.DecimalField(max_digits=22, decimal_places=10, allow_null=True),
                    "origine": serializers.CharField(),
                    "listino_id": serializers.IntegerField(allow_null=True),
                    "contratto_id": serializers.IntegerField(allow_null=True),
                    "promo_id": serializers.IntegerField(allow_null=True),
                    "tipo_variazione_applicata": serializers.CharField(allow_null=True),
                    "valore_variazione_applicata": serializers.DecimalField(max_digits=10, decimal_places=4, allow_null=True),
                },
            )},
        )},
    )
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            articolo_id = payload.get("articolo_id")
            uom_id = payload.get("uom_id")
            auth_user_id = get_actor_user_id(request)
            return preventivi_service.suggerisci_prezzo_riga(
                preventivo_id,
                articolo_id=str(articolo_id) if articolo_id else None,
                uom_id=int(uom_id) if uom_id is not None else None,
                auth_user_id=auth_user_id,
            )
        return handle_post_json(request, handler=_handler)


# ── Riepilogo IVA aggregato (regola fiscale art. 21 DPR 633/72) ──


# View dal factory condiviso `build_riepilogo_iva_view` (estrazione
# regola-del-2 dei cloni preventivi/ordini/ddt). La closure legge il global
# di modulo a call-time: i patch dei test sul service restano validi.
ApiPreventivoRiepilogoIva = build_riepilogo_iva_view(
    schema_prefix="Preventivo",
    url_kwarg="preventivo_id",
    list_call=lambda preventivo_id: preventivi_service.list_riepilogo_iva(
        preventivo_id),
    doc="""GET /api/v1/vendite/preventivi/<id>/riepilogo-iva/

    Restituisce il riepilogo IVA del preventivo: una riga per gruppo
    (iva_id, natura, esigibilita, split_payment) con imponibile e imposta
    aggregati e arrotondati a 2 decimali sull'aggregato per aliquota
    (regola fiscale: DPR 633/72 art. 21 + DM 24/12/93). Lettura pura dalla
    view denormalizzata `vendite.vw_preventivi_riepilogo_iva_dettaglio`,
    nessun side-effect: il riepilogo e' mantenuto dal trigger AFTER su
    preventivi_righe via fn_ricalcola_riepilogo_iva_preventivo.

    Area `vendite` livello LETTURA sufficiente.
    """,
    model_permission=("vendite", "preventivo"),
)


# ── Contesto pricing ──


class ApiPreventivoContestoPricing(DomainAPIView):
    """GET /api/v1/vendite/preventivi/<id>/contesto-pricing/

    Ritorna il contesto pricing applicato al preventivo: contratto attivo
    (se presente per BA/utility/data) oppure listino mappato alla categoria
    cliente, oppure nessuna config. Lettura informativa per l'header del
    drawer preventivo (audit visivo del path resolver). Lo stesso resolver
    `fn_resolve_prezzo_listino_v2` applica la stessa logica al calcolo
    prezzi riga.

    Area `vendite` livello LETTURA sufficiente.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoContestoPricingResponse",
            fields={"data": inline_serializer(
                name="PreventivoContestoPricingData",
                fields={
                    "preventivo_id": serializers.IntegerField(),
                    "data_riferimento": serializers.DateField(),
                    "fonte": serializers.CharField(
                        help_text="'CONTRATTO' | 'CATEGORIA' | 'NONE'",
                    ),
                    "contratto_id": serializers.IntegerField(allow_null=True),
                    "contratto_numero": serializers.CharField(allow_null=True),
                    "listino_id": serializers.IntegerField(allow_null=True),
                    "listino_codice": serializers.CharField(allow_null=True),
                    "listino_descrizione": serializers.CharField(allow_null=True),
                    "categoria_cliente_id": serializers.IntegerField(allow_null=True),
                    "categoria_cliente_codice": serializers.CharField(allow_null=True),
                    "categoria_cliente_descrizione": serializers.CharField(allow_null=True),
                },
            )},
        )},
    )
    # Scopo: Restituisce via GET il contesto pricing del preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.get_contesto_pricing(preventivo_id)
        return success_response(data or {})


# ── Indirizzi ──


# View dal factory condiviso `build_indirizzi_documento_views` (pannello
# indirizzi slot-per-tipo, design brief-design-indirizzi-documenti-vendita).
_indirizzi_views = build_indirizzi_documento_views(
    schema_prefix="Preventivo",
    url_kwarg="preventivo_id",
    list_call=lambda preventivo_id: preventivi_service.list_indirizzi(preventivo_id),
    upsert_call=lambda preventivo_id, payload: preventivi_service.upsert_indirizzo(
        preventivo_id, payload),
    delete_call=lambda preventivo_id, indirizzo_id: preventivi_service.delete_indirizzo(
        preventivo_id, indirizzo_id),
    model_permission=("vendite", "preventivo"),
)
ApiPreventivoIndirizzi = _indirizzi_views.lista
ApiPreventivoIndirizzoDetail = _indirizzi_views.detail


# ── Integrazione: push commessa ──


class ApiPreventivoPushCommessa(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "push_commessa_preventivi"

    @extend_schema(
        request=_RIGHE_IDS_REQUEST,
        responses={200: inline_serializer(
            name="PreventivoPushCommessaResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Push preventivo in commessa per fatturazione via POST. Body
    # opzionale `{righe_ids: [..]}` per lo smistamento selettivo (Pannello
    # Smistamento); assente = tutte le righe servizio eleggibili. Ritorna
    # report dell'orchestrator: stato (COMPLETATO/PARZIALE/ERRORE), push_log_id,
    # durata_ms, handlers (dettaglio per handler con counters e errors), e
    # righe_pushable (diagnostico pre-push). Idempotency-Key obbligatoria
    # (write-once: evita doppio push su retry/click multipli).
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return preventivi_service.push_a_commessa(
                preventivo_id, righe_ids=_parse_righe_ids(payload),
            )
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ── Integrazione: smistamento (pannello) ──


class ApiPreventivoSmistamento(DomainAPIView):
    """`GET /api/v1/vendite/preventivi/<id>/smistamento/` — fonte dati del
    Pannello Smistamento: aggregato per ramo (progress verso EVASO) + righe con
    natura, destinazione e stato autorevole. Sostituisce il vecchio
    `/stato-fatturazione/` (viste DB rinominate natura-aware, 2026-06-12)."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoSmistamentoResponse",
            fields={"data": inline_serializer(name="PreventivoSmistamentoData", fields={
                "aggregato": serializers.DictField(),
                "righe": serializers.ListField(child=serializers.DictField()),
            })},
        )},
    )
    # Scopo: Restituisce via GET lo smistamento del preventivo (aggregato + righe).
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.smistamento(preventivo_id)
        return success_response(data)


class ApiPreventivoCompletaSmistamento(DomainAPIView):
    """`POST /api/v1/vendite/preventivi/<id>/completa-smistamento/` — completa il
    flusso SMISTAMENTO della pratica con l'esito di RAMO calcolato dal dominio
    (MERCE_PRESENTE/SOLO_SERVIZI, bivio-per-esito rev.3). L'operatore NON sceglie
    l'esito (il FE sopprime il picker): e' derivato dallo split gia' eseguito nel
    Pannello. Guard: smistamento completo su entrambi i rami. Idempotente."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "preventivo")

    @extend_schema(
        request=None,
        responses={200: inline_serializer(
            name="PreventivoCompletaSmistamentoResponse",
            fields={"data": inline_serializer(
                name="PreventivoCompletaSmistamentoData",
                fields={
                    "flusso_id": serializers.IntegerField(),
                    "esito": serializers.CharField(),
                    "gia_completato": serializers.BooleanField(),
                },
            )},
        )},
    )
    # Scopo: Completa lo step SMISTAMENTO con esito di ramo calcolato dal dominio.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return preventivi_service.completa_smistamento(
                preventivo_id,
                user=getattr(request.user, "username", None) or None,
            )
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ── Integrazione: genera pratica ──


class ApiPreventivoGeneraPratica(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "genera_pratica_preventivi"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoGeneraPraticaRequest",
            fields={
                "tipo_prestazione_id": serializers.IntegerField(),
                "priorita_id": serializers.IntegerField(),
                "descrizione": serializers.CharField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoGeneraPraticaResponse",
            fields={"data": inline_serializer(name="PreventivoGeneraPraticaData", fields={
                "pratica_id": serializers.IntegerField(),
                "preventivo_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Genera pratica esecutiva da preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        # Dal BB: un campo assente era un KeyError, cioe' un 500.
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            v = PayloadValidator(validation_code="E_PREV_VALIDAZIONE")
            return preventivi_service.genera_pratica(
                preventivo_id,
                tipo_prestazione_id=v.require_positive_int(payload, "tipo_prestazione_id"),
                priorita_id=v.require_positive_int(payload, "priorita_id"),
                descrizione=payload.get("descrizione"),
            )
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ── Righe: la lista configurabile `vendite.preventivo_righe` ──
# Pagina ed export dal factory condiviso `build_lista_figlia_views`
# (brief-db-liste-righe-documento, lotto A). La closure legge il global di
# modulo a call-time: i patch dei test sul service restano validi.
# ⚠️ `GET …/righe/` resta la lettura COMPLETA: la lista e' su `…/righe/lista/`.
_PreventivoRigheLista, _PreventivoRigheListaExport = build_lista_figlia_views(
    schema_prefix="PreventivoRighe",
    operation_id="vendite_preventivi_righe_lista",
    area_funzionale="vendite",
    lista_emittente_param=EMITTENTE_DOCUMENTO_PARAM,
    url_kwarg="preventivo_id",
    model_permission=('vendite', 'preventivo'),
    pagina_call=lambda documento_id, **kw: preventivi_service.list_righe_pagina(documento_id, **kw),
    colonne_ordinabili=PreventiviRepository.righe_colonne_ordinabili(),
    ordine_assente=PreventiviRepository.righe_ordine_di_partenza(),
)


# ⭐ Il cancello di perimetro come LETTERALE nel corpo della classe: e' la
#    forma che `test_perimetro_emittente_copertura` legge (vedi la factory).
class ApiPreventivoRigheListaView(_PreventivoRigheLista):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.preventivo_righe"


class ApiPreventivoRigheListaExportView(_PreventivoRigheListaExport):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.preventivo_righe"
