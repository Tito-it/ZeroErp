# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API del dominio `pagamenti` — le distinte contabili, le loro righe e
#        la registrazione.
# Note: Grammatica URL di `api.md`: il metodo dice l'operazione, il path la
#       risorsa, e il verbo compare SOLO per le azioni di dominio, come ultimo
#       segmento. ⛔ Niente `/distinte/crea/`.
#
#       ⚠️ La risorsa si chiama `distinte` e non `contabili`: sul filo si usa
#       la parola che l'operatore legge sulla schermata.
# ------------------------------------------------------------

from typing import Any
from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    pagina_da_query,
    corpo_oggetto,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_int_strict,
    qp_iso_date_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.openapi_params import parametri_finestra, descrizione_order_by
from apps.core.api.success_responses import success_response
from apps.pagamenti.db.pagamenti_repository import (
    DISTINTA_RIGHE_SORT_COLUMNS,
    DISTINTE_SORT_COLUMNS,
    ECCEDENZE_SORT_COLUMNS,
    ENTI_INCASSO_SORT_COLUMNS,
    RATE_FUORI_CAPIENZA_SORT_COLUMNS,
    RATE_SORT_COLUMNS,
    RIGHE_SORT_COLUMNS,
)
from apps.pagamenti.services import (
    enti_incasso_service,
    pagamenti_service,
    saldi_service,
    sistemazioni_service,
)
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.core.api.openapi_params import param_ricerca_full

AREA = "pagamenti"


# ⭐ `escludi_riga_id` — «prima di se'» — e' LO STESSO parametro sulla rata e
#    sul documento (dal 2026-09-18, P-6): una dichiarazione sola, cosi' la
#    frase che il client legge in OpenAPI non puo' divergere fra i due livelli.
_PARAM_ESCLUDI_RIGA_ID = OpenApiParameter(
    name="escludi_riga_id", type=int, location=OpenApiParameter.QUERY,
    required=False,
    description=(
        "Esclude una riga contabile dal conto: serve a chiedere lo "
        "spazio PRIMA DI SE', cioe' a sapere se quella riga ci sta "
        "senza contarsi addosso."
    ),
)


# Scopo: legge `escludi_riga_id` dalla query string, strict (400 se non numerico).
# ⚠️ Il nome si prende dal parametro dichiarato, non si riscrive: due letterali
#    per la stessa chiave sono il modo in cui OpenAPI e parsing si sfilano.
def _escludi_riga_id(request: Request) -> int | None:
    nome = _PARAM_ESCLUDI_RIGA_ID.name
    return qp_int_optional(request.query_params.get(nome), nome)


# ⭐ `scartate` — l'interruttore «Mostra scartate (N)» delle righe di una
#    distinta (BE-2, D20-c): UNA dichiarazione per la lista e per il suo export,
#    come `escludi_riga_id` sui due livelli del saldo.
# La ricerca libera delle liste (dal 2026-09-23, brief-be-ricerca-full-liste-
# residue §5.3). ⛔ Nessun 400 sotto soglia, rate comprese (brief-db-be-fe-
# ricerca-soglia-per-lista §6 a, Tid 2026-09-26): il termine corto lo ignora il
# BB, sulla soglia del catalogo della lista.
_PARAM_SEARCH = param_ricerca_full()

_PARAM_SCARTATE = OpenApiParameter(
    name="scartate", type=bool, location=OpenApiParameter.QUERY, required=False,
    description=(
        "`1` mostra anche le righe SCARTATA («non e' nostra»). Default: "
        "nascoste — lista ed export insieme — e la risposta dichiara quante "
        "sono in `scartate_count`."
    ),
)


# Scopo: legge `scartate` dalla query string; assente = nascoste.
def _scartate(request: Request) -> bool:
    nome = _PARAM_SCARTATE.name
    return qp_bool_optional(request.query_params.get(nome), nome) is True


# Risposta generica: il contenuto e' documentato per endpoint nel service, e
# gli schemi di dettaglio arriveranno col consolidamento OpenAPI del dominio.
_RISPOSTA_GENERICA = inline_serializer(
    name="PagamentiRispostaGenerica",
    fields={
        "data": serializers.DictField(),
        "meta": serializers.DictField(required=False),
    },
)


# ══════════════════════════════════════════════════════════════════
#  Distinte
# ══════════════════════════════════════════════════════════════════


