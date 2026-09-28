# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory delle due API view della LISTA delle righe di un documento
#        vendita — la pagina (`GET …/righe/lista/`) e il suo export
#        (`GET …/righe/lista/export/`) — per la lista configurabile
#        `vendite.<doc>_righe` (brief-db-liste-righe-documento, lotto A,
#        2026-09-28). Regola del 2: quattro documenti (preventivo, ordine,
#        DDT, reso) per due view ciascuno; cambiano solo nomi, kwarg URL,
#        lista a catalogo, oggetto dei permessi e service.
#
# ⭐ PERCHE' `…/righe/lista/` E NON `…/righe/` (decisione di Tid,
#    2026-09-28). `GET …/righe/` resta la lettura COMPLETA (dialog di
#    evasione e riconsegna, stampe, script), e la stessa view serve il POST
#    di creazione riga. Il cancello del perimetro emittente (`lista_codice`)
#    scatta su OGNI metodo della view: messo su `…/righe/` avrebbe rifiutato
#    con 422 anche la creazione di una riga a chi vede piu' emittenti. Sul
#    percorso suo, il cancello guarda solo la lista.
#
# ⭐ `lista_emittente_param`: la lista vive DENTRO il drawer di un documento,
#    che ha gia' il suo emittente. La lista a catalogo e' `perimetro_emittente
#    = t`, `multi_emittente = f`: senza il parametro, chi vede piu' emittenti
#    riceverebbe E_UI_LISTA_EMITTENTE_DA_SCEGLIERE a drawer aperto. E' la PK
#    (`emittenti_fiscali.id`), come per le revisioni.
#
# ⭐ IL `lista_codice` NON LO METTE LA FACTORY: lo scrive il dominio, come
#    LETTERALE, nelle due sottoclassi (`class ApiPreventivoRigheListaView(
#    _Lista): lista_codice = "vendite.preventivo_righe"`). E' la forma che
#    `test_perimetro_emittente_copertura` sa leggere (AST sul corpo delle
#    classi): assegnato qui con un `setattr` il cancello ci sarebbe ma il
#    presidio non lo vedrebbe. L'export lo rilegge da `self.lista_codice`:
#    una sede sola. Lista ed export dichiarano lo stesso codice (l'export e'
#    la porta piu' larga).
#
#    Testabilita' (stesso contratto di `riepilogo_iva_views`): il service
#    arriva come CLOSURE del modulo del dominio, che legge il global a
#    call-time, cosi' i patch dei test sul service continuano a funzionare.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.payload_validators import paginated_envelope, parse_list_params
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS

# La lettura della pagina: (documento_id, search=, order_by=, order_dir=,
# limit=, offset=, max_limit=) -> (righe, totale).
PaginaRighe = Callable[..., tuple[list[dict[str, Any]], int]]

_EMITTENTE_PARAM = "emittente_fiscale_id"


# Scopo: i parametri OpenAPI comuni a pagina ed export.
def _parametri(colonne_ordinabili: Iterable[str]) -> list[OpenApiParameter]:
    return [
        OpenApiParameter(
            name=_EMITTENTE_PARAM, type=int, required=False,
            description=(
                "Emittente del documento (PK). Lo legge SOLO il cancello di "
                "perimetro, per chi vede più emittenti: non filtra le righe e "
                "non allarga niente — la visibilità resta allo scope e alla RLS."
            ),
        ),
        param_ricerca_full(),
        OpenApiParameter(
            name="order_by", type=str, required=False,
            description=(
                "campo_sorgente della lista a catalogo ("
                + " | ".join(colonne_ordinabili)
                + "). Assente: l'ordine del documento."
            ),
        ),
        OpenApiParameter(name="order_dir", type=str, required=False,
                         description="asc | desc (assente: asc; desc sulle date)"),
    ]


