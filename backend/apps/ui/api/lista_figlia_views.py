# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory delle due API view di una LISTA FIGLIA — la lista
#        configurabile che vive dentro il drawer di un padre (le righe di un
#        documento, la distinta di un articolo): la pagina
#        (`GET …/<padre>/…/lista/`) e il suo export (`…/lista/export/`).
# Note: ⭐ Regola del 2 FRA DOMINI (2026-09-28, ok Tid): nata in vendite per i
#       cinque documenti (lotti A e C del brief-db-liste-righe-documento), la
#       distinta base del catalogo ne era la seconda copia scritta a mano, con
#       le stesse due view. Sta in `ui` e non in `core` perche' l'export e' il
#       BB `export_helpers` di questa app, e `core` non importa `ui`.
# ------------------------------------------------------------
#
# ⭐ UN PERCORSO SUO (`…/righe/lista/`, `…/componenti/lista/`), mai quello
#    della risorsa (decisione di Tid, 2026-09-28). `GET …/righe/` resta la
#    lettura COMPLETA, e la stessa view serve il POST di creazione. Il
#    cancello del perimetro emittente (`lista_codice`) scatta su OGNI metodo
#    della view: messo sulla risorsa avrebbe rifiutato con 422 anche la
#    creazione a chi vede piu' emittenti. Sul percorso suo guarda solo la lista.
#
# ⭐ `lista_emittente_param`: una lista che vive dentro un documento che HA un
#    emittente (`perimetro_emittente = t`, `multi_emittente = f`) lo riceve
#    dal padre, o chi vede piu' emittenti riceverebbe
#    E_UI_LISTA_EMITTENTE_DA_SCEGLIERE a drawer aperto. E' la PK
#    (`emittenti_fiscali.id`): `EMITTENTE_DOCUMENTO_PARAM`. `None` per un
#    padre «per azienda» senza emittente suo (la distinta, D-8.2), dove chi
#    vede piu' emittenti lo sceglie come nella lista degli articoli.
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
# ⭐ `con_scope`: il service riceve lo scope applicativo dell'operatore
#    (`auth_user_id`, sommato alla RLS) per il cancello di testata — la
#    fattura, come il suo dettaglio e il suo giornale.
#
# ⭐ `filtri`: i filtri PROPRI della lista (la distinta: `valido_al`, «in
#    vigore al»), letti dalla query con i validatori del dominio e passati al
#    service come keyword. Pagina ed export li leggono dalla stessa funzione:
#    l'export segue la lista a video per costruzione. Nel file finiscono fra
#    i `filtri_applicati`.
#
#    Testabilita' (stesso contratto di `riepilogo_iva_views`): il service
#    arriva come CLOSURE del modulo del dominio, che legge il global a
#    call-time, cosi' i patch dei test sul service continuano a funzionare.

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id
from apps.core.api.openapi_params import descrizione_order_by, param_ricerca_full
from apps.core.api.payload_validators import paginated_envelope, parse_list_params
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS

# La lettura della pagina: (padre_id, search=, order_by=, order_dir=, limit=,
# offset=, max_limit=, **filtri[, auth_user_id=]) -> (righe, totale).
PaginaFiglia = Callable[..., tuple[list[dict[str, Any]], int]]
# I filtri propri della lista, dalla query: {nome: valore} (None = assente).
LeggiFiltri = Callable[[Mapping[str, Any]], dict[str, Any]]

# L'emittente del documento padre, per il cancello di perimetro (la PK).
EMITTENTE_DOCUMENTO_PARAM = "emittente_fiscale_id"


# Scopo: i parametri OpenAPI comuni a pagina ed export.
def _parametri(
    colonne_ordinabili: Iterable[str],
    *,
    ordine_assente: str,
    lista_emittente_param: str | None,
    parametri_filtri: Sequence[OpenApiParameter],
) -> list[OpenApiParameter]:
    emittente = [] if lista_emittente_param is None else [
        OpenApiParameter(
            name=lista_emittente_param, type=int, required=False,
            description=(
                "Emittente del documento (PK). Lo legge SOLO il cancello di "
                "perimetro, per chi vede più emittenti: non filtra le righe e "
                "non allarga niente — la visibilità resta allo scope e alla RLS."
            ),
        ),
    ]
    return [
        *emittente,
        *parametri_filtri,
        param_ricerca_full(),
        OpenApiParameter(
            name="order_by", type=str, required=False,
            description=descrizione_order_by(colonne_ordinabili, f"Assente: {ordine_assente}"),
        ),
        OpenApiParameter(name="order_dir", type=str, required=False,
                         description="asc | desc (assente: asc; desc sulle date)"),
    ]


# Scopo: i filtri propri della lista nella forma di `filtri_applicati`
#        dell'export: solo quelli indicati, le date in ISO. None se nessuno.
def _filtri_applicati(filtri: Mapping[str, Any]) -> dict[str, Any] | None:
    applicati = {
        nome: valore.isoformat() if isinstance(valore, date) else valore
        for nome, valore in filtri.items()
        if valore is not None
    }
    return applicati or None


