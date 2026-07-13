# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per vendite.ordini (scheletro CRUD + conferma + push singolo).
#        Espone: lista DEF-8 + export, testata CRUD, righe + componenti BoM,
#        conferma (DRAFT->CONFERMATO) e push singolo a commessa. La transizione
#        di stato e' enforced dal trigger DB trgfn_ordini_guard_transizione_*;
#        il service traduce gli errori P0001 in ServiceError -> envelope uniforme.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    paginated_envelope,
    parse_list_params,
    qp_bool,
    qp_int_optional,
    qp_iso_date_optional,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api.indirizzi_documento_views import (
    build_indirizzi_documento_views,
)
from apps.vendite.api.riepilogo_iva_views import build_riepilogo_iva_view
from apps.vendite.services import ordini_service

# Codice lista configurabile (catalogo ui.lista_definizione id=7). Usato
# dall'export per risolvere colonne visibili/ordine/permessi dell'utente.
_LISTA_CODICE_ORDINI = "vendite.ordini"


# Scopo: Estrae i filtri lista comuni (list + export) dalla query string. NESSUN
#        default temporale backend: il default `data_da` (anno-1) lo applica la UI
#        (allineato a preventivi/offerte; evita non-determinismo `date.today()`
#        lato API).
def _extract_list_filters(qp) -> dict[str, Any]:
    return {
        "stato_codice": qp_str(qp.get("stato_codice_interno")),
        "billing_account_id": qp_int_optional(qp.get("billing_account_id"), "billing_account_id"),
        "utility_id": qp_int_optional(qp.get("utility_id"), "utility_id"),
        "data_da": qp_iso_date_optional(qp.get("data_da"), "data_da"),
        "data_al": qp_iso_date_optional(qp.get("data_a"), "data_a"),
    }


# Scopo: normalizza le `righe` da evadere dal body di genera-ddt. Assente/null =
#        tutto il residuo dell'ordine (None). Lista vuota = errore esplicito: NON
#        deve degradare silenziosamente a "tutto" (un client che intende "nessuna
#        riga" otterrebbe l'evasione completa). Ogni voce =
#        {ordine_riga_id, qta_da_evadere} in unita' operativa (qta passata
#        intatta alla fn DB fn_genera_ddt_da_ordine).
def _parse_righe_evasione(
    payload: dict[str, object],
) -> list[dict[str, Any]] | None:
    righe = payload.get("righe")
    if righe is None:
        return None
    ErrorManager.require(
        isinstance(righe, list) and len(righe) > 0,
        code="E_DDT_VALIDAZIONE",
        message="righe non valido: lista non vuota di {ordine_riga_id, "
                "qta_da_evadere}, oppure omettere il campo per evadere tutto "
                "il residuo.",
        detail=f"righe={righe!r}",
        function_name="apps.vendite.api.views_ordini._parse_righe_evasione",
    )
    out: list[dict[str, Any]] = []
    for r in righe:
        ErrorManager.require(
            isinstance(r, dict) and r.get("ordine_riga_id") is not None,
            code="E_DDT_VALIDAZIONE",
            message="Ogni riga richiede ordine_riga_id.",
            detail=f"riga={r!r}",
            function_name="apps.vendite.api.views_ordini._parse_righe_evasione",
        )
        assert isinstance(r, dict)
        out.append({
            "ordine_riga_id": int(r["ordine_riga_id"]),
            "qta_da_evadere": r.get("qta_da_evadere"),
        })
    return out


