# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API dei TITOLI IVA del soggetto (I7 / D10 di
#        brief-db-be-iva-risolutore-e-regime-cliente).
#        Grammatica di `api.md`: nessun verbo nel path, il metodo HTTP dice
#        l'operazione. Le rotte sono annidate sotto il soggetto perche' il
#        titolo E' del soggetto (D10-bis: proprietario il soggetto, destinatario
#        l'emittente).
#
# ⚠️ Il perimetro emittente lo fa la RLS sulle tre tabelle, non queste view.
#    L'ownership check «il titolo e' di QUESTO soggetto» sta nel service, ed e'
#    un'altra domanda: la RLS dice cosa l'operatore puo' vedere, l'ownership dice
#    che l'id nel path e quello nella riga combaciano.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.anagrafiche.db.titoli_iva_repository import SFONDATI_ORDER_DEFAULT
from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
from apps.core.api.payload_validators import corpo_oggetto, parse_list_params, qp_str
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS

_AREA = "anagrafiche"
# ⚠️ Stesso oggetto di permesso del soggetto: un titolo IVA e' un dato
#    anagrafico del soggetto, non un'entita' con un suo ciclo autorizzativo.
#    Se un giorno servisse piu' fine, e' il tema dei permessi v3 (sotto-oggetti).
_MODEL = ("anagrafiche", "soggetto")


# =================================================================
# Titoli IVA del soggetto — lista + crea
# =================================================================

