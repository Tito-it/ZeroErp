# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API del CRUD delle FAMIGLIE DI DOCUMENTO — lista, export, dettaglio,
#        creazione (dalla madre), update e il verbo `attivo`, piu' il lookup che
#        alimenta il drawer dei registri.
#        Brief: brief-be-fe-crud-registri-di-numerazione §11.10.
# ------------------------------------------------------------
#
# ⭐ DUE BASI IN UN FILE SOLO, ED E' LA COSA DA CAPIRE PRIMA DI LEGGERE.
#    Il CRUD sta su `AdminAPIView` — ✅ D6 (Tid, 2026-09-01): «solo
#    amministratore», e il cancello sta sull'endpoint, non nel database
#    (`vendite.famiglie_documento` non ha RLS e non gliene si aggiunge una per
#    un caso che un permesso risolve).
#    ⛔ Il LOOKUP no, e non e' un'incoerenza: lo chiama il drawer dei REGISTRI —
#    una schermata di dominio, aperta da chi i registri li configura — per
#    precompilare la forma del numero e per sapere quali campi mostrare.
#    Metterlo dietro il cancello dell'amministratore spegnerebbe quei campi a
#    tutti gli altri, in silenzio: il drawer non riceverebbe i default e
#    ricadrebbe sui valori cablati che BE-F2/FE-F1 esistono per togliere.

from __future__ import annotations

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import AdminAPIView, DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
)
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.services.famiglie_service import FamiglieDocumentoService
from apps.core.api.openapi_params import param_ricerca_full

# Il codice della lista a catalogo. ⚠️ Vive in una costante perche' lo leggono
# in tre: la lista, l'export e — indirettamente — il presidio di copertura.
_LISTA_CODICE = "vendite.famiglie_documento"

# I filtri della lista, in una sede sola: la view di lista e quella di export
# devono filtrare allo STESSO modo, o si esporta un insieme diverso da quello
# che si vede (ed e' il difetto che l'export dei documenti ha gia' avuto).
_PARAMETRI_FILTRO = [
    OpenApiParameter(
        name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False,
        description=(
            "Assente = TUTTE, spente comprese. ⚠️ Il default non nasconde le "
            "famiglie spente: sono quelle che spiegano un rifiuto in creazione "
            "(la tabella e' gia' numerata) e nasconderle manderebbe a cercarle "
            "dove non si vedono."
        ),
    ),
    OpenApiParameter(
        name="gestisce_serie", type=bool, location=OpenApiParameter.QUERY,
        required=False,
        description="Derivato da `colonna_serie IS NOT NULL`, non una colonna.",
    ),
    param_ricerca_full(),
    OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY,
                     required=False,
                     description="Whitelist; fuori whitelist → ordine di default."),
    OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY,
                     required=False, description="asc (default) | desc"),
]


# Scopo: i filtri della lista, letti dalla query string una volta per le due
#        view che li usano.
def _filtri(request: Request) -> dict:
    qp = request.query_params
    return {
        "attivo": qp_bool_optional(qp.get("attivo"), "attivo"),
        "gestisce_serie": qp_bool_optional(qp.get("gestisce_serie"), "gestisce_serie"),
    }


