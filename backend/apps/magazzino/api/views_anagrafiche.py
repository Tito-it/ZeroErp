# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API delle tre ANAGRAFICHE di `magazzino` — magazzini, ubicazioni
#        (sotto `magazzini/<id>/ubicazioni/`), lotti (`lotti/?articolo_id=`):
#        lista offset-based + export, crea, dettaglio + PATCH.
# Note: Grammatica URL di `api.md`: il metodo dice l'operazione, il path la
#       risorsa. Nessuna azione di dominio: disattivare e' un `PATCH
#       {attivo: false}` (e il DB decide, con i suoi `block_deact`).
#
#       ⚠️ Le POST che creano pretendono l'`Idempotency-Key` (il client la
#       manda da `idem()` in `api/magazzino.js`): un doppio click non fa due
#       magazzini.
#
#       ⚠️ Le liste sono OFFSET-based (`limit`/`offset`, `{count, results}`),
#       la lingua di `<ListaConfigurabile>`; `order_by`/`order_dir` passano
#       GREZZI (api.md §parse_list_params), come in `views.py`.
#
#       ⭐ `lista_codice` su magazzini e ubicazioni (il perimetro e' l'emittente
#       del magazzino). ⛔ NON sui lotti: `magazzino.lotti` e' a catalogo con
#       `perimetro_emittente = false` (un lotto e' dell'articolo, nessun
#       `emittente_fiscale_id` in tabella) e l'export riceve il codice da una
#       costante di modulo — la forma di `views_famiglie.py`. Registro:
#       `test_perimetro_emittente_copertura._ESENZIONI`.
#
#       Piano: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config §4-6.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_detail_patch, handle_post_json
from apps.core.api.payload_validators import (
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_str,
)
from apps.core.api.search_validators import require_min_search_length
from apps.core.api.success_responses import success_response
from apps.magazzino.api._comuni import (
    AREA,
    PARAM_FORMATO,
    RISPOSTA_GENERICA,
    RISPOSTE_EXPORT,
    filtri_label,
    params_lista,
)
from apps.magazzino.db.anagrafiche_magazzino_repository import (
    LOTTI_SORT_COLUMNS,
    MAGAZZINI_SORT_COLUMNS,
    UBICAZIONI_SORT_COLUMNS,
)
from apps.magazzino.services import anagrafiche_magazzino_service as svc
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.core.api.openapi_params import param_ricerca_full

# I codici delle liste a catalogo, in costanti di modulo: li leggono la lista,
# l'export e il presidio di copertura del perimetro (che risolve un `Name`
# dello stesso modulo, non un `Attribute` di un'altra classe). Per i lotti il
# codice va SOLO a `build_export_response`, non come attributo di classe —
# vedi la nota in testa (perimetro_emittente = false).
_LISTA_MAGAZZINI = "magazzino.magazzini"
_LISTA_UBICAZIONI = "magazzino.ubicazioni"
_LISTA_LOTTI = "magazzino.lotti"

# Sotto soglia la view risponde 400 (`require_min_search_length`).
_PARAM_SEARCH = param_ricerca_full(rifiuta_sotto_soglia=True)
_PARAM_ATTIVO = OpenApiParameter(
    name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False,
    description="Assente = tutte, spente comprese; `true` = solo attive.",
)


# Scopo: i filtri comuni alle tre liste: ricerca libera e flag attivo.
def _filtri_anagrafica(qp) -> dict:
    search = qp_str(qp.get("search"))
    if search:
        require_min_search_length(search)
    return {
        "search": search,
        "attivo": qp_bool_optional(qp.get("attivo"), "attivo"),
    }


# Scopo: l'ordinamento GREZZO dalla query string (il service valida).
def _ordinamento(qp) -> dict:
    return {"order_by": qp_str(qp.get("order_by")), "order_dir": qp_str(qp.get("order_dir"))}


# ══════════════════════════════════════════════════════════════════
#  Magazzini
# ══════════════════════════════════════════════════════════════════

