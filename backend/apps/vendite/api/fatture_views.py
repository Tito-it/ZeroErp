# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view di CONSULTAZIONE della fattura — dettaglio completo
#        (testata + righe + riepilogo IVA + scadenze) per il drawer di
#        visualizzazione. Sola lettura: la fattura si produce dalla pipeline
#        di fatturazione e oltre la soglia di congelamento le righe sono
#        congelate a DB (`trgfn_fattura_satellite_guard_congelamento`, la
#        guardia generica che dal 2026-08-30 copre anche le righe), quindi
#        qui non esiste nessun verbo di modifica. La soglia e' un dato:
#        `config.stati_doc_fiscale.congela_fiscale` (oggi da DEFINITIVA).
#        Le view dei documenti generati (stampa/allegati) vivono in
#        `fatture_documenti_views.py`; le azioni di processo (emissione,
#        numerazione, ristampa massiva) nel cockpit fatturazione.
#        Brief: docs/it/dev/work-done/brief-be-fe-drawer-fattura.md §5
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id
from apps.core.api.payload_validators import (
    paginated_envelope,
    parse_list_params,
    qp_str,
)
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api._giornale_params import (
    EMITTENTE_PARAM_GIORNALE_ENTITA,
    PARAMS_LISTA_GIORNALE_ENTITA,
    parametri_lista_giornale_entita,
)
from apps.vendite.api._list_filters_helpers import extract_doc_list_filters
from apps.core.api.success_responses import success_response
from apps.vendite.services.vendite_service import (
    get_fattura_dettaglio,
    get_fattura_giornale,
    list_fatture_rows,
)
from apps.core.api.openapi_params import param_ricerca_full
from apps.ui.api.lista_figlia_views import EMITTENTE_DOCUMENTO_PARAM, build_lista_figlia_views
from apps.vendite.db.fatture_repository import FattureRepository
from apps.vendite.services import vendite_service