class ApiFamiglieList(AdminAPIView):
    """GET/POST /api/v1/vendite/famiglie/ — lista e creazione."""

    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_famiglie_list",
        parameters=[
            *_PARAMETRI_FILTRO,
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY,
                             required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY,
                             required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeFamiglieListResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata delle famiglie, con i conteggi dei registri e i
    #        motivi dei DUE verbi bloccabili (spegnere, cambiare la struttura).
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="codice_interno")
        results, total = FamiglieDocumentoService().list_famiglie(
            **_filtri(request),
            search=p["search"],
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        operation_id="vendite_famiglie_create",
        request=inline_serializer(name="VenditeFamigliaCreateReq", fields={
            "codice_interno": serializers.CharField(
                help_text=(
                    "Il codice_interno della SORGENTE di cui la famiglia numera i "
                    "documenti (config.sorgenti, da `famiglie/sorgenti/`): la "
                    "tabella e' la sua target_table. Dal 2026-10-20 non ci sono "
                    "piu' schema_tabella e nome_tabella (G-5)."
                ),
            ),
            "descrizione": serializers.CharField(),
            "colonna_numero": serializers.CharField(),
            "colonna_billing_account": serializers.CharField(
                required=False, allow_null=True,
                help_text=(
                    "Vuota = questa famiglia non ha un billing account "
                    "(P-9, 2026-09-14: la controparte di un ordine di acquisto "
                    "e' un soggetto_ruolo)."
                ),
            ),
            "colonna_serie": serializers.CharField(
                required=False, allow_null=True,
                help_text="Vuota = questa famiglia non gestisce le serie.",
            ),
            "prefisso_default": serializers.CharField(required=False, allow_null=True),
            "lunghezza_default": serializers.IntegerField(required=False),
            "attivo": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(
            name="VenditeFamigliaCreateResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea la famiglia PASSANDO DALLA MADRE — che nella stessa
    #        transazione le provvede i registri su ogni emittente.
    # ⛔ Nessun `presidia_data_documento` nel payload, ed e' il modello a dirlo:
    #    una famiglia creata dal CRUD nasce NON fiscale (✅ D5, §11.11). Il
    #    `CHECK` dei registri cabla `'FATTURA'` e un `CHECK` non puo' leggere
    #    un'altra tabella — offrire il campo prometterebbe un comportamento che
    #    il resto del modello non da'.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request, handler=FamiglieDocumentoService().crea_famiglia,
        )


class ApiFamiglieExport(AdminAPIView):
    """GET /api/v1/vendite/famiglie/export/?formato=csv|xlsx

    ⛔ Nessun renderer nuovo (§11.10 BE-F7): righe + colonne del catalogo al
    building block generico. Il file esce con le stesse colonne che si vedono
    a video, perche' le risolve la stessa config runtime.
    ⚠️ Il parametro e' `formato`, non `format`: `format` e' un magic query
    parameter di DRF e intercetterebbe la chiamata prima della view.
    """

    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_famiglie_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, location=OpenApiParameter.QUERY,
                             required=False, description="csv (default) | xlsx"),
            *_PARAMETRI_FILTRO,
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Restituisce il file di export delle famiglie filtrate.
    # ⚠️ `EXPORT_MAX_ROWS + 1` non e' un di piu': serve a distinguere «ci stanno
    #    tutte» da «sono di piu' del limite» PRIMA di serializzare.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)
        p = parse_list_params(request.query_params, default_order="codice_interno")
        filtri = _filtri(request)
        results, total = FamiglieDocumentoService().list_famiglie(
            **filtri,
            search=p["search"],
            limit=EXPORT_MAX_ROWS + 1, offset=0,
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE,
            results=results,
            total=total,
            # ⚠️ Solo i filtri DAVVERO applicati: `filtri` porta `None` per
            #    quelli non passati, e un metadato «attivo: None» dentro il file
            #    dice a chi lo rilegge che un filtro c'era, quando non c'era.
            #    La ricerca libera la dichiara il BB (`filtri_export_con_ricerca`).
            filtri_applicati={
                k: v
                for k, v in filtri.items()
                if v is not None and v != ""
            },
            fmt=fmt,
        )


class ApiFamigliaDetail(AdminAPIView):
    """GET/PATCH /api/v1/vendite/famiglie/<id>/ — dettaglio e modifica."""

    @extend_schema(
        operation_id="vendite_famiglie_detail",
        responses={200: inline_serializer(
            name="VenditeFamigliaDetailResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio di una famiglia, coi conteggi e i due blocchi.
    def get(self, request: Request, famiglia_id: int) -> JsonResponse:
        return success_response(
            FamiglieDocumentoService().get_famiglia(famiglia_id),
        )

    @extend_schema(
        operation_id="vendite_famiglie_update",
        request=inline_serializer(name="VenditeFamigliaUpdateReq", fields={
            # Il codice dell'operatore (dal 2026-09-24): mutabile e unico; vuoto -> 400.
            "codice": serializers.CharField(required=False),
            "descrizione": serializers.CharField(required=False),
            "colonna_numero": serializers.CharField(required=False),
            "colonna_billing_account": serializers.CharField(required=False),
            "colonna_serie": serializers.CharField(required=False, allow_null=True),
            "prefisso_default": serializers.CharField(required=False, allow_null=True),
            "lunghezza_default": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(
            name="VenditeFamigliaUpdateResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna le colonne ammesse.
    # ⛔ `codice_interno` e `attivo` non sono fra queste: il primo lo presidia il
    #    lock automatico (D3), il secondo ha il suo verbo. Le quattro colonne
    #    strutturali invece ci sono, e a rifiutarle quando la famiglia ha gia'
    #    dei registri e' il guard `..._guard_struttura` — non un secondo elenco
    #    scritto qui.
    def patch(self, request: Request, famiglia_id: int) -> JsonResponse:
        payload = dict(corpo_oggetto(request))
        return success_response(
            FamiglieDocumentoService().update_famiglia(famiglia_id, payload),
        )


class ApiFamigliaAttivo(AdminAPIView):
    """POST /api/v1/vendite/famiglie/<id>/attivo/ — accende o spegne.

    ⚠️ POST e non PATCH, come il gemello dei registri: e' un VERBO, non la
    modifica di una colonna, e le due schermate devono chiamarlo allo stesso
    modo.
    """

    @extend_schema(
        operation_id="vendite_famiglie_attivo",
        request=inline_serializer(name="VenditeFamigliaAttivoReq", fields={
            "attivo": serializers.BooleanField(),
        }),
        responses={200: inline_serializer(
            name="VenditeFamigliaAttivoResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Verbo suo e non un PATCH su una colonna: spegnere una famiglia e'
    #        l'azione che il guard di disattivazione presidia, e riaccenderla e'
    #        cio' che si fa al posto di crearne un'altra sulla stessa tabella.
    def post(self, request: Request, famiglia_id: int) -> JsonResponse:
        payload = corpo_oggetto(request)
        attivo = payload.get("attivo")
        ErrorManager.require(
            isinstance(attivo, bool),
            code="E_VENDITE_VALIDATION",
            message="Il campo `attivo` è obbligatorio e deve essere booleano.",
            context={"field": "attivo"},
        )
        assert isinstance(attivo, bool)
        return success_response(
            FamiglieDocumentoService().set_attivo(famiglia_id, attivo),
        )


class ApiFamiglieLookup(DomainAPIView):
    """GET /api/v1/vendite/famiglie/lookup/ — le famiglie attive, coi default.

    ⭐ NON e' l'elenco della lista: qui non c'e' paginazione, non ci sono
    capability e non c'e' il cancello dell'amministratore. Lo legge il drawer
    dei REGISTRI, che da queste righe prende `prefisso_default` e
    `lunghezza_default` per precompilare la forma alla creazione (§11.10 FE-F1)
    e `presidia_data_documento` / `gestisce_serie` per decidere quali campi
    mostrare (FE-F2, FE-F5).

    ⛔ E non e' il lookup generico: `dbops.fn_get_lookup_codici` torna
    id/codice/descrizione/attivo e non puo' portare i default della forma ne'
    le colonne di natura — non e' un suo difetto, e' generico e va lasciato
    generico (decisione di Tid, 2026-09-01).
    """

    area_funzionale = "vendite"

    @extend_schema(
        operation_id="vendite_famiglie_lookup",
        responses={200: inline_serializer(
            name="VenditeFamiglieLookupResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Le famiglie attive con i loro default, per le tendine di dominio.
    # ⛔ `{"results": [...]}` E NON LA LISTA NUDA, ed e' la forma di TUTTI i
    #    lookup dedicati (`ProvinceLookupView`, e le gemelle regioni/stati).
    #    ⚠️ Fino al 2026-09-08 qui tornava la lista nuda, e il difetto era
    #    INVISIBILE DA QUESTO LATO: il composable `useLookup` del frontend
    #    trasforma ogni risposta con `r.data.data.results`, che su una lista nuda
    #    vale `undefined`. Il `ref` delle famiglie passava da `[]` a `undefined`,
    #    il primo `.map()` sollevava, e Vue svuotava il sottoalbero — il drawer
    #    dei registri si apriva BIANCO, con il backend verde e nessun errore in
    #    nessun log. Il presidio e' in `test_il_lookup_torna_l_envelope_results`.
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": FamiglieDocumentoService().list_lookup()})


class ApiFamiglieSorgenti(AdminAPIView):
    """GET /api/v1/vendite/famiglie/sorgenti/ — le sorgenti fra cui si sceglie la famiglia.

    ⭐ Dal 2026-10-20 (brief-db-grammatica-unica-documenti 2c, G-5) una famiglia
    e' quella di una SORGENTE: la creazione riceve il suo `codice_interno` e la
    tabella dei documenti e' la sua `target_table`. Il drawer delle famiglie
    sceglie da qui invece di scrivere schema e tabella.

    ⛔ Non e' il lookup generico: quello da' `codice` (il nome mutabile) e non
    `codice_interno`, e non sa dire se la sorgente ha gia' una famiglia o se la
    sua tabella e' gia' numerata — le due informazioni con cui il drawer spegne
    la voce e dice perche'. Il rifiuto vero resta al DB.

    Cancello dell'amministratore, come la creazione: serve solo a lei.
    """

    @extend_schema(
        operation_id="vendite_famiglie_sorgenti",
        responses={200: inline_serializer(
            name="VenditeFamiglieSorgentiResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: le sorgenti di documento con tabella, famiglia esistente e chi
    #        numera gia' la tabella. Envelope `{"results": [...]}`, come i lookup
    #        dedicati (vedi `ApiFamiglieLookup`).
    def get(self, request: Request) -> JsonResponse:
        return success_response(
            {"results": FamiglieDocumentoService().list_sorgenti_numerabili()},
        )