class SoggettoTitoliIvaView(DomainAPIView):
    """GET lista titoli IVA del soggetto, POST registra un titolo."""
    area_funzionale = _AREA
    # ⭐ Cancello di perimetro emittente: `perimetro_emittente = t` a
    #    catalogo (decisione D-3 del lotto 2, 2026-09-02) — vale
    #    l'emittente dell'operatore, e la lista non si assume il compito
    #    di dire da quale emittente arriva ogni riga.
    lista_codice = "anagrafiche.soggetto_titoli_iva"
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="SoggettoTitoliIvaListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Titoli IVA del soggetto. Ogni riga porta `residuo` (tetto meno
    #        imponibile gia' applicato) e `ambito_incompleto` (Q2).
    # ⚠️ PAGINATA dal 2026-09-02, come ogni altra lista configurabile: bundle
    #    standard `parse_list_params` per `limit`/`offset`/`order_by`.
    # ⭐ `order_dir` dal bundle: assente = `None` (dal 2026-09-26), e decide
    #    il default STORICO del repository (validita' piu' lunga per prima).
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(TitoliIvaService().list_titoli_soggetto(
            soggetto_id,
            limit=p["limit"],
            offset=p["offset"],
            # ⛔ Il grezzo anche per `order_by`, non `p["order_by"]`: il bundle
            #    ha un default suo (`"descrizione"`) che qui non e' una colonna
            #    di niente. Passandolo, l'assenza di ordinamento arriverebbe al
            #    repository come una richiesta — che lui scarta perche' fuori
            #    whitelist, cioe' la cosa giusta per il motivo sbagliato.
            order_by=qp_str(qp.get("order_by")),
            order_dir=p["order_dir"],
        ))

    @extend_schema(
        request=inline_serializer(name="SoggettoTitoloIvaCreateReq", fields={
            "emittente_fiscale_id": serializers.IntegerField(),
            "tipo_titolo_iva_id": serializers.IntegerField(),
            "iva_id": serializers.IntegerField(),
            "ambito": serializers.CharField(required=False),
            "valido_dal": serializers.DateField(),
            "valido_al": serializers.DateField(required=False, allow_null=True),
            "protocollo": serializers.CharField(required=False, allow_null=True),
            "data_ricezione": serializers.DateField(required=False, allow_null=True),
            "riferimento": serializers.CharField(required=False, allow_null=True),
            "plafond": serializers.DecimalField(
                max_digits=18, decimal_places=2, required=False, allow_null=True,
            ),
            "note": serializers.CharField(required=False, allow_null=True),
        }),
        responses={200: inline_serializer(
            name="SoggettoTitoloIvaCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Registra un titolo IVA per il soggetto.
    def post(self, request: Request, soggetto_id: str) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: TitoliIvaService().create_titolo(soggetto_id, p),
        )


# =================================================================
# Tipi di titolo ammessi per il soggetto — lookup del drawer
# =================================================================

class SoggettoTitoliIvaTipiLookupView(DomainAPIView):
    """GET i tipi di titolo IVA che la natura del soggetto ammette."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="SoggettoTitoliIvaTipiLookupResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lookup dedicato (api.md §Lookup, pattern 2): il generico
    #        `config.tipi_titolo_iva` non sa filtrare per la natura del soggetto.
    #        Envelope `{"results": [...]}`, senza paginazione.
    # ⚠️ Solo comodita' del form: un tipo non ammesso lo rifiuta comunque il DB
    #    (brief-db-dati-fiscali-e-societari-del-soggetto, parte D).
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        return success_response(TitoliIvaService().list_tipi_ammessi(soggetto_id))


# =================================================================
# Titolo IVA — dettaglio, aggiorna, elimina
# =================================================================

class SoggettoTitoliIvaDetailView(DomainAPIView):
    """GET dettaglio (con ambiti e movimenti), PATCH aggiorna, DELETE elimina."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="SoggettoTitoloIvaDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio del titolo, con le righe di ambito e il registro.
    def get(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return success_response(
            TitoliIvaService().get_titolo(soggetto_id, titolo_id),
        )

    @extend_schema(
        request=inline_serializer(name="SoggettoTitoloIvaUpdateReq", fields={
            "tipo_titolo_iva_id": serializers.IntegerField(required=False),
            "iva_id": serializers.IntegerField(required=False),
            "ambito": serializers.CharField(required=False),
            "valido_dal": serializers.DateField(required=False),
            "valido_al": serializers.DateField(required=False, allow_null=True),
            "protocollo": serializers.CharField(required=False, allow_null=True),
            "data_ricezione": serializers.DateField(required=False, allow_null=True),
            "riferimento": serializers.CharField(required=False, allow_null=True),
            "plafond": serializers.DecimalField(
                max_digits=18, decimal_places=2, required=False, allow_null=True,
            ),
            "attivo": serializers.BooleanField(required=False),
            "note": serializers.CharField(required=False, allow_null=True),
        }),
        responses={200: inline_serializer(
            name="SoggettoTitoloIvaUpdateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna il titolo.
    # ⛔ `emittente_fiscale_id` NON e' nel serializer, ed e' la decisione Q5:
    #    spostare il destinatario sposterebbe sotto un altro fornitore anche il
    #    plafond gia' consumato, perche' i movimenti sono attaccati al titolo.
    def patch(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return success_response(
            TitoliIvaService().update_titolo(soggetto_id, titolo_id, corpo_oggetto(request)),
        )

    @extend_schema(
        responses={200: inline_serializer(
            name="SoggettoTitoloIvaDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina il titolo, ammesso solo senza movimenti (Q6).
    def delete(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return success_response(
            TitoliIvaService().delete_titolo(soggetto_id, titolo_id),
        )


# =================================================================
# Ambiti del titolo — l'oggetto su cui il titolo si applica (D12)
# =================================================================

class SoggettoTitoloIvaAmbitiView(DomainAPIView):
    """GET righe di ambito, POST aggiunge una riga."""
    area_funzionale = _AREA
    # ⭐ Cancello di perimetro emittente: la lista e' a catalogo (lotto 3,
    #    2026-09-02), quindi la view deve dichiarare il suo `lista_codice` — e'
    #    lui che aggancia `ui.fn_resolve_lista_config`, senza il quale la lista
    #    non e' configurabile affatto.
    # ⚠️ Il perimetro qui vale come sul PADRE (`anagrafiche.soggetto_titoli_iva`):
    #    l'emittente e' quello dell'operatore. Se non lo fosse, il drawer del
    #    titolo non si sarebbe nemmeno potuto aprire — la lista da cui si arriva
    #    e' gia' passata dallo stesso cancello.
    lista_codice = "anagrafiche.titolo_iva_ambiti"
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="TitoloIvaAmbitiListResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Righe di ambito del titolo, con il conteggio accanto.
    # ⚠️ NON paginata, e il `count` non e' per questo decorativo: la lista 64 si
    #    monta `:paginata="false"`, dove `total` e' l'asserzione che le righe
    #    consegnate siano TUTTE — il building block rifiuta di disegnare la
    #    tabella se non coincide con quante ne ha ricevute.
    def get(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return success_response(
            TitoliIvaService().list_ambiti(soggetto_id, titolo_id),
        )

    @extend_schema(
        request=inline_serializer(name="TitoloIvaAmbitoCreateReq", fields={
            "livello": serializers.CharField(),
            "articolo_id": serializers.UUIDField(required=False, allow_null=True),
            "gruppo_voce_id": serializers.IntegerField(required=False, allow_null=True),
            "tipo_voce_id": serializers.IntegerField(required=False, allow_null=True),
            "note": serializers.CharField(required=False, allow_null=True),
        }),
        responses={200: inline_serializer(
            name="TitoloIvaAmbitoCreateResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiunge una riga di ambito (ARTICOLO / GRUPPO_VOCE / TIPO_VOCE).
    def post(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: TitoliIvaService().create_ambito(soggetto_id, titolo_id, p),
        )


class SoggettoTitoloIvaAmbitoDetailView(DomainAPIView):
    """DELETE toglie una riga di ambito."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="TitoloIvaAmbitoDeleteResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Toglie una riga di ambito.
    def delete(
        self, request: Request, soggetto_id: str, titolo_id: int, ambito_id: int,
    ) -> JsonResponse:
        return success_response(
            TitoliIvaService().delete_ambito(soggetto_id, titolo_id, ambito_id),
        )


# =================================================================
# Registro movimenti del titolo (D5)
# =================================================================

class SoggettoTitoloIvaMovimentiView(DomainAPIView):
    """GET registro movimenti, POST registra una FORZATURA manuale."""
    area_funzionale = _AREA
    # ⭐ Cancello di perimetro emittente, stessa ragione degli ambiti qui sopra
    #    (lotto 3, 2026-09-02): senza `lista_codice` la lista non e'
    #    configurabile affatto, e il perimetro vale come sul padre.
    lista_codice = "anagrafiche.titolo_iva_movimenti"
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="TitoloIvaMovimentiListResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Il registro del titolo: fatture, note di credito e forzature.
    # ⚠️ PAGINATO (lista 65): il registro cresce a ogni fattura.
    # ⛔ `order_by` si legge GREZZO (`qp_str`), non da `parse_list_params`:
    #    il bundle ha un default suo (`"descrizione"`) che qui non e' una
    #    colonna di niente. `order_dir` dal bundle: assente = `None`, e decide
    #    il default del repository, «il piu' recente per primo».
    def get(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(TitoliIvaService().list_movimenti(
            soggetto_id, titolo_id,
            limit=p["limit"],
            offset=p["offset"],
            order_by=qp_str(qp.get("order_by")),
            order_dir=p["order_dir"],
        ))

    @extend_schema(
        request=inline_serializer(name="TitoloIvaForzaturaCreateReq", fields={
            "imponibile": serializers.DecimalField(max_digits=18, decimal_places=2),
            "data_movimento": serializers.DateField(),
            "motivo": serializers.CharField(),
        }),
        responses={200: inline_serializer(
            name="TitoloIvaForzaturaCreateResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Registra una forzatura manuale sul plafond.
    # ⛔ SOLO forzature (Q3): `FATTURA` e `NOTA_CREDITO` li produce la
    #    fatturazione con I4, dalla primitiva che tiene il lock di D15-bis. Il
    #    guard sta nel service, dove puo' dare il messaggio giusto — qui il
    #    serializer non espone nemmeno `tipo_movimento`.
    def post(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: TitoliIvaService().create_forzatura(
                soggetto_id, titolo_id, p,
            ),
        )


class SoggettoTitoloIvaMovimentoAnnullaView(DomainAPIView):
    """POST annulla un movimento del registro con un contro-movimento."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        request=inline_serializer(name="TitoloIvaMovimentoAnnullaReq", fields={
            "motivo": serializers.CharField(),
        }),
        responses={200: inline_serializer(
            name="TitoloIvaMovimentoAnnullaResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Annulla una forzatura scrivendo il contro-movimento (`Q7`).
    # ⛔ `annulla` come ultimo segmento, e NON un `DELETE`: l'azione non
    #    cancella niente — aggiunge una riga. Il verbo nomina cio' che e', ed e'
    #    la grammatica URL delle azioni di dominio.
    # ⚠️ Nessun `tipo_movimento` nel serializer: si annullano SOLO forzature, e
    #    a dirlo e' la check a DB — che risponde con il motivo, non con un 500.
    def post(
        self, request: Request, soggetto_id: str, titolo_id: int, movimento_id: int,
    ) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: TitoliIvaService().annulla_movimento(
                soggetto_id, titolo_id, movimento_id, p,
            ),
        )


# =================================================================
# Presidio: i titoli con il plafond sfondato (Q4)
# =================================================================

class TitoliIvaSfondatiView(DomainAPIView):
    """GET i titoli il cui consumo ha superato il tetto."""
    area_funzionale = _AREA
    # ⭐ Cancello di perimetro emittente: `perimetro_emittente = t` a
    #    catalogo (decisione D-3 del lotto 2, 2026-09-02) — vale
    #    l'emittente dell'operatore, e la lista non si assume il compito
    #    di dire da quale emittente arriva ogni riga.
    lista_codice = "anagrafiche.titoli_iva_sfondati"
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="TitoliIvaSfondatiResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista di presidio, cross-soggetto.
    # ⭐ Esiste perche' il DB ha deciso di NON bloccare il superamento sulle
    #    forzature: «una forzatura esiste per registrare fatturazioni fuori dal
    #    sistema, e impedire di scriverla impedirebbe di accorgersene». Questa
    #    lista e' l'altra meta' di quella decisione.
    # ⚠️ PAGINATA: `limit`/`offset`/`order_by`/`order_dir` dal query string, con
    #    il bundle standard `parse_list_params`. L'ordinamento di default resta
    #    l'eccedenza decrescente — su un presidio l'ordine non e' una preferenza.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order=SFONDATI_ORDER_DEFAULT)
        dati = TitoliIvaService().list_titoli_sfondati(
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            # ⭐ Assente = `None` (dal 2026-09-26 `parse_list_params` non lo
            #    normalizza piu' ad "asc"): decide il `default_desc` del
            #    repository, il caso piu' grave per primo. Fino ad allora qui
            #    si rileggeva il valore grezzo per aggirare il bundle.
            order_dir=p["order_dir"],
        )
        return success_response(dati)


# =================================================================
# Export della lista dei titoli del soggetto (DEF-1)
# =================================================================

class SoggettoTitoliIvaExportView(DomainAPIView):
    """GET esporta in CSV/XLSX i titoli IVA del soggetto."""
    area_funzionale = _AREA
    # ⭐ Stesso `lista_codice` della lista a video, ed e' il punto dell'export
    #    configurabile: le colonne del file sono quelle che l'operatore VEDE
    #    (preferenza + preset + permessi), non un elenco cablato qui che
    #    diverge alla prima colonna aggiunta a catalogo.
    lista_codice = "anagrafiche.soggetto_titoli_iva"
    model_permission = _MODEL

    @extend_schema(
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Il file della lista dei titoli di UN soggetto.
    # ⚠️ `limit=EXPORT_MAX_ROWS + 1` e non la pagina a video: l'export esporta
    #    il DATASET, non la pagina. Il `+1` serve al guard di
    #    `build_export_response`, che rifiuta PRIMA di serializzare invece di
    #    consegnare un file troncato in silenzio.
    # ⚠️ `?formato=`, non `?format=`: quest'ultimo e' un parametro magico di DRF
    #    e collide col content negotiation (`feedback_drf_format_magic_param`).
    def get(self, request: Request, soggetto_id: str) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        dati = TitoliIvaService().list_titoli_soggetto(
            soggetto_id,
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
            # ⛔ Nessun filtro da dichiarare: questa lista non ne ha — il
            #    soggetto e' nel path, non e' una scelta dell'operatore. Un
            #    `{"soggetto": ...}` scritto qui sarebbe un filtro inventato
            #    nell'intestazione del file.
            filtri_applicati=None,
            fmt=fmt,
        )