# Scopo: Costruisce la coppia (lista, export) delle righe di un documento.
#        Parametri:
#         - schema_prefix:  prefisso dei nomi OpenAPI e delle classi
#                           ("Preventivo" -> "ApiPreventivoRigheLista")
#         - operation:      radice degli operationId ("vendite_preventivi")
#         - url_kwarg:      kwarg URL del documento ("preventivo_id")
#         - model_permission: oggetto dei permessi del documento: le righe
#                           sono una parte dell'oggetto e ne chiedono il livello
#         - pagina_call:    closure del dominio sul service di pagina
#         - colonne_ordinabili: la whitelist del repository, per la doc OpenAPI
def build_righe_lista_views(
    *,
    schema_prefix: str,
    operation: str,
    url_kwarg: str,
    model_permission: tuple[str, str],
    pagina_call: PaginaRighe,
    colonne_ordinabili: Iterable[str],
) -> tuple[type[DomainAPIView], type[DomainAPIView]]:
    parametri = _parametri(sorted(colonne_ordinabili))

    class _RigheLista(DomainAPIView):
        area_funzionale = "vendite"
        is_search_endpoint = True

        @extend_schema(
            operation_id=f"{operation}_righe_lista",
            parameters=[
                *parametri,
                OpenApiParameter(name="limit", type=int, required=False),
                OpenApiParameter(name="offset", type=int, required=False),
            ],
            responses={200: inline_serializer(
                name=f"{schema_prefix}RigheListaResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: una pagina delle righe del documento, per la lista
        #        configurabile. Envelope paginato standard.
        def get(self, request: Request, **kwargs: int) -> JsonResponse:
            qp = request.query_params
            # ⚠️ `default_order=""`: senza richiesta decide il repository (l'ordine
            #    del documento), non una colonna scelta qui.
            p = parse_list_params(qp, default_order="")
            results, total = pagina_call(
                int(kwargs[url_kwarg]),
                search=p["search"],
                order_by=p["order_by"],
                order_dir=p["order_dir"],
                limit=p["limit"],
                offset=p["offset"],
            )
            return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    class _RigheExport(DomainAPIView):
        area_funzionale = "vendite"
        is_search_endpoint = True

        @extend_schema(
            operation_id=f"{operation}_righe_lista_export",
            parameters=[
                OpenApiParameter(name="formato", type=str, required=False,
                                 description="csv (default) | xlsx"),
                *parametri,
            ],
            responses={
                (200, "text/csv"): bytes,
                (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
            },
        )
        # Scopo: il file delle righe del documento, con ricerca e ordinamento
        #        della lista a video. Legge fino a EXPORT_MAX_ROWS + 1 righe per
        #        accorgersi di un file troncato.
        def get(self, request: Request, **kwargs: int) -> HttpResponse:
            qp = request.query_params
            fmt = parse_export_format(request)
            p = parse_list_params(qp, default_order="")
            results, total = pagina_call(
                int(kwargs[url_kwarg]),
                search=p["search"],
                order_by=p["order_by"],
                order_dir=p["order_dir"],
                limit=EXPORT_MAX_ROWS + 1,
                offset=0,
                max_limit=EXPORT_MAX_ROWS + 1,
            )
            return build_export_response(
                request, lista_codice=self.lista_codice,
                results=results, total=total,
                filtri_applicati=None, fmt=fmt,
            )

    for classe, suffisso in ((_RigheLista, "RigheListaBase"), (_RigheExport, "RigheListaExportBase")):
        classe.model_permission = model_permission
        classe.lista_emittente_param = _EMITTENTE_PARAM
        classe.__name__ = f"Api{schema_prefix}{suffisso}"
        classe.__qualname__ = classe.__name__
        classe.__doc__ = (
            f"GET …/{{{url_kwarg}}}/righe/lista/{'export/' if classe is _RigheExport else ''} — "
            "lista configurabile delle righe del documento."
        )
    return _RigheLista, _RigheExport