class ApiDistinteList(DomainAPIView):
    """GET/POST /api/v1/pagamenti/distinte/ — elenco e apertura."""

    area_funzionale = AREA
    is_search_endpoint = True
    # ✅ Dichiarabile dal 2026-08-27: il codice e' a catalogo (lotto 9, seed di
    # `ui.lista_definizione`). Prima non si poteva, ed e' il verso in cui vale
    # la pena ricordarlo: il cancello di perimetro emittente risolve il codice a
    # catalogo e, non trovandolo, rifiuta la lista a un utente MULTI-emittente —
    # cioe' dichiararlo troppo presto spegneva la schermata invece di prepararla.
    # ⚠️ La lista nasce `multi_emittente = f` (default: non certificata): chi ha
    # piu' di un emittente deve sceglierne uno prima di entrare.
    lista_codice = "pagamenti.distinte"

    @extend_schema(
        operation_id="pagamenti_distinte_list",
        parameters=[
            _PARAM_SEARCH,
            OpenApiParameter(
                name="stato", type=str, location=OpenApiParameter.QUERY, required=False,
                description=(
                    "Filtro stato (codice interno): BOZZA | IMPORTATA | VALIDATA | "
                    "CHIUSA | ANNULLATA."
                ),
            ),
            OpenApiParameter(
                name="origine", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro origine: MANUALE (la digita una persona) | GENERATA "
                    "(la scrive il giro dei fondi fattura) | AUTOMATICA (import). "
                    "⭐ Non e' un dettaglio tecnico: dice a chi guarda se sta "
                    "vedendo il lavoro di qualcuno o la contabilita' interna."
                ),
            ),
            OpenApiParameter(
                name="centro_riscossione_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro centro di riscossione.",
            ),
            OpenApiParameter(
                name="ente_incasso_id", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Filtro canale di incasso.",
            ),
            OpenApiParameter(
                name="data_da", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description="Data contabile da (ISO). Il floor standard delle liste lo applica il frontend.",
            ),
            OpenApiParameter(
                name="data_a", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data contabile a (ISO).",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=descrizione_order_by(
                    DISTINTE_SORT_COLUMNS, "Senza: data_contabile.",
                ),
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc (default desc).",
            ),
            *parametri_finestra(),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET l'elenco paginato delle distinte contabili.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        limit, offset = pagina_da_query(qp)
        data = pagamenti_service.list_distinte(
            stato=qp_str_upper(qp.get("stato")),
            origine=qp_str_upper(qp.get("origine")),
            centro_riscossione_id=qp_int_optional(
                qp.get("centro_riscossione_id"), "centro_riscossione_id"
            ),
            ente_incasso_id=qp_int_optional(qp.get("ente_incasso_id"), "ente_incasso_id"),
            data_da=qp_iso_date_optional(qp.get("data_da"), "data_da"),
            data_a=qp_iso_date_optional(qp.get("data_a"), "data_a"),
            search=qp_str(qp.get("search")),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            limit=limit,
            offset=offset,
        )
        return success_response(data)

    @extend_schema(
        operation_id="pagamenti_distinte_create",
        request=inline_serializer(
            name="PagamentiDistintaCreate",
            fields={
                "centro_riscossione_id": serializers.IntegerField(),
                "data_contabile": serializers.DateField(),
                "ente_incasso_id": serializers.IntegerField(required=False),
                # Facoltativo: senza, lo risolve il DB dal canale o dalla
                # sessione; se non puo', 400 `E_CONTABILE_EMITTENTE_OBBLIGATORIO`.
                "emittente_fiscale_id": serializers.IntegerField(required=False),
                "importo_dichiarato": serializers.DecimalField(
                    max_digits=18, decimal_places=2, required=False
                ),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Apre (o ritrova) via POST la distinta manuale dell'operatore.
    # ⚠️ La risposta porta `gia_popolata`: il *get or create* puo' aver
    #    restituito la distinta di stamattina, e la schermata deve dirlo —
    #    entrarci in silenzio e' il modo in cui si registra due volte credendo
    #    di cominciare.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return pagamenti_service.crea_distinta(dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiDistintaDetail(DomainAPIView):
    """GET/PATCH /api/v1/pagamenti/distinte/<id>/ — dettaglio e compilazione."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_distinta_detail",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET testata, totali derivati e i due cataloghi di
    #        stato in un round-trip solo. ⚠️ Le righe NO (dal 2026-09-18):
    #        hanno la loro lista paginata in `righe/`.
    def get(self, request: Request, contabile_id: int) -> JsonResponse:
        return success_response(pagamenti_service.get_distinta(contabile_id))

    @extend_schema(
        operation_id="pagamenti_distinta_update",
        request=inline_serializer(
            name="PagamentiDistintaPatch",
            fields={
                "data_contabile": serializers.DateField(required=False),
                "ente_incasso_id": serializers.IntegerField(required=False),
                "importo_dichiarato": serializers.DecimalField(
                    max_digits=18, decimal_places=2, required=False
                ),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Aggiorna via PATCH i campi che una persona compila.
    # ⛔ Lo stato non passa di qui: e' un'azione, e ha il suo endpoint.
    def patch(self, request: Request, contabile_id: int) -> JsonResponse:
        return success_response(
            pagamenti_service.aggiorna_distinta(contabile_id, corpo_oggetto(request))
        )


class ApiDistintaStato(DomainAPIView):
    """POST /api/v1/pagamenti/distinte/<id>/stato/ — il percorso della distinta."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_distinta_stato",
        request=inline_serializer(
            name="PagamentiDistintaStato",
            fields={"nuovo_stato": serializers.CharField()},
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Chiede via POST un cambio di stato sulla testata.
    # ⛔ `CHIUSA` non e' fra i valori ammessi: la chiusura e' una CONSEGUENZA
    #    del registrare, non un gesto a parte.
    def post(self, request: Request, contabile_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return pagamenti_service.cambia_stato_distinta(contabile_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ══════════════════════════════════════════════════════════════════
#  Righe
# ══════════════════════════════════════════════════════════════════


# I parametri di lista delle righe di una distinta, dichiarati UNA volta: la
# lista e il suo export accettano lo stesso ordinamento, e due elenchi OpenAPI
# scritti a mano sono il modo in cui i due si sfilano (stessa ragione di
# `_PARAM_ESCLUDI_RIGA_ID`).
_PARAMS_ORDINAMENTO_DISTINTA_RIGHE = [
    OpenApiParameter(
        name="order_by", type=str, location=OpenApiParameter.QUERY, required=False,
        description=descrizione_order_by(
            DISTINTA_RIGHE_SORT_COLUMNS,
            "Senza: id DESC (l'ultima riga digitata in cima). "
            "`fattura_numero_documento` ordina per la coppia (numero, serie).",
        ),
    ),
    OpenApiParameter(
        name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False,
        description="asc | desc (le colonne data partono DESC).",
    ),
]


class ApiDistintaRighe(DomainAPIView):
    """GET/POST /api/v1/pagamenti/distinte/<id>/righe/ — le righe della distinta."""

    area_funzionale = AREA
    is_search_endpoint = True
    # ⭐ Lista configurabile dal 2026-09-18 (`pagamenti.distinta_righe`, id 69):
    #    il cancello di perimetro emittente vale come su ogni altra lista.
    lista_codice = "pagamenti.distinta_righe"

    @extend_schema(
        operation_id="pagamenti_distinta_righe_list",
        parameters=[
            _PARAM_SEARCH,
            *_PARAMS_ORDINAMENTO_DISTINTA_RIGHE,
            _PARAM_SCARTATE,
            OpenApiParameter(
                name="limit", type=int, location=OpenApiParameter.QUERY, required=False,
                description=f"Righe per pagina (default {DEFAULT_LIMIT}, max {MAX_LIMIT}).",
            ),
            OpenApiParameter(
                name="offset", type=int, location=OpenApiParameter.QUERY, required=False,
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET le righe attive della distinta, paginate.
    # ⚠️ PAGINATA dal 2026-09-18 (decisione di Tid), come ogni lista
    #    configurabile: bundle standard `parse_list_params` per `limit`/`offset`.
    # ⛔ `order_by` GREZZO e non dal bundle: il suo default (`"descrizione"`)
    #    qui non e' una colonna. `order_dir` dal bundle: assente = `None`, e
    #    decide il default del repository (`id DESC`, le date DESC).
    def get(self, request: Request, contabile_id: int) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(
            pagamenti_service.list_righe(
                contabile_id,
                search=qp_str(qp.get("search")),
                limit=p["limit"],
                offset=p["offset"],
                order_by=qp_str(qp.get("order_by")),
                order_dir=p["order_dir"],
                scartate=_scartate(request),
            )
        )

    @extend_schema(
        operation_id="pagamenti_distinta_righe_create",
        request=inline_serializer(
            name="PagamentiRigaCreate",
            fields={
                "importo": serializers.DecimalField(max_digits=18, decimal_places=2),
                "riferimento_ente": serializers.CharField(required=False),
                "data_pagamento": serializers.DateField(required=False),
                "data_valuta": serializers.DateField(required=False),
                "data_operazione": serializers.DateField(required=False),
                "motivo_sospeso": serializers.CharField(required=False),
                "meta": serializers.DictField(required=False),
                # ⭐ D16: la destinazione viaggia coi fatti. Con `fattura_id` la
                #    riga nasce ABBINATA; senza, DA_ABBINARE (l'eccezione
                #    dichiarata). `billing_account_id` assente = quello della
                #    fattura. La forzatura e' il SECONDO tempo della capienza.
                "fattura_id": serializers.IntegerField(required=False),
                "billing_account_id": serializers.IntegerField(required=False),
                "scadenza_id": serializers.IntegerField(required=False),
                "forzata": serializers.BooleanField(required=False),
                "motivo_forzatura": serializers.CharField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Aggiunge via POST una riga — un importo arrivato, e di chi e'.
    # ⭐ Con la fattura nasce `ABBINATA` in un INSERT solo (D16); senza nasce
    #    `DA_ABBINARE`, che sulla manuale e' l'eccezione che l'operatore
    #    dichiara, non il default.
    def post(self, request: Request, contabile_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return pagamenti_service.crea_riga(contabile_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiDistintaRigheExport(DomainAPIView):
    """GET /api/v1/pagamenti/distinte/<id>/righe/export/ — CSV/XLSX delle righe."""

    area_funzionale = AREA
    # ⭐ LO STESSO `lista_codice` della lista a video, letto da lei e non
    #    ricopiato: le colonne del file sono quelle che l'operatore VEDE
    #    (preferenza + preset + permessi), e il cancello di perimetro vale anche
    #    sulla porta piu' larga (`base_views.lista_codice`). Due letterali
    #    uguali divergono al primo rename, e l'export scaricherebbe le colonne
    #    di un'altra lista senza nessun errore.
    lista_codice = ApiDistintaRighe.lista_codice

    @extend_schema(
        operation_id="pagamenti_distinta_righe_export",
        parameters=[
            _PARAM_SEARCH,
            OpenApiParameter(
                name="formato", type=str, location=OpenApiParameter.QUERY,
                required=True, description="csv | xlsx.",
            ),
            *_PARAMS_ORDINAMENTO_DISTINTA_RIGHE,
            _PARAM_SCARTATE,
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Il file delle righe di UNA distinta — «la contabile in CSV/Excel».
    # ⚠️ `limit=EXPORT_MAX_ROWS + 1` e non la pagina a video: l'export esporta
    #    il DATASET, non la pagina. Il `+1` serve al guard di
    #    `build_export_response`, che rifiuta PRIMA di serializzare invece di
    #    consegnare un file troncato in silenzio.
    # ⚠️ `?formato=`, non `?format=`: quest'ultimo e' un parametro magico di DRF
    #    e collide col content negotiation (`feedback_drf_format_magic_param`).
    def get(self, request: Request, contabile_id: int) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        scartate = _scartate(request)
        dati = pagamenti_service.list_righe(
            contabile_id,
            search=qp_str(qp.get("search")),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            scartate=scartate,
        )
        return build_export_response(
            request,
            lista_codice=self.lista_codice,
            results=dati["results"],
            total=dati["count"],
            # ⭐ L'UNICO filtro della lista e' l'interruttore delle scartate, e si
            #    dichiara nel file solo quando e' acceso: la distinta e' nel path,
            #    non e' una scelta dell'operatore.
            filtri_applicati={"scartate": True} if scartate else None,
            fmt=fmt,
        )


class ApiDistintaRigheDaRate(DomainAPIView):
    """POST /api/v1/pagamenti/distinte/<id>/righe/da-rate/ — N rate scelte, N righe."""

    # Stesso gate di `POST righe/` (`add` d'area): e' la stessa nascita, in
    # elenco. ⚠️ Verbo di COLLEZIONE sulle righe della distinta: le righe nate
    # dalle rate scelte — un nome che dice COSA, non come (api.md).
    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_distinta_righe_da_rate",
        request=inline_serializer(
            name="PagamentiRigheDaRate",
            fields={
                # I fatti COMUNI, uguali per tutte le righe del giro.
                "riferimento_ente": serializers.CharField(required=False),
                "data_pagamento": serializers.DateField(required=False),
                "data_valuta": serializers.DateField(required=False),
                "data_operazione": serializers.DateField(required=False),
                "meta": serializers.DictField(required=False),
                # Per riga: la rata, il suo importo e il secondo tempo.
                "righe": serializers.ListField(
                    child=inline_serializer(
                        name="PagamentiRigaDaRata",
                        fields={
                            "scadenza_id": serializers.IntegerField(),
                            "importo": serializers.DecimalField(
                                max_digits=18, decimal_places=2
                            ),
                            "forzata": serializers.BooleanField(required=False),
                            "motivo_forzatura": serializers.CharField(required=False),
                        },
                    ),
                ),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Crea via POST una riga per ogni rata scelta, con esito PER RIGA.
    # ⚠️ Lo status e' 200 anche su `PARZIALE`/`ERRORE`: chi legge guarda `esito`
    #    e `falliti[]`, ciascuno col suo errore intero (`ui_action` compresa).
    def post(self, request: Request, contabile_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return pagamenti_service.crea_righe_da_rate(contabile_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRigaDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/pagamenti/righe/<id>/ — i fatti della riga, e la sua eliminazione."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_riga_update",
        request=inline_serializer(
            name="PagamentiRigaPatch",
            fields={
                "importo": serializers.DecimalField(
                    max_digits=18, decimal_places=2, required=False
                ),
                "riferimento_ente": serializers.CharField(required=False),
                "data_pagamento": serializers.DateField(required=False),
                "data_valuta": serializers.DateField(required=False),
                "data_operazione": serializers.DateField(required=False),
                "motivo_sospeso": serializers.CharField(required=False),
                "meta": serializers.DictField(required=False),
                # ⭐ Il SECONDO TEMPO della capienza, anche in modifica (Tid,
                #    2026-09-15): un importo corretto oltre il residuo della
                #    rata prende il 409 confermabile, e qui si conferma.
                "forzata": serializers.BooleanField(required=False),
                "motivo_forzatura": serializers.CharField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Aggiorna via PATCH i FATTI di una riga (com'e' arrivato il denaro)
    #        e, se il guard della rata ha chiesto conferma, la forzatura.
    # ⛔ Non l'abbinamento: quello e' un verbo, perche' porta con se' la rata,
    #    e perche' e' una decisione — non la correzione di un dato digitato
    #    male.
    def patch(self, request: Request, riga_id: int) -> JsonResponse:
        return success_response(
            pagamenti_service.aggiorna_riga(riga_id, corpo_oggetto(request))
        )

    @extend_schema(
        operation_id="pagamenti_riga_delete",
        responses={200: inline_serializer(
            name="PagamentiRigaDelete",
            fields={
                "riga_id": serializers.IntegerField(),
                "eliminata": serializers.BooleanField(),
            },
        )},
    )
    # Scopo: Elimina via DELETE una riga di una distinta manuale in bozza
    #        (`attivo = false`, D17). Il metodo dice il verbo; i motivi per cui
    #        non si puo' li da' il database (409 `E_RIGA_CONTABILE_DISTINTA_*`).
    # ⚠️ `handle_post_json` e non una chiamata diretta: e' la sede unica del
    #    controllo `Idempotency-Key` e del replay in strong mode. Il corpo di un
    #    DELETE e' vuoto, e il payload viene ignorato di proposito — quello che
    #    serve e' nel path (stessa forma di `DELETE /vendite/fondi-fattura/{id}/`).
    def delete(self, request: Request, riga_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda _payload: pagamenti_service.elimina_riga(riga_id),
            require_idempotency_key=True,
        )


class ApiRigaStato(DomainAPIView):
    """POST /api/v1/pagamenti/righe/<id>/stato/ — il percorso della riga."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_riga_stato",
        request=inline_serializer(
            name="PagamentiRigaStato",
            fields={
                "nuovo_stato": serializers.CharField(),
                "motivo_sospeso": serializers.CharField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Chiede via POST un cambio di stato sulla riga.
    # ⚠️ Il motivo viaggia nello stesso giro della sospensione: sospendere
    #    senza dire perche' lascia la riga in una coda dove il prossimo che la
    #    guarda non sa che cosa si era gia' capito.
    def post(self, request: Request, riga_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return pagamenti_service.cambia_stato_riga(riga_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ══════════════════════════════════════════════════════════════════
#  Registrazione
# ══════════════════════════════════════════════════════════════════


class ApiDistintaAnteprimaRegistrazione(DomainAPIView):
    """GET /api/v1/pagamenti/distinte/<id>/anteprima-registrazione/."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_distinta_anteprima_registrazione",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: La fotografia di che cosa succede se si registra adesso.
    # ⭐ I due numeri di questa risposta (`righe_registrabili`,
    #    `totale_registrabile`) sono quelli da rimandare indietro come
    #    dichiarazione: e' cosi' che il database verifica di registrare
    #    esattamente cio' che l'operatore ha approvato.
    def get(self, request: Request, contabile_id: int) -> JsonResponse:
        return success_response(pagamenti_service.anteprima_registrazione(contabile_id))


class ApiDistintaRegistra(DomainAPIView):
    """POST /api/v1/pagamenti/distinte/<id>/registra/ — il gesto irreversibile."""

    area_funzionale = AREA
    # 🔴 Il cancello sull'unico gesto di questo dominio che non si puo' disfare.
    # ⚠️ L'azione `registra_distinta` va seminata a catalogo e ASSEGNATA a un
    #    profilo: finche' non lo e', `fn_check_azione_processo` risponde
    #    `false` per tutti tranne i super admin — fail-closed, che e' il verso
    #    giusto in cui sbagliare su un gesto irreversibile.
    post_permission = "registra_distinta"

    @extend_schema(
        operation_id="pagamenti_distinta_registra",
        request=inline_serializer(
            name="PagamentiDistintaRegistra",
            fields={
                "righe_attese": serializers.IntegerField(required=False),
                "totale_atteso": serializers.DecimalField(
                    max_digits=18, decimal_places=2, required=False
                ),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Registra la distinta — una sola `SELECT` sulla funzione madre.
    # ⛔ L'esito risale INTATTO: `NULLA_DA_POSTARE` non e' un errore, e il
    #    backend non lo trasforma in uno. La frase la sceglie il frontend.
    def post(self, request: Request, contabile_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return dict(
                pagamenti_service.registra_distinta(contabile_id, dict(payload))
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiDistintaCorreggi(DomainAPIView):
    """POST /api/v1/pagamenti/distinte/<id>/correggi/ — la correzione guidata."""

    area_funzionale = AREA
    # 🔴 Lo stesso cancello della registrazione, e per la stessa ragione: la
    #    correzione nasce dal registrato e produrra' movimenti di segno opposto
    #    quando qualcuno la registrera'. ⛔ Un gesto che rovescia del denaro non
    #    puo' avere una porta piu' larga di quello che lo ha scritto.
    post_permission = "registra_distinta"

    @extend_schema(
        operation_id="pagamenti_distinta_correggi",
        request=inline_serializer(
            name="PagamentiDistintaCorreggi",
            fields={
                "data_contabile": serializers.DateField(required=False),
                "motivo": serializers.CharField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Apre via POST una distinta NUOVA con le righe di segno opposto gia'
    #        compilate — una sola `SELECT` sulla funzione madre.
    # ⭐ Le righe nascono con fattura e rata gia' scritte ma in `DA_ABBINARE`
    #    (decisione C-1, misurata dal team DB il 28/08): nascerle gia' abbinate
    #    avrebbe richiesto di scrivere `forzata = true` al posto dell'operatore,
    #    perche' su una rata saldata dal movimento che si sta correggendo non
    #    c'e' capienza in nessuna direzione. La correzione guida tutto tranne
    #    l'ultimo clic, e il doppio tempo resta il gesto di una persona.
    # ⛔ `NULLA_DA_CORREGGERE` risale INTATTO: e' un esito, non un errore.
    # ⛔ E non si chiama «storno»: `STORNATA` e' fuori dal catalogo dal 21/08.
    def post(self, request: Request, contabile_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return pagamenti_service.correggi_distinta(contabile_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ══════════════════════════════════════════════════════════════════
#  Abbinamento, code e saldi (slice 3)
# ══════════════════════════════════════════════════════════════════


class ApiRigaAbbina(DomainAPIView):
    """POST /api/v1/pagamenti/righe/<id>/abbina/ — il denaro trova il suo posto."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_riga_abbina",
        request=inline_serializer(
            name="PagamentiRigaAbbina",
            fields={
                "fattura_id": serializers.IntegerField(),
                "billing_account_id": serializers.IntegerField(),
                "scadenza_id": serializers.IntegerField(required=False),
                "forzata": serializers.BooleanField(required=False),
                "motivo_forzatura": serializers.CharField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Imputa via POST una riga a una fattura, e quando c'e' a una rata.
    # 🔴 Il DOPPIO TEMPO della capienza passa di qui: il primo tentativo arriva
    #    senza `forzata`, il database rifiuta con `E_RIGA_CONTABILE_CAPIENZA_SUPERATA`
    #    (409) e un messaggio che porta gia' i numeri, e la conferma
    #    dell'operatore torna con `forzata = true`. ⚠️ Il frontend riconosce quel
    #    rifiuto dall'`ui_action` `confirm_and_retry`, non da un elenco di
    #    codici cablato.
    def post(self, request: Request, riga_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return pagamenti_service.abbina_riga(riga_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRigaRegistra(DomainAPIView):
    """POST /api/v1/pagamenti/righe/<id>/registra/ — la registrazione tardiva."""

    area_funzionale = AREA
    # 🔴 LO STESSO CANCELLO DELLA REGISTRAZIONE (`registra_distinta`), e per la
    #    stessa ragione: questo verbo scrive un movimento — rovescia denaro — e
    #    non puo' avere una porta piu' larga di quella che chiude la distinta.
    post_permission = "registra_distinta"

    @extend_schema(
        operation_id="pagamenti_riga_registra",
        request=inline_serializer(
            name="PagamentiRigaRegistra",
            fields={
                "fattura_id": serializers.IntegerField(),
                "billing_account_id": serializers.IntegerField(required=False),
                "scadenza_id": serializers.IntegerField(required=False),
                "forzata": serializers.BooleanField(required=False),
                "motivo_forzatura": serializers.CharField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Abbina E registra via POST una riga `SOSPESA` sotto una distinta
    #        gia' registrata (D20-b): una sola `SELECT` sulla madre
    #        `fn_posta_riga_tardiva`. Movimento scritto, riga `POSTATA`,
    #        distinta che resta `CHIUSA`.
    # ⚠️ Il payload e' quello di `abbina` — e' lo stesso gesto, con la
    #    registrazione dentro. Il doppio tempo della capienza passa intatto:
    #    409 `confirm_and_retry`, poi `forzata = true`.
    # ⛔ Non un esito «nulla da postare»: una tardiva che non si puo' fare e' un
    #    rifiuto (`E_RIGA_CONTABILE_TARDIVA_*`, 409) con la sua frase.
    def post(self, request: Request, riga_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return pagamenti_service.registra_riga_tardiva(riga_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRigheCoda(DomainAPIView):
    """GET /api/v1/pagamenti/righe/ — la coda del riconciliatore."""

    area_funzionale = AREA
    is_search_endpoint = True
    # ⭐ Una definizione sola per DUE porte (Q-4 → c): «da abbinare» e «sospese»
    # sono la stessa lista col filtro `coda` gia' impostato, quindi condividono
    # la configurazione di colonne — che e' il motivo per cui il seed e' uno.
    lista_codice = "pagamenti.righe"

    @extend_schema(
        operation_id="pagamenti_righe_coda",
        parameters=[
            _PARAM_SEARCH,
            OpenApiParameter(
                name="coda", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Quale coda: DA_ABBINARE (lavoro non ancora fatto) | "
                    "SOSPESE (lavoro fatto che ha trovato un ostacolo) | TUTTE. "
                    "⭐ Sono due mestieri diversi e due voci di menu, ma la "
                    "stessa lista con il filtro gia' impostato."
                ),
            ),
            OpenApiParameter(
                name="billing_account_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro cliente.",
            ),
            OpenApiParameter(
                name="data_da", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data contabile della distinta, da (ISO).",
            ),
            OpenApiParameter(
                name="data_a", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data contabile della distinta, a (ISO).",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=descrizione_order_by(
                    RIGHE_SORT_COLUMNS, "Senza: data_pagamento.",
                ),
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc (default desc).",
            ),
            *parametri_finestra(),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET le righe da lavorare, di tutte le distinte.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        limit, offset = pagina_da_query(qp)
        data = pagamenti_service.list_coda_righe(
            coda=qp_str_upper(qp.get("coda")),
            billing_account_id=qp_int_optional(
                qp.get("billing_account_id"), "billing_account_id"
            ),
            data_da=qp_iso_date_optional(qp.get("data_da"), "data_da"),
            data_a=qp_iso_date_optional(qp.get("data_a"), "data_a"),
            search=qp_str(qp.get("search")),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiRateList(DomainAPIView):
    """GET /api/v1/pagamenti/rate/ — l'elenco delle rate col saldo, la sorgente del picker."""

    area_funzionale = AREA
    is_search_endpoint = True
    # ⭐ La lista `pagamenti.rate` (id 68): nasce per il picker della distinta
    #    (D19-c) ed e' la rotta che lo scadenzario riusera' (brief madre §3.4).
    # ⛔ Niente `skip_area_check`: la consumano schermate di `pagamenti` — a
    #    differenza delle quattro `fatture/<id>/…`, che servono il drawer
    #    fattura di `vendite`.
    lista_codice = "pagamenti.rate"

    @extend_schema(
        operation_id="pagamenti_rate_list",
        parameters=[
            OpenApiParameter(
                name="billing_account_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Il cliente: uno dei due criteri del picker.",
            ),
            OpenApiParameter(
                name="fattura_numero", type=int, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Il numero del documento, confronto ESATTO (101 non porta "
                    "1010): l'altro criterio del picker. `serie` e `anno` "
                    "facoltativi per disambiguare."
                ),
            ),
            OpenApiParameter(
                name="serie", type=str, location=OpenApiParameter.QUERY, required=False,
            ),
            OpenApiParameter(
                name="anno", type=int, location=OpenApiParameter.QUERY, required=False,
            ),
            # ⭐ Dal 2026-09-24 sul BB: le colonne le dice il catalogo (anche il
            #    numero documento), e la soglia vera e' il 400 del service (§6).
            #    ⚠️ Non confonderla con `fattura_numero`, il filtro ESATTO.
            _PARAM_SEARCH,
            OpenApiParameter(
                name="solo_aperte", type=bool, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Solo le rate con residuo diverso da zero (Q-B): il filtro "
                    "sta nel WHERE e chiede il saldo di tutto il perimetro."
                ),
            ),
            OpenApiParameter(
                name="solo_numerate", type=bool, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Solo le rate di documenti NUMERATI (`numero IS NOT NULL`): "
                    "la bozza non e' un documento fiscale. **Default: true** — "
                    "e' un perimetro di dominio, non un filtro: assente vale "
                    "`true`, e per vedere anche le bozze si passa "
                    "`solo_numerate=false`. Vale anche sul perimetro di "
                    "`solo_aperte`."
                ),
            ),
            OpenApiParameter(
                name="data_scadenza_da", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Scadenza da (ISO).",
            ),
            OpenApiParameter(
                name="data_scadenza_a", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Scadenza a (ISO).",
            ),
            OpenApiParameter(
                name="natura_doc_codice", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description="Natura del documento (codice interno), per lo scadenzario.",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=descrizione_order_by(
                    RATE_SORT_COLUMNS,
                    "Senza: data_scadenza ASC (e' una coda). I tre saldi non ordinano: "
                    "arrivano dal nucleo DOPO la pagina.",
                ),
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc.",
            ),
            OpenApiParameter(
                name="limit", type=int, location=OpenApiParameter.QUERY, required=False,
                description=f"Righe per pagina (default {DEFAULT_LIMIT}, max {MAX_LIMIT}).",
            ),
            OpenApiParameter(
                name="offset", type=int, location=OpenApiParameter.QUERY, required=False,
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET le rate del perimetro, ciascuna col suo saldo.
    # ⚠️ `order_dir` GREZZO e non `p["order_dir"]`: il bundle lo normalizza ad
    #    `asc`, e sulle colonne data il verso naturale (DESC) non arriverebbe
    #    mai (api.md §parse_list_params).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        data = saldi_service.list_rate(
            auth_user_id=get_scope_user_id(request),
            billing_account_id=qp_int_optional(
                qp.get("billing_account_id"), "billing_account_id"
            ),
            fattura_numero=qp_int_optional(qp.get("fattura_numero"), "fattura_numero"),
            serie=qp_str(qp.get("serie")),
            anno=qp_int_optional(qp.get("anno"), "anno"),
            search=qp_str(qp.get("search")),
            solo_aperte=qp_bool_optional(qp.get("solo_aperte"), "solo_aperte"),
            solo_numerate=qp_bool_optional(qp.get("solo_numerate"), "solo_numerate"),
            data_scadenza_da=qp_iso_date_optional(
                qp.get("data_scadenza_da"), "data_scadenza_da"
            ),
            data_scadenza_a=qp_iso_date_optional(
                qp.get("data_scadenza_a"), "data_scadenza_a"
            ),
            # Il maiuscolo lo mette il service (una sede, provata dal suo test).
            natura_doc_codice=qp_str(qp.get("natura_doc_codice")),
            limit=p["limit"],
            offset=p["offset"],
            order_by=qp_str(qp.get("order_by")),
            order_dir=p["order_dir"],
        )
        return success_response(data)


class ApiRateFuoriCapienza(DomainAPIView):
    """GET /api/v1/pagamenti/rate/fuori-capienza/ — l'elenco che rende onesta la forzatura."""

    area_funzionale = AREA
    is_search_endpoint = True
    lista_codice = "pagamenti.rate_fuori_capienza"

    @extend_schema(
        operation_id="pagamenti_rate_fuori_capienza",
        parameters=[
            _PARAM_SEARCH,
            OpenApiParameter(
                name="motivo", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "SOVRA_INCASSATA (e' entrato piu' del dovuto) | "
                    "MOVIMENTO_CONTRARIO (un rimborso dove non era entrato "
                    "niente). ⭐ Sono due popolazioni diverse in un elenco solo, "
                    "e il motivo e' la prima colonna da guardare. "
                    "Motivo fuori vocabolario -> 400."
                ),
            ),
            OpenApiParameter(
                name="billing_account_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro cliente.",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=descrizione_order_by(
                    RATE_FUORI_CAPIENZA_SORT_COLUMNS, "Senza: data_scadenza.",
                ),
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc (default desc).",
            ),
            *parametri_finestra(),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET le rate uscite dalla banda di capienza.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        limit, offset = pagina_da_query(qp)
        data = pagamenti_service.list_rate_fuori_capienza(
            motivo=qp_str_upper(qp.get("motivo")),
            billing_account_id=qp_int_optional(
                qp.get("billing_account_id"), "billing_account_id"
            ),
            search=qp_str(qp.get("search")),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiRataSaldo(DomainAPIView):
    """GET /api/v1/pagamenti/rate/<id>/saldo/ — i tre numeri di una rata."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_rata_saldo",
        parameters=[_PARAM_ESCLUDI_RIGA_ID],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET residuo, in lavorazione e incassato di una rata.
    def get(self, request: Request, scadenza_id: int) -> JsonResponse:
        return success_response(
            saldi_service.saldo_rata(
                scadenza_id, escludi_riga_id=_escludi_riga_id(request),
            )
        )


class ApiFatturaSaldo(DomainAPIView):
    """GET /api/v1/pagamenti/fatture/<id>/saldo/ — il saldo di un documento."""

    # ⭐ Lo consuma il drawer FATTURA, che vive in `vendite`: senza questo, per
    #    vedere se una fattura e' pagata servirebbe la LETTURA su `pagamenti` —
    #    cioe' allargare un permesso per comodita'. E' lo stesso pattern del
    #    lookup cross-dominio: risponde il MINIMO su un documento gia' scelto.
    # ⚠️ E sta qui e non in `vendite` per un vincolo, non per gusto: le chiamate
    #    laterali fra moduli di pari livello non sono ammesse (api.md), quindi
    #    `vendite` non puo' chiedere un saldo a `pagamenti`.
    # ⛔ E NON dichiara `area_funzionale`, ed e' la riga che conta: la catena
    #    legge lo skip SOLO se l'area non si risolve. Fino al 2026-09-12 queste
    #    quattro view dichiaravano anche `area_funzionale = AREA`, e lo skip era
    #    MUTO — la LETTURA su `pagamenti` serviva davvero, e il commento qui
    #    sopra prometteva un comportamento che il codice non aveva. Decisione
    #    di Tid (2026-09-12): vale lo skip. Presidiato da
    #    `core/tests/test_skip_area_check_registro.py`.
    skip_area_check = True

    @extend_schema(
        operation_id="pagamenti_fattura_saldo",
        parameters=[_PARAM_ESCLUDI_RIGA_ID],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET residuo, in lavorazione e incassato di una fattura.
    # ⭐ Tutti e tre dal 2026-08-29 (DB-10 atterrata il 25/08): fino ad allora
    #    `incassato` era `null`. ⛔ Resta il divieto: NON si somma dalle rate (una
    #    riga puo' avere fattura senza rata: il fondo fattura e' cosi').
    # ⭐ `escludi_riga_id` dal 2026-09-18 (P-6): lo stesso «prima di se'» della
    #    rata — la riga SENZA rata che si sta correggendo non si conta piu'
    #    addosso, e il pannello smette di dichiarare che non sa escluderla.
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        return success_response(
            saldi_service.saldo_documento(
                fattura_id, escludi_riga_id=_escludi_riga_id(request),
            )
        )


class ApiFatturaRateSaldo(DomainAPIView):
    """GET /api/v1/pagamenti/fatture/<id>/rate/ — le rate con il loro saldo."""

    # Stessa ragione del saldo documento: lo consuma il form dell'abbinamento,
    # e risponde il minimo su una fattura gia' scelta.
    skip_area_check = True

    @extend_schema(
        operation_id="pagamenti_fattura_rate",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET le rate di una fattura, ciascuna col suo saldo.
    # ⭐ Un giro solo e non uno per rata: il form le mostra tutte insieme, e N
    #    chiamate per disegnare un menu sono N modi di essere lenti.
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        return success_response(saldi_service.saldi_rate_documento(fattura_id))


# ══════════════════════════════════════════════════════════════════
#  Le sistemazioni — che cosa si fa del denaro di troppo (slice 5)
# ══════════════════════════════════════════════════════════════════


class ApiEccedenze(DomainAPIView):
    """GET /api/v1/pagamenti/eccedenze/ — i documenti che hanno incassato più del dovuto."""

    area_funzionale = AREA
    is_search_endpoint = True
    lista_codice = "pagamenti.eccedenze"

    @extend_schema(
        operation_id="pagamenti_eccedenze",
        parameters=[
            _PARAM_SEARCH,
            OpenApiParameter(
                name="chi_e_in_credito", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "CLIENTE (ha pagato più del dovuto) | AZIENDA (un documento "
                    "a credito su cui è entrato denaro). Valore fuori "
                    "vocabolario -> 400."
                ),
            ),
            OpenApiParameter(
                name="billing_account_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro cliente.",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=descrizione_order_by(
                    ECCEDENZE_SORT_COLUMNS,
                    "Senza: eccedenza_cliente. ⭐ Il default è per CLIENTE, non "
                    "per documento: la decisione si prende guardando il cliente.",
                ),
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc (default desc).",
            ),
            *parametri_finestra(),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET l'elenco delle eccedenze da sistemare.
    # ⭐ La vista porta già il raggruppamento per cliente in finestra
    #    (`eccedenza_cliente`, `documenti_cliente`): il backend non somma niente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        limit, offset = pagina_da_query(qp)
        data = sistemazioni_service.list_eccedenze(
            chi_e_in_credito=qp_str_upper(qp.get("chi_e_in_credito")),
            billing_account_id=qp_int_optional(
                qp.get("billing_account_id"), "billing_account_id"
            ),
            search=qp_str(qp.get("search")),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiSistemazioni(DomainAPIView):
    """POST /api/v1/pagamenti/sistemazioni/ — registra la decisione."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_sistemazione_create",
        request=inline_serializer(
            name="PagamentiSistemazioneCreate",
            fields={
                "fattura_origine_id": serializers.IntegerField(),
                "destinazione": serializers.CharField(),
                "importo": serializers.DecimalField(max_digits=18, decimal_places=2),
                "fattura_destinazione_id": serializers.IntegerField(required=False),
                "motivo": serializers.CharField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Registra via POST che cosa si è deciso di fare di un'eccedenza.
    # ⚠️ **Registrare non è eseguire**: l'atto nasce in bozza e il denaro si
    #    muove alla conferma. Fra i due momenti può arrivare un altro incasso —
    #    ed è la ragione per cui il controllo dell'eccedenza sta là.
    # 🔴 Cliente ed emittente NON si passano: li deriva il backend dalla fattura
    #    di origine, perché non sono una scelta di chi compila.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return sistemazioni_service.crea_sistemazione(dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiSistemazioneDetail(DomainAPIView):
    """GET /api/v1/pagamenti/sistemazioni/<id>/ — il dettaglio dell'atto."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_sistemazione_detail",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET l'atto, col suo esito quando c'è.
    def get(self, request: Request, sistemazione_id: int) -> JsonResponse:
        return success_response(
            sistemazioni_service.get_sistemazione(sistemazione_id)
        )


class ApiFatturaSistemazioni(DomainAPIView):
    """GET /api/v1/pagamenti/fatture/<id>/sistemazioni/ — gli atti su un documento."""

    # ⭐ Cancello di perimetro emittente (2026-09-02, con la conversione della
    #    lista su `<ListaConfigurabile>`): `perimetro_emittente = t` a catalogo
    #    (decisione D-3 del lotto 2), quindi vale l'emittente dell'operatore e
    #    la lista non si assume il compito di dire da quale emittente arriva
    #    ogni riga.
    lista_codice = "pagamenti.sistemazioni_fattura"
    # Stessa ragione del saldo: lo consuma il drawer fattura, che vive in
    # `vendite`, e risponde il minimo su un documento già scelto.
    skip_area_check = True

    @extend_schema(
        operation_id="pagamenti_fattura_sistemazioni",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET gli atti registrati su una fattura.
    # ⭐ Sono più di uno per natura: si può rimborsare una parte e riportare il
    #    resto.
    # ⚠️ PAGINATA dal 2026-09-02, come ogni altra lista configurabile: bundle
    #    standard `parse_list_params` per `limit`/`offset`.
    # ⛔ `order_by` NON viene da `parse_list_params`, e non e' una svista: quel
    #    bundle ha un `order_by` di default (`"descrizione"`) che qui non e'
    #    colonna di niente. `order_dir` dal bundle: assente = `None`, e decide
    #    il default del repository.
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(
            sistemazioni_service.list_sistemazioni_fattura(
                fattura_id,
                limit=p["limit"],
                offset=p["offset"],
                order_by=qp_str(qp.get("order_by")),
                order_dir=p["order_dir"],
            )
        )


class ApiFatturaSistemazioniExport(DomainAPIView):
    """GET /api/v1/pagamenti/fatture/<id>/sistemazioni/export/ — CSV/XLSX."""

    # ⭐ LO STESSO `lista_codice` della lista a video, letto da lei e non
    #    ricopiato (18/09, come `ApiDistintaRigheExport`): le colonne del file
    #    sono quelle che l'operatore VEDE (preferenza + preset + permessi), non
    #    un elenco cablato qui che diverge alla prima colonna aggiunta a
    #    catalogo — e due letterali uguali divergono al primo rename, senza
    #    nessun errore.
    lista_codice = ApiFatturaSistemazioni.lista_codice
    # Stessa ragione della lista: la consuma il drawer dell'eccedenza, che vive
    # in `vendite`.
    skip_area_check = True

    @extend_schema(
        operation_id="pagamenti_fattura_sistemazioni_export",
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Il file degli atti di UNA fattura.
    # ⚠️ `limit=EXPORT_MAX_ROWS + 1` e non la pagina a video: l'export esporta il
    #    DATASET, non la pagina. Il `+1` serve al guard di
    #    `build_export_response`, che rifiuta PRIMA di serializzare invece di
    #    consegnare un file troncato in silenzio.
    # ⚠️ `?formato=`, non `?format=`: quest'ultimo e' un parametro magico di DRF
    #    e collide col content negotiation (`feedback_drf_format_magic_param`).
    def get(self, request: Request, fattura_id: int) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        dati = sistemazioni_service.list_sistemazioni_fattura(
            fattura_id,
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
            # ⛔ Nessun filtro da dichiarare: questa lista non ne ha — la
            #    fattura e' nel path, non e' una scelta dell'operatore. Un
            #    `{"fattura": ...}` scritto qui sarebbe un filtro inventato
            #    nell'intestazione del file.
            filtri_applicati=None,
            fmt=fmt,
        )


class ApiSistemazioneConferma(DomainAPIView):
    """POST /api/v1/pagamenti/sistemazioni/<id>/conferma/ — l'atto diventa un fatto."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_sistemazione_conferma",
        request=inline_serializer(
            name="PagamentiSistemazioneConferma",
            fields={"ente_incasso_id": serializers.IntegerField(required=False)},
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Esegue via POST l'atto: una sola `SELECT` sulla funzione madre, che
    #        sceglie la strada (fondo, distinta negativa, compensazione) e ci
    #        mette sopra il denaro.
    # ⚠️ Il **canale del rimborso** si chiede QUI e non alla registrazione: da
    #    quale conto esce il bonifico è una decisione del momento in cui si paga.
    def post(self, request: Request, sistemazione_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return sistemazioni_service.conferma_sistemazione(
                sistemazione_id, dict(payload)
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiSistemazioneAnnulla(DomainAPIView):
    """POST /api/v1/pagamenti/sistemazioni/<id>/annulla/ — la decisione si scarta."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_sistemazione_annulla",
        request=inline_serializer(
            name="PagamentiSistemazioneAnnulla",
            fields={"motivo": serializers.CharField(required=False)},
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Scarta via POST l'atto, lasciandolo a registro con la sua ragione.
    # ⚠️ Il motivo è obbligatorio se l'atto non ne aveva già uno: lo dice il
    #    guard del database, che sa se ce n'era uno — il backend non lo replica.
    def post(self, request: Request, sistemazione_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return sistemazioni_service.annulla_sistemazione(
                sistemazione_id, dict(payload)
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ══════════════════════════════════════════════════════════════════
#  I canali di incasso — da dove arrivano i soldi (slice 4)
# ══════════════════════════════════════════════════════════════════


class ApiEntiIncasso(DomainAPIView):
    """GET/POST /api/v1/pagamenti/enti-incasso/ — i canali di incasso."""

    area_funzionale = AREA
    # ⭐ Cancello di perimetro emittente: `perimetro_emittente = t` a
    #    catalogo (decisione D-3 del lotto 2, 2026-09-02) — vale
    #    l'emittente dell'operatore, e la lista non si assume il compito
    #    di dire da quale emittente arriva ogni riga.
    lista_codice = "pagamenti.canali_incasso"
    is_search_endpoint = True

    @extend_schema(
        operation_id="pagamenti_enti_incasso_list",
        parameters=[
            OpenApiParameter(
                name="tipo", type=str, location=OpenApiParameter.QUERY, required=False,
                description="BANCA | POSTE | PSP | ALTRO. Fuori vocabolario -> 400.",
            ),
            OpenApiParameter(
                name="centro_riscossione_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro centro di riscossione.",
            ),
            OpenApiParameter(
                name="attivo", type=bool, location=OpenApiParameter.QUERY,
                required=False, description="Filtro attivo/disattivo.",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=descrizione_order_by(
                    ENTI_INCASSO_SORT_COLUMNS, "Senza: codice.",
                ),
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc (default) | desc.",
            ),
            *parametri_finestra(),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET l'elenco dei canali di incasso.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        limit, offset = pagina_da_query(qp)
        data = enti_incasso_service.list_enti_incasso(
            tipo=qp_str_upper(qp.get("tipo")),
            centro_riscossione_id=qp_int_optional(
                qp.get("centro_riscossione_id"), "centro_riscossione_id"
            ),
            attivo=qp_bool_optional(qp.get("attivo"), "attivo"),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            limit=limit,
            offset=offset,
        )
        return success_response(data)

    @extend_schema(
        operation_id="pagamenti_enti_incasso_create",
        request=inline_serializer(
            name="PagamentiEnteIncassoCreate",
            fields={
                "codice": serializers.CharField(),
                "descrizione": serializers.CharField(),
                "tipo": serializers.CharField(),
                "soggetto_ruolo_conto_bancario_id": serializers.IntegerField(),
                "centro_riscossione_id": serializers.IntegerField(required=False),
                "soggetto_ruolo_id": serializers.IntegerField(required=False),
                "bank_branch_id": serializers.IntegerField(required=False),
                "formato_flusso": serializers.CharField(required=False),
                "regole_match": serializers.DictField(required=False),
                "meta": serializers.DictField(required=False),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Crea via POST un canale di incasso.
    # 🔴 Il **conto** è obbligatorio su TUTTI i tipi, non solo su BANCA: un
    #    canale senza conto produrrebbe una coda di denaro che nessuno vede — e
    #    il conto è il punto da cui il database ricava di chi sono i soldi.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return enti_incasso_service.crea_ente_incasso(dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiEnteIncassoDetail(DomainAPIView):
    """GET/PATCH /api/v1/pagamenti/enti-incasso/<id>/ — il canale."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_ente_incasso_detail",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET il canale, col suo conto in chiaro.
    def get(self, request: Request, ente_incasso_id: int) -> JsonResponse:
        return success_response(
            enti_incasso_service.get_ente_incasso(ente_incasso_id)
        )

    @extend_schema(
        operation_id="pagamenti_ente_incasso_update",
        request=inline_serializer(
            name="PagamentiEnteIncassoPatch",
            fields={
                "codice": serializers.CharField(required=False),
                "descrizione": serializers.CharField(required=False),
                "tipo": serializers.CharField(required=False),
                "attivo": serializers.BooleanField(required=False),
                "centro_riscossione_id": serializers.IntegerField(required=False),
                "soggetto_ruolo_id": serializers.IntegerField(required=False),
                "bank_branch_id": serializers.IntegerField(required=False),
                "soggetto_ruolo_conto_bancario_id": serializers.IntegerField(
                    required=False
                ),
                "formato_flusso": serializers.CharField(required=False),
                "regole_match": serializers.DictField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Aggiorna via PATCH i campi del canale.
    # ⛔ `codice_interno` non è aggiornabile: è la chiave stabile con cui il
    #    resto del sistema lo nomina.
    def patch(self, request: Request, ente_incasso_id: int) -> JsonResponse:
        return success_response(
            enti_incasso_service.aggiorna_ente_incasso(
                ente_incasso_id, corpo_oggetto(request)
            )
        )


class ApiContiIncasso(DomainAPIView):
    """GET /api/v1/pagamenti/conti-incasso/ — i conti agganciabili a un canale."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_conti_incasso",
        parameters=[
            OpenApiParameter(
                name="soggetto_ruolo_id", type=int, location=OpenApiParameter.QUERY,
                required=True,
                description="Il soggetto (ruolo) di cui elencare i conti di incasso.",
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET i soli conti con `uso = 'INCASSO'` del soggetto.
    # 🔴 **BE-8**: il database rifiuta gli altri con un errore parlante, ma un
    #    elenco che li propone fa sbagliare — e chi sbaglia se ne accorge dopo
    #    aver compilato tutto il resto.
    # ⚠️ Un elenco VUOTO non è un guasto: quel soggetto non ha ancora un conto
    #    di incasso censito **a livello di ruolo**. La risposta lo dice con
    #    `nessun_conto_di_incasso`, perché un menu vuoto senza spiegazione
    #    sembra un errore dell'applicazione.
    def get(self, request: Request) -> JsonResponse:
        soggetto_ruolo_id = qp_int_strict(
            request.query_params.get("soggetto_ruolo_id"), "soggetto_ruolo_id", 0
        )
        return success_response(
            enti_incasso_service.list_conti_incasso(soggetto_ruolo_id)
        )