class ApiOrdiniList(DomainAPIView):
    """GET/POST /api/v1/vendite/ordini/ — lista paginata + create BOZZA."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_ordini_list",
        parameters=[
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False,
                             description="codice_interno stato (DRAFT | CONFERMATO | ...)"),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False,
                             description="Data ISO; default anno-1."),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="campo_sorgente catalogo 'vendite.ordini' "
                                         "(numero | data | ragione_sociale_completa | "
                                         "ba_codice | utility_codice | totale_doc | "
                                         "fatturazione_trigger | stato_descrizione)."),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeOrdiniListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata ordini con filtri standard + scope emittente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data")
        f = _extract_list_filters(qp)
        results, total = ordini_service.list_ordini_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            **f,
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    # Scopo: Crea nuovo ordine in stato BOZZA (DRAFT).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=ordini_service.crea_ordine)


class ApiOrdiniExportView(DomainAPIView):
    """GET /api/v1/vendite/ordini/export/?formato=csv|xlsx (DEF-1).

    NB: parametro `formato` (italiano), NON `format` (magic param DRF —
    memoria feedback_drf_format_magic_param).
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_ordini_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Export CSV/XLSX della lista ordini. Filtri identici al list endpoint;
    #        fetcha fino a EXPORT_MAX_ROWS+1 per intercettare l'overflow.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)
        p = parse_list_params(qp, default_order="data")
        f = _extract_list_filters(qp)
        results, total = ordini_service.list_ordini_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            **f,
        )
        filtri_applicati = ordini_service.resolve_filtri_export_label(
            search=p["search"],
            stato_codice=f["stato_codice"],
            billing_account_id=f["billing_account_id"],
            utility_id=f["utility_id"],
            data_da=f["data_da"],
            data_al=f["data_al"],
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_ORDINI,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


class ApiOrdineDetail(DomainAPIView):
    """GET/PATCH/DELETE /api/v1/vendite/ordini/<ordine_id>/."""

    area_funzionale = "vendite"

    # Scopo: Dettaglio testata ordine + capability.
    def get(self, request: Request, ordine_id: int) -> JsonResponse:
        return success_response(ordini_service.get_ordine(int(ordine_id)))

    # Scopo: Aggiorna testata ordine (solo DRAFT). PATCH usa request.data
    #        (api.md §handle_post_json vs request.data): DRF ha gia' parsato il
    #        body; handle_post_json rileggerebbe il raw consumato.
    def patch(self, request: Request, ordine_id: int) -> JsonResponse:
        return success_response(
            ordini_service.aggiorna_ordine(int(ordine_id), dict(request.data)),
        )

    # Scopo: Hard-delete ordine (abbandono bozza, solo DRAFT).
    def delete(self, request: Request, ordine_id: int) -> JsonResponse:
        return success_response(ordini_service.elimina_ordine(int(ordine_id)))


class ApiOrdinePerPratica(DomainAPIView):
    """`GET /api/v1/vendite/ordini/per-pratica/?pratica_id=<id>`: risolve
    l'ordine COLLEGATO a una pratica (agganciato da PostSmistamentoHandler).
    Alimenta gli step a valle del percorso (CONFERMA_ORDINE / INVIO_COMMESSA)
    che aprono l'OrdiniDrawer su quell'ordine. Ritorna `{"ordine_id": <id|null>}`."""

    area_funzionale = "vendite"

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
            name="OrdinePerPraticaResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    def get(self, request: Request) -> JsonResponse:
        pratica_id = qp_int_optional(request.query_params.get("pratica_id"), "pratica_id")
        ErrorManager.require(
            pratica_id is not None,
            code="E_PRATICA_ID_OBBLIGATORIO",
            message="pratica_id obbligatorio.",
        )
        assert pratica_id is not None
        return success_response(ordini_service.get_ordine_per_pratica(pratica_id))


class ApiOrdineConferma(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/conferma/ (DRAFT->CONFERMATO)."""

    area_funzionale = "vendite"

    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        user = getattr(request.user, "username", None) or None
        return success_response(ordini_service.conferma(int(ordine_id), user=user))


class ApiOrdinePush(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/push/ — push singolo a commessa."""

    area_funzionale = "vendite"

    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        user = getattr(request.user, "username", None) or None
        return success_response(ordini_service.push_a_commessa(int(ordine_id), user=user))


class ApiOrdineCambiaStato(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/cambia-stato/ — transizione di
    stato data-driven (es. annulla). Body: `stato_codice` (= `target_state`
    dell'azione). L'ammissibilita' e' validata dal trigger guard DB."""

    area_funzionale = "vendite"

    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: ordini_service.cambia_stato(
                int(ordine_id), payload.get("stato_codice"),
            ),
        )


# View dal factory condiviso `build_indirizzi_documento_views` (pannello
# indirizzi slot-per-tipo, design brief-design-indirizzi-documenti-vendita).
_indirizzi_views = build_indirizzi_documento_views(
    schema_prefix="Ordine",
    url_kwarg="ordine_id",
    list_call=lambda ordine_id: ordini_service.list_indirizzi(ordine_id),
    upsert_call=lambda ordine_id, payload: ordini_service.upsert_indirizzo(
        ordine_id, payload),
    delete_call=lambda ordine_id, indirizzo_id: ordini_service.delete_indirizzo(
        ordine_id, indirizzo_id),
)
ApiOrdineIndirizzi = _indirizzi_views.lista
ApiOrdineIndirizzoDetail = _indirizzi_views.detail


# View dal factory condiviso `build_riepilogo_iva_view` (estrazione
# regola-del-2 dei cloni preventivi/ordini/ddt). La closure legge il global
# di modulo a call-time: i patch dei test sul service restano validi.
ApiOrdineRiepilogoIva = build_riepilogo_iva_view(
    schema_prefix="Ordine",
    url_kwarg="ordine_id",
    list_call=lambda ordine_id: ordini_service.list_riepilogo_iva(ordine_id),
    doc="""GET /api/v1/vendite/ordini/<id>/riepilogo-iva/

    Restituisce il riepilogo IVA dell'ordine: una riga per gruppo aliquota
    (natura/esigibilita/split sempre NULL) con imponibile e imposta aggregati
    e arrotondati a 2 decimali sull'aggregato per aliquota (regola fiscale:
    DPR 633/72 art. 21 + DM 24/12/93, identica ai preventivi). Lettura pura
    dalla view derivata `vendite.vw_ordini_riepilogo_iva_dettaglio`, nessun
    side-effect: i totali di testata sono mantenuti dal trigger su ordini_righe
    via fn_ricalcola_totali_ordine.

    Area `vendite` livello LETTURA sufficiente.
    """,
)


class ApiOrdineRighe(DomainAPIView):
    """GET/POST /api/v1/vendite/ordini/<ordine_id>/righe/."""

    area_funzionale = "vendite"

    # Scopo: Lista righe dell'ordine.
    def get(self, request: Request, ordine_id: int) -> JsonResponse:
        return success_response(ordini_service.list_righe(int(ordine_id)))

    # Scopo: Aggiunge una riga (solo DRAFT). Pricing via BB condiviso.
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        auth_user_id = get_scope_user_id(request)
        return handle_post_json(
            request,
            handler=lambda payload: ordini_service.gestisci_riga(
                int(ordine_id), payload, auth_user_id=auth_user_id,
            ),
        )


class ApiOrdineRigaDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/ordini/<ordine_id>/righe/<riga_id>/."""

    area_funzionale = "vendite"

    def patch(self, request: Request, ordine_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            ordini_service.aggiorna_riga(
                int(ordine_id), int(riga_id), dict(request.data),
                auth_user_id=get_scope_user_id(request),
            ),
        )

    def delete(self, request: Request, ordine_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            ordini_service.elimina_riga(int(ordine_id), int(riga_id)),
        )


class ApiOrdineRigaPreviewComponenti(DomainAPIView):
    """POST /api/v1/vendite/ordini/<ordine_id>/righe/preview-componenti/.

    Preview read-only dei componenti BoM per il drawer riga (pre-save).
    """

    area_funzionale = "vendite"

    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        auth_user_id = get_scope_user_id(request)

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            righe = ordini_service.preview_componenti_riga(
                int(ordine_id),
                articolo_id=str(payload.get("articolo_id")),
                uom_operativa_id=payload.get("uom_operativa_id"),
                quantita=payload.get("quantita"),
                auth_user_id=auth_user_id,
            )
            return {"componenti": righe}

        return handle_post_json(request, handler=_handler)


class ApiOrdineRigaComponentiList(DomainAPIView):
    """GET /api/v1/vendite/ordini/<ordine_id>/righe/<riga_id>/componenti/."""

    area_funzionale = "vendite"

    def get(self, request: Request, ordine_id: int, riga_id: int) -> JsonResponse:
        solo_attivi = qp_bool(request.query_params.get("solo_attivi"), default=True)
        return success_response(
            ordini_service.list_componenti_riga(
                int(ordine_id), int(riga_id), solo_attivi=solo_attivi,
            ),
        )


class ApiOrdineRigaComponenteDetail(DomainAPIView):
    """PATCH/DELETE /.../righe/<riga_id>/componenti/<componente_id>/."""

    area_funzionale = "vendite"

    def patch(
        self, request: Request, ordine_id: int, riga_id: int, componente_id: int,
    ) -> JsonResponse:
        return success_response(
            ordini_service.update_componente(
                int(ordine_id), int(riga_id), int(componente_id), dict(request.data),
            ),
        )

    def delete(
        self, request: Request, ordine_id: int, riga_id: int, componente_id: int,
    ) -> JsonResponse:
        return success_response(
            ordini_service.delete_componente(
                int(ordine_id), int(riga_id), int(componente_id),
            ),
        )


class ApiOrdineGeneraDdt(DomainAPIView):
    """`POST /api/v1/vendite/ordini/<ordine_id>/genera-ddt/` — evasione: genera
    un DDT (DRAFT) dall'ordine copiando lo snapshot righe/componenti + il
    fulfillment riga<->riga e proiettando lo stato ordine (CONFERMATO /
    PARZIALMENTE_EVASO / EVASO). L'endpoint vive nel dominio SORGENTE (ordine),
    la logica sta in `ddt_service` (stesso app vendite, come genera-ordine sta
    nei preventivi). Body opzionale `{righe: [{ordine_riga_id, qta_da_evadere}]}`
    (unita' operativa) per l'evasione parziale/selettiva; assente = tutto il
    residuo."""

    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="OrdineGeneraDdtResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Genera un DDT da evasione dell'ordine. Delega a ddt_service (import
    #        locale per evitare cicli). Ritorna {ddt_id, numero, ordine_id}.
    def post(self, request: Request, ordine_id: int) -> JsonResponse:
        from apps.vendite.services import ddt_service

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return ddt_service.crea_ddt_da_ordine(
                int(ordine_id), _parse_righe_evasione(payload),
            )
        return handle_post_json(request, handler=_handler)