class ApiFatturaDetail(DomainAPIView):
    """Dettaglio completo di una fattura per la consultazione a video.

    Restituisce in un solo round-trip testata (cliente, emittente, pagamento,
    totali, tutto gia' decodificato), righe, riepilogo IVA e piano rate — gli
    stessi quattro lettori che alimentano il contesto del PDF, cosi' video e
    stampa mostrano lo stesso documento per costruzione — piu' i `contatori`
    dei badge (note), che il drawer mostra senza una seconda chiamata.

    Le `righe` vengono dalla vista della lista (`vw_fattura_righe_lista`):
    primo livello, componenti esposti di un kit dentro il padre. Dal
    2026-09-30 e' anche la sorgente del contesto di stampa (forma 2, brief-db-
    documenti-versione-contesto-template §11): una proiezione sola.

    Fattura inesistente **o fuori scope emittente** → 404 identico: un errore
    che distinguesse i due casi confermerebbe l'esistenza di una fattura altrui.
    """

    area_funzionale = "vendite"
    # `vendite.fattura` E' catalogato in `config.area_model_overrides`: un admin
    # puo' bloccare le fatture come singolo oggetto, e il drawer deve
    # rispettarlo. Senza override il resolver ricade sul livello area, quindi
    # per l'operatore normale non cambia nulla.
    model_permission = ("vendite", "fattura")

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeFatturaDettaglioResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFatturaDettaglioData",
                        fields={
                            "fattura": serializers.DictField(),
                            "righe": serializers.ListField(child=serializers.DictField()),
                            "riepilogo_iva": serializers.ListField(
                                child=serializers.DictField(),
                            ),
                            "scadenze": serializers.ListField(
                                child=serializers.DictField(),
                            ),
                            # I documenti a monte che la fattura cita, dal
                            # lettore del DB `vendite.fn_fattura_origini`:
                            # livello, tipo_id, tipo_codice_interno,
                            # etichetta, uid, codice. Lista vuota = nessuno.
                            "origini": serializers.ListField(
                                child=serializers.DictField(),
                            ),
                            # Badge della barra azioni del drawer senza un
                            # secondo round-trip. Dict (non scalare) per
                            # reggere i prossimi contatori.
                            "contatori": inline_serializer(
                                name="VenditeFatturaDettaglioContatori",
                                fields={"note": serializers.IntegerField()},
                            ),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il documento fattura completo per il drawer.
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        # `get_scope_user_id` ritorna None per il superuser (vede tutto): lo
        # scope applicativo si somma alla RLS, non la sostituisce.
        data = get_fattura_dettaglio(
            fattura_id=fattura_id,
            auth_user_id=get_scope_user_id(request),
        )
        return success_response(data)


class ApiFatturaGiornale(DomainAPIView):
    """La STORIA di una fattura: cosa le e' successo, in ordine di tempo.

    Elenco paginato e di sola lettura dalla vista cucita
    `script.vw_giornale_entita`, che unisce i registri di evento del progetto in
    una forma normalizzata — per la fattura oggi risponde `vendite.fatture_log`.

    ⭐ E' il **primo consumatore** di quella vista: fino al 2026-08-24 il suo
    perimetro era verificato dal pgTAP e non dall'uso.

    ⭐ Dal 2026-09-27 e' la lista a catalogo `vendite.giornale` — la stessa del
    giornale trasversale e della Storia del lotto — filtrata sul documento:
    contratto di lista standard (`limit`/`offset`/`order_by`/`order_dir`,
    `_giornale_params`), ordine di partenza del preset (`quando desc`).

    ⛔ Non e' il pannello «Collegamenti» (`/passaggi/`), che dice **con quali
    altri documenti** questo e' legato: qui si risponde a *«cosa gli e'
    successo»*, che e' una domanda diversa e ha una sorgente diversa.

    Fattura inesistente **o fuori scope emittente** → 404 identico. ⚠️ E il 404
    lo decide la TESTATA, non la vista: quella e' `security_invoker` e su una
    fattura altrui risponderebbe zero righe, cioe' «non e' successo niente»
    invece di «non la vedi».
    """

    area_funzionale = "vendite"
    # Stesso livello oggetto del dettaglio: chi non puo' vedere la fattura non
    # ne vede nemmeno la storia.
    model_permission = ("vendite", "fattura")
    lista_codice = "vendite.giornale"
    lista_emittente_param = EMITTENTE_PARAM_GIORNALE_ENTITA

    @extend_schema(
        parameters=PARAMS_LISTA_GIORNALE_ENTITA,
        responses={
            200: inline_serializer(
                name="VenditeFatturaGiornaleResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFatturaGiornaleData",
                        fields={
                            "fattura_id": serializers.IntegerField(),
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
    # Scopo: Restituisce via GET il giornale paginato della fattura.
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        data = get_fattura_giornale(
            fattura_id=fattura_id,
            **parametri_lista_giornale_entita(request.query_params),
            auth_user_id=get_scope_user_id(request),
        )
        return success_response(data)


# Codice lista (`ui.lista_definizione`) usato dall'export per risolvere colonne
# visibili, ordine e permessi dell'operatore.
_LISTA_CODICE_FATTURE = "vendite.fatture"

# Scopo: i filtri della lista fatture, letti una volta sola dalla query string.
# ⭐ Riusa `extract_doc_list_filters`, la convenzione comune alle sei sorelle
#    (`stato_codice_interno`, `billing_account_id`, `data_da`, `data_a`,
#    `utility_id`), e aggiunge il solo filtro che è proprio del documento
#    fiscale: la NATURA, che separa le fatture dalle note di credito.
# ⚠️ `data_da`/`data_a` filtrano la DATA DEL DOCUMENTO, non la competenza della
#    commessa che l'ha generato: è la ragione per cui questa lista esiste.
def _filtri_lista_fatture(qp) -> dict[str, Any]:
    f = extract_doc_list_filters(qp, with_utility=True)
    f["natura_doc_codice"] = qp_str(qp.get("natura_doc_codice"))
    # ⭐ Identificativo fiscale: e' il criterio con cui la lista SOGGETTI manda
    #    qui. Un soggetto e' una persona giuridica, non un conto — i suoi
    #    documenti si raccolgono per codice fiscale / partita IVA, non per
    #    billing account (che sono piu' d'uno).
    f["id_fiscale"] = qp_str(qp.get("id_fiscale"))
    return f


_PARAMETRI_LISTA_FATTURE = [
    param_ricerca_full(),
    OpenApiParameter(name="stato_codice_interno", type=str, required=False),
    OpenApiParameter(name="natura_doc_codice", type=str, required=False,
                     description="FATTURA | NOTA_CREDITO | NOTA_DEBITO"),
    OpenApiParameter(name="billing_account_id", type=int, required=False),
    OpenApiParameter(name="id_fiscale", type=str, required=False,
                     description="Codice fiscale / partita IVA, confronto ESATTO "
                                 "(la ricerca libera sullo stesso campo e' invece "
                                 "parziale)."),
    OpenApiParameter(name="utility_id", type=int, required=False),
    OpenApiParameter(name="data_da", type=str, required=False,
                     description="Data ISO del DOCUMENTO (non della competenza)."),
    OpenApiParameter(name="data_a", type=str, required=False),
    OpenApiParameter(name="limit", type=int, required=False),
    OpenApiParameter(name="offset", type=int, required=False),
    OpenApiParameter(name="order_by", type=str, required=False,
                     description="`campo_sorgente` del catalogo `vendite.fatture`."),
    OpenApiParameter(name="order_dir", type=str, required=False),
]


class ApiFattureList(DomainAPIView):
    """GET /api/v1/vendite/fatture/ — la lista dei documenti fiscali.

    ⭐ La **settima** lista del ciclo attivo: fino al 2026-08-24 la fattura era
    l'unico documento senza la sua, e si raggiungeva solo passando da un lotto,
    da un cruscotto o da un collegamento.

    ⚠️ Sola lettura: la fattura si produce dalla pipeline di fatturazione, non
    da un form. Nessun `POST`, e non è una dimenticanza.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    # ⚠️ LETTERALE e non la costante: `test_perimetro_emittente_copertura`
    #    legge questo attributo con `ast.literal_eval`, e una variabile la
    #    salta in silenzio — la lista risulterebbe senza cancello.
    lista_codice = "vendite.fatture"
    # Stesso livello oggetto del dettaglio: chi non può vedere una fattura non
    # ne vede nemmeno l'elenco.
    model_permission = ("vendite", "fattura")

    @extend_schema(
        operation_id="vendite_fatture_list",
        parameters=_PARAMETRI_LISTA_FATTURE,
        responses={200: inline_serializer(
            name="VenditeFattureListResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: elenco paginato dei documenti fiscali, con filtri e scope emittente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data")
        results, total = list_fatture_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            **_filtri_lista_fatture(qp),
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


class ApiFattureExportView(DomainAPIView):
    """GET /api/v1/vendite/fatture/export/?formato=csv|xlsx

    ⚠️ `formato` e non `format`: quest'ultimo è un magic parameter di DRF e
    verrebbe intercettato prima della view.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    # ⚠️ LETTERALE e non la costante: `test_perimetro_emittente_copertura`
    #    legge questo attributo con `ast.literal_eval`, e una variabile la
    #    salta in silenzio — la lista risulterebbe senza cancello.
    lista_codice = "vendite.fatture"
    model_permission = ("vendite", "fattura")

    @extend_schema(
        operation_id="vendite_fatture_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            *_PARAMETRI_LISTA_FATTURE,
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: file CSV/XLSX della lista fatture.
    # ⚠️ Filtri IDENTICI a quelli della lista — il file È la lista. E si fetcha
    #    `EXPORT_MAX_ROWS + 1` per RILEVARE il superamento del tetto invece di
    #    consegnare un file troncato in silenzio.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)
        p = parse_list_params(qp, default_order="data")
        filtri = _filtri_lista_fatture(qp)
        results, total = list_fatture_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            max_limit=EXPORT_MAX_ROWS + 1,
            **filtri,
        )
        # La ricerca libera la dichiara il BB (`filtri_export_con_ricerca`).
        applicati = {k: str(v) for k, v in filtri.items() if v is not None}
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_FATTURE,
            results=results,
            total=total,
            filtri_applicati=applicati,
            fmt=fmt,
        )


# ── Righe: la lista configurabile `vendite.fattura_righe` (lista 102) ──
# Pagina ed export dal factory condiviso `build_lista_figlia_views`
# (brief-db-liste-righe-documento, lotto C). La closure legge il global di
# modulo a call-time: i patch dei test sul service restano validi.
# ⭐ `con_scope=True`: la testata si legge con lo scope dell'operatore, come
#    il dettaglio e il giornale della fattura.
# ⚠️ Sola lettura: niente `…/righe/` completa esposta a parte — la lettura
#    completa arriva col dettaglio (`righe`), dalla stessa vista.
_FatturaRigheLista, _FatturaRigheListaExport = build_lista_figlia_views(
    schema_prefix="FatturaRighe",
    operation_id="vendite_fatture_righe_lista",
    area_funzionale="vendite",
    lista_emittente_param=EMITTENTE_DOCUMENTO_PARAM,
    url_kwarg="fattura_id",
    model_permission=("vendite", "fattura"),
    pagina_call=lambda documento_id, **kw: vendite_service.list_fattura_righe_pagina(documento_id, **kw),
    colonne_ordinabili=FattureRepository.righe_colonne_ordinabili(),
    ordine_assente=FattureRepository.righe_ordine_di_partenza(),
    con_scope=True,
)


# ⭐ Il cancello di perimetro come LETTERALE nel corpo della classe: e' la
#    forma che `test_perimetro_emittente_copertura` legge (vedi la factory).
class ApiFatturaRigheListaView(_FatturaRigheLista):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.fattura_righe"


class ApiFatturaRigheListaExportView(_FatturaRigheListaExport):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.fattura_righe"