# Scopo: Costruisce la coppia (lista, export) di una lista figlia.
#        Parametri:
#         - schema_prefix:  prefisso dei nomi OpenAPI e delle classi
#                           ("PreventivoRighe" -> "ApiPreventivoRigheListaBase",
#                           "PreventivoRigheListaResponse")
#         - operation_id:   operationId della pagina; l'export aggiunge `_export`
#         - area_funzionale: l'area del padre (ne chiede il livello)
#         - url_kwarg:      kwarg URL del padre ("preventivo_id", "articolo_id"),
#                           passato al service cosi' come lo converte l'URL
#         - model_permission: oggetto dei permessi del padre: la lista ne e'
#                           una parte e ne chiede il livello
#         - pagina_call:    closure del dominio sul service di pagina
#         - colonne_ordinabili: la whitelist del repository, per la doc OpenAPI
#         - ordine_assente: la frase OpenAPI dell'ordine senza richiesta
#         - lista_emittente_param: vedi in testa (None: nessuno)
#         - con_scope:      passa al service `auth_user_id`
#         - filtri / parametri_filtri: i filtri propri della lista e la loro
#                           doc OpenAPI
def build_lista_figlia_views(
    *,
    schema_prefix: str,
    operation_id: str,
    area_funzionale: str,
    url_kwarg: str,
    model_permission: tuple[str, str],
    pagina_call: PaginaFiglia,
    colonne_ordinabili: Iterable[str],
    ordine_assente: str = "l'ordine del documento.",
    lista_emittente_param: str | None = None,
    con_scope: bool = False,
    filtri: LeggiFiltri | None = None,
    parametri_filtri: Sequence[OpenApiParameter] = (),
) -> tuple[type[DomainAPIView], type[DomainAPIView]]:
    parametri = _parametri(
        sorted(colonne_ordinabili),
        ordine_assente=ordine_assente,
        lista_emittente_param=lista_emittente_param,
        parametri_filtri=parametri_filtri,
    )

    # Scopo: gli argomenti che il service riceve oltre al contratto di lista:
    #        i filtri propri e lo scope dove il padre lo chiede. Una sede per
    #        le due view.
    def _filtri(request: Request) -> dict[str, Any]:
        return filtri(request.query_params) if filtri is not None else {}

    def _scope(request: Request) -> dict[str, Any]:
        return {"auth_user_id": get_scope_user_id(request)} if con_scope else {}

    class _Lista(DomainAPIView):
        is_search_endpoint = True

        @extend_schema(
            operation_id=operation_id,
            parameters=[
                *parametri,
                OpenApiParameter(name="limit", type=int, required=False),
                OpenApiParameter(name="offset", type=int, required=False),
            ],
            responses={200: inline_serializer(
                name=f"{schema_prefix}ListaResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: una pagina della lista figlia. Envelope paginato standard.
        def get(self, request: Request, **kwargs: Any) -> JsonResponse:
            # ⚠️ `default_order=""`: senza richiesta decide il repository
            #    (l'ordine del padre), non una colonna scelta qui.
            p = parse_list_params(request.query_params, default_order="")
            results, total = pagina_call(
                kwargs[url_kwarg],
                search=p["search"],
                order_by=p["order_by"],
                order_dir=p["order_dir"],
                limit=p["limit"],
                offset=p["offset"],
                **_filtri(request),
                **_scope(request),
            )
            return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    class _Export(DomainAPIView):
        is_search_endpoint = True
        # Lo scrive il dominio nella sottoclasse, come letterale (⭐ in testa).
        lista_codice: str

        @extend_schema(
            operation_id=f"{operation_id}_export",
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
        # Scopo: il file della lista figlia, con filtri, ricerca e ordinamento
        #        della lista a video. Legge fino a EXPORT_MAX_ROWS + 1 righe per
        #        accorgersi di un file troncato.
        def get(self, request: Request, **kwargs: Any) -> HttpResponse:
            fmt = parse_export_format(request)
            p = parse_list_params(request.query_params, default_order="")
            propri = _filtri(request)
            results, total = pagina_call(
                kwargs[url_kwarg],
                search=p["search"],
                order_by=p["order_by"],
                order_dir=p["order_dir"],
                limit=EXPORT_MAX_ROWS + 1,
                offset=0,
                max_limit=EXPORT_MAX_ROWS + 1,
                **propri,
                **_scope(request),
            )
            return build_export_response(
                request, lista_codice=self.lista_codice,
                results=results, total=total,
                filtri_applicati=_filtri_applicati(propri), fmt=fmt,
            )

    for classe, suffisso in ((_Lista, "ListaBase"), (_Export, "ListaExportBase")):
        classe.area_funzionale = area_funzionale
        classe.model_permission = model_permission
        if lista_emittente_param is not None:
            classe.lista_emittente_param = lista_emittente_param
        classe.__name__ = f"Api{schema_prefix}{suffisso}"
        classe.__qualname__ = classe.__name__
        classe.__doc__ = (
            f"GET …/{{{url_kwarg}}}/…/lista/{'export/' if classe is _Export else ''} — "
            "lista configurabile figlia del padre."
        )
    return _Lista, _Export