class ApiMagazziniList(DomainAPIView):
    """GET lista / POST crea — /api/v1/magazzino/magazzini/."""

    area_funzionale = AREA
    is_search_endpoint = True
    lista_codice = _LISTA_MAGAZZINI

    @extend_schema(
        operation_id="magazzino_magazzini_list",
        parameters=[_PARAM_SEARCH, _PARAM_ATTIVO, *params_lista(MAGAZZINI_SORT_COLUMNS, "Senza: codice.")],
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: I magazzini del perimetro, paginati.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(svc.list_magazzini(
            auth_user_id=get_scope_user_id(request),
            **_filtri_anagrafica(qp), **_ordinamento(qp),
            limit=p["limit"], offset=p["offset"],
        ))

    @extend_schema(operation_id="magazzino_magazzini_create", responses={200: RISPOSTA_GENERICA})
    # Scopo: Crea un magazzino (l'emittente lo mette il DB dalla GUC).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=svc.crea_magazzino, require_idempotency_key=True)


class ApiMagazziniExport(DomainAPIView):
    """GET /api/v1/magazzino/magazzini/export/ — CSV/XLSX."""

    area_funzionale = AREA
    lista_codice = _LISTA_MAGAZZINI

    @extend_schema(
        operation_id="magazzino_magazzini_export",
        parameters=[PARAM_FORMATO, _PARAM_SEARCH, _PARAM_ATTIVO, *params_lista(MAGAZZINI_SORT_COLUMNS, "")],
        responses=RISPOSTE_EXPORT,
    )
    # Scopo: Il file dei magazzini: il DATASET, non la pagina.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        filtri = _filtri_anagrafica(qp)
        dati = svc.list_magazzini(
            auth_user_id=get_scope_user_id(request), **filtri, **_ordinamento(qp),
            limit=EXPORT_MAX_ROWS + 1, offset=0,
        )
        return build_export_response(
            request, lista_codice=self.lista_codice,
            results=dati["results"], total=dati["count"],
            filtri_applicati=filtri_label(filtri) or None, fmt=fmt,
        )


class ApiMagazzinoDetail(DomainAPIView):
    """GET dettaglio / PATCH — /api/v1/magazzino/magazzini/<id>/."""

    area_funzionale = AREA

    @extend_schema(operation_id="magazzino_magazzini_detail", responses={200: RISPOSTA_GENERICA})
    # Scopo: Il magazzino; 404 no-leak fuori perimetro.
    def get(self, request: Request, magazzino_id: int) -> JsonResponse:
        return success_response(svc.get_magazzino(magazzino_id))

    @extend_schema(operation_id="magazzino_magazzini_update", responses={200: RISPOSTA_GENERICA})
    # Scopo: Aggiorna per delta (compreso `attivo`: disattiva/riattiva).
    def patch(self, request: Request, magazzino_id: int) -> JsonResponse:
        return handle_detail_patch(request, svc.aggiorna_magazzino, magazzino_id)


# ══════════════════════════════════════════════════════════════════
#  Ubicazioni (figlie del magazzino)
# ══════════════════════════════════════════════════════════════════

_PARAM_PARENT = OpenApiParameter(
    name="parent_id", type=int, location=OpenApiParameter.QUERY, required=False,
    description="Solo le figlie dirette di questa ubicazione.",
)


class ApiUbicazioniList(DomainAPIView):
    """GET lista / POST crea — /api/v1/magazzino/magazzini/<id>/ubicazioni/."""

    area_funzionale = AREA
    is_search_endpoint = True
    lista_codice = _LISTA_UBICAZIONI

    @extend_schema(
        operation_id="magazzino_ubicazioni_list",
        parameters=[_PARAM_SEARCH, _PARAM_ATTIVO, _PARAM_PARENT, *params_lista(UBICAZIONI_SORT_COLUMNS, "Senza: codice.")],
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: Le ubicazioni del magazzino, paginate (404 sulla testata prima).
    def get(self, request: Request, magazzino_id: int) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(svc.list_ubicazioni(
            magazzino_id,
            **_filtri_anagrafica(qp), **_ordinamento(qp),
            parent_id=qp_int_optional(qp.get("parent_id"), "parent_id"),
            limit=p["limit"], offset=p["offset"],
        ))

    @extend_schema(operation_id="magazzino_ubicazioni_create", responses={200: RISPOSTA_GENERICA})
    # Scopo: Crea un'ubicazione nel magazzino del path.
    def post(self, request: Request, magazzino_id: int) -> JsonResponse:
        return handle_post_json(
            request, handler=lambda p: svc.crea_ubicazione(magazzino_id, p), require_idempotency_key=True,
        )


class ApiUbicazioniExport(DomainAPIView):
    """GET /api/v1/magazzino/magazzini/<id>/ubicazioni/export/ — CSV/XLSX."""

    area_funzionale = AREA
    lista_codice = _LISTA_UBICAZIONI

    @extend_schema(
        operation_id="magazzino_ubicazioni_export",
        parameters=[PARAM_FORMATO, _PARAM_SEARCH, _PARAM_ATTIVO, _PARAM_PARENT, *params_lista(UBICAZIONI_SORT_COLUMNS, "")],
        responses=RISPOSTE_EXPORT,
    )
    # Scopo: Il file delle ubicazioni del magazzino.
    def get(self, request: Request, magazzino_id: int) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        filtri = {**_filtri_anagrafica(qp), "parent_id": qp_int_optional(qp.get("parent_id"), "parent_id")}
        dati = svc.list_ubicazioni(
            magazzino_id, **filtri, **_ordinamento(qp), limit=EXPORT_MAX_ROWS + 1, offset=0,
        )
        return build_export_response(
            request, lista_codice=self.lista_codice,
            results=dati["results"], total=dati["count"],
            filtri_applicati=filtri_label({"magazzino_id": magazzino_id, **filtri}) or None, fmt=fmt,
        )


class ApiUbicazioneDetail(DomainAPIView):
    """GET dettaglio / PATCH — /api/v1/magazzino/magazzini/<id>/ubicazioni/<uid>/."""

    area_funzionale = AREA

    @extend_schema(operation_id="magazzino_ubicazioni_detail", responses={200: RISPOSTA_GENERICA})
    # Scopo: L'ubicazione del magazzino; 404 sulla coppia.
    def get(self, request: Request, magazzino_id: int, ubicazione_id: int) -> JsonResponse:
        return success_response(svc.get_ubicazione(magazzino_id, ubicazione_id))

    @extend_schema(operation_id="magazzino_ubicazioni_update", responses={200: RISPOSTA_GENERICA})
    # Scopo: Aggiorna per delta. ⚠️ Non `handle_detail_patch`: la risorsa e'
    #        la COPPIA (magazzino, ubicazione) e il BB conosce una sola chiave.
    def patch(self, request: Request, magazzino_id: int, ubicazione_id: int) -> JsonResponse:
        return handle_post_json(
            request, handler=lambda p: svc.aggiorna_ubicazione(magazzino_id, ubicazione_id, p),
        )


# ══════════════════════════════════════════════════════════════════
#  Lotti (figli dell'articolo)
# ══════════════════════════════════════════════════════════════════

_PARAM_ARTICOLO = OpenApiParameter(
    name="articolo_id", type=str, location=OpenApiParameter.QUERY, required=True,
    description="L'articolo (uuid), OBBLIGATORIO: i lotti si leggono per articolo.",
)


class ApiLottiList(DomainAPIView):
    """GET lista / POST crea — /api/v1/magazzino/lotti/?articolo_id=."""

    area_funzionale = AREA
    is_search_endpoint = True

    @extend_schema(
        operation_id="magazzino_lotti_list",
        parameters=[_PARAM_ARTICOLO, _PARAM_SEARCH, _PARAM_ATTIVO, *params_lista(LOTTI_SORT_COLUMNS, "Senza: data_arrivo DESC.")],
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: I lotti dell'articolo, paginati.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(svc.list_lotti(
            articolo_id=qp.get("articolo_id"),
            **_filtri_anagrafica(qp), **_ordinamento(qp),
            limit=p["limit"], offset=p["offset"],
        ))

    @extend_schema(operation_id="magazzino_lotti_create", responses={200: RISPOSTA_GENERICA})
    # Scopo: Crea un lotto (`articolo_id` nel payload).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=svc.crea_lotto, require_idempotency_key=True)


class ApiLottiExport(DomainAPIView):
    """GET /api/v1/magazzino/lotti/export/?articolo_id= — CSV/XLSX."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="magazzino_lotti_export",
        parameters=[PARAM_FORMATO, _PARAM_ARTICOLO, _PARAM_SEARCH, _PARAM_ATTIVO, *params_lista(LOTTI_SORT_COLUMNS, "")],
        responses=RISPOSTE_EXPORT,
    )
    # Scopo: Il file dei lotti dell'articolo.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        filtri = {"articolo_id": qp.get("articolo_id"), **_filtri_anagrafica(qp)}
        dati = svc.list_lotti(**filtri, **_ordinamento(qp), limit=EXPORT_MAX_ROWS + 1, offset=0)
        return build_export_response(
            request, lista_codice=_LISTA_LOTTI,
            results=dati["results"], total=dati["count"],
            filtri_applicati=filtri_label(filtri) or None, fmt=fmt,
        )


class ApiLottoDetail(DomainAPIView):
    """GET dettaglio / PATCH — /api/v1/magazzino/lotti/<id>/."""

    area_funzionale = AREA

    @extend_schema(operation_id="magazzino_lotti_detail", responses={200: RISPOSTA_GENERICA})
    # Scopo: Il lotto; 404.
    def get(self, request: Request, lotto_id: int) -> JsonResponse:
        return success_response(svc.get_lotto(lotto_id))

    @extend_schema(operation_id="magazzino_lotti_update", responses={200: RISPOSTA_GENERICA})
    # Scopo: Aggiorna per delta.
    def patch(self, request: Request, lotto_id: int) -> JsonResponse:
        return handle_detail_patch(request, svc.aggiorna_lotto, lotto_id)
