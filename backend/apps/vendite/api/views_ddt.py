# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per vendite.ddt (CRUD testata + righe + componenti BoM,
#        cambio stato data-driven, push singolo a commessa). Clone
#        strutturale di views_ordini: la transizione di stato e' enforced dal
#        trigger DB trgfn_ddt_guard_transizione; il service traduce gli errori
#        P0001 in ServiceError -> envelope uniforme. Nessun post_permission
#        (solo area_funzionale, come ordini). Numero assegnato a EMESSO dal
#        trigger DB (non passato dal client). L'EMISSIONE (DRAFT->EMESSO +
#        genera PDF, multipart) vive in `ddt_documenti_views.ApiDdtEmetti`
#        (mirror ordini).
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
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api.indirizzi_documento_views import (
    build_indirizzi_documento_views,
)
from apps.vendite.api.riepilogo_iva_views import build_riepilogo_iva_view
from apps.vendite.services import ddt_service

# Codice lista (ui.lista_definizione) usato dall'export per risolvere
# colonne visibili/ordine/permessi dell'utente.
_LISTA_CODICE_DDT = "vendite.ddt"


# Scopo: Estrae i filtri lista comuni dalla query string. NESSUN default
#        temporale backend: il default `data_da` (anno-1) lo applica la UI
#        (allineato a ordini/preventivi; evita non-determinismo `date.today()`).
def _extract_list_filters(qp) -> dict[str, Any]:
    return {
        "stato_codice": qp_str(qp.get("stato_codice_interno")),
        "billing_account_id": qp_int_optional(qp.get("billing_account_id"), "billing_account_id"),
        "utility_id": qp_int_optional(qp.get("utility_id"), "utility_id"),
        "data_da": qp_iso_date_optional(qp.get("data_da"), "data_da"),
        "data_al": qp_iso_date_optional(qp.get("data_a"), "data_a"),
    }


class ApiDdtList(DomainAPIView):
    """GET/POST /api/v1/vendite/ddt/ — lista paginata + create BOZZA standalone."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_ddt_list",
        parameters=[
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False,
                             description="codice_interno stato (DRAFT | EMESSO | SPEDITO | ...)"),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False,
                             description="Data ISO; default anno-1."),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="campo_sorgente catalogo 'vendite.ddt' "
                                         "(numero | data | destinatario_denominazione | "
                                         "ba_codice | stato_descrizione | ...)."),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeDdtListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata DDT con filtri standard + scope emittente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data")
        f = _extract_list_filters(qp)
        results, total = ddt_service.list_ddt_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            **f,
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    # Scopo: Crea nuovo DDT standalone in stato BOZZA (DRAFT).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=ddt_service.crea_ddt)


class ApiDdtExportView(DomainAPIView):
    """GET /api/v1/vendite/ddt/export/?formato=csv|xlsx (DEF-1).

    NB: parametro `formato` (italiano), NON `format` (magic param DRF —
    memoria feedback_drf_format_magic_param).
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_ddt_export",
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
    # Scopo: Export CSV/XLSX della lista DDT. Filtri identici al list endpoint;
    #        fetcha fino a EXPORT_MAX_ROWS+1 per intercettare l'overflow.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)
        p = parse_list_params(qp, default_order="data")
        f = _extract_list_filters(qp)
        results, total = ddt_service.list_ddt_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            **f,
        )
        filtri_applicati = ddt_service.resolve_filtri_export_label(
            search=p["search"],
            stato_codice=f["stato_codice"],
            billing_account_id=f["billing_account_id"],
            utility_id=f["utility_id"],
            data_da=f["data_da"],
            data_al=f["data_al"],
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_DDT,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


class ApiDdtDetail(DomainAPIView):
    """GET/PATCH/DELETE /api/v1/vendite/ddt/<ddt_id>/."""

    area_funzionale = "vendite"

    # Scopo: Dettaglio testata DDT + capability.
    def get(self, request: Request, ddt_id: int) -> JsonResponse:
        return success_response(ddt_service.get_ddt(int(ddt_id)))

    # Scopo: Aggiorna testata DDT (solo DRAFT). PATCH usa request.data (DRF ha
    #        gia' parsato il body; handle_post_json rileggerebbe il raw consumato).
    def patch(self, request: Request, ddt_id: int) -> JsonResponse:
        return success_response(
            ddt_service.aggiorna_ddt(int(ddt_id), dict(request.data)),
        )

    # Scopo: Hard-delete DDT (abbandono bozza, solo DRAFT + 0 righe).
    def delete(self, request: Request, ddt_id: int) -> JsonResponse:
        return success_response(ddt_service.elimina_ddt(int(ddt_id)))


class ApiDdtCambiaStato(DomainAPIView):
    """POST /api/v1/vendite/ddt/<ddt_id>/cambia-stato/ — transizione di stato
    data-driven (SPEDITO / CONSEGNATO / RESO / ANNULLATO). Body: `stato_codice`
    (= `target_state` dell'azione). L'ammissibilita' e' validata dal trigger
    guard DB."""

    area_funzionale = "vendite"

    # Scopo: Esegue la transizione di stato richiesta (validata dal trigger DB).
    def post(self, request: Request, ddt_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: ddt_service.cambia_stato(
                int(ddt_id), payload.get("stato_codice"),
            ),
        )


class ApiDdtPush(DomainAPIView):
    """POST /api/v1/vendite/ddt/<ddt_id>/push/ — push singolo a commessa
    (sorgente DDT_VENDITA, fatturazione differita)."""

    area_funzionale = "vendite"

    # Scopo: Push singolo del DDT a commessa (sorgente DDT_VENDITA).
    def post(self, request: Request, ddt_id: int) -> JsonResponse:
        user = getattr(request.user, "username", None) or None
        return success_response(ddt_service.push_a_commessa(int(ddt_id), user=user))


# View dal factory condiviso `build_indirizzi_documento_views` (pannello
# indirizzi slot-per-tipo, design brief-design-indirizzi-documenti-vendita).
# Closure sul modulo: i patch dei test su ddt_service.* restano validi.
_indirizzi_views = build_indirizzi_documento_views(
    schema_prefix="Ddt",
    url_kwarg="ddt_id",
    list_call=lambda ddt_id: ddt_service.list_indirizzi(ddt_id),
    upsert_call=lambda ddt_id, payload: ddt_service.upsert_indirizzo(ddt_id, payload),
    delete_call=lambda ddt_id, indirizzo_id: ddt_service.delete_indirizzo(
        ddt_id, indirizzo_id),
)
ApiDdtIndirizzi = _indirizzi_views.lista
ApiDdtIndirizzoDetail = _indirizzi_views.detail


# View dal factory condiviso `build_riepilogo_iva_view` (estrazione
# regola-del-2 dei cloni preventivi/ordini/ddt). La closure legge il global
# di modulo a call-time: i patch dei test sul service restano validi.
ApiDdtRiepilogoIva = build_riepilogo_iva_view(
    schema_prefix="Ddt",
    url_kwarg="ddt_id",
    list_call=lambda ddt_id: ddt_service.list_riepilogo_iva(ddt_id),
    doc="""GET /api/v1/vendite/ddt/<id>/riepilogo-iva/

    Restituisce il riepilogo IVA del DDT: una riga per gruppo aliquota
    (natura/esigibilita/split sempre NULL) con imponibile e imposta aggregati
    e arrotondati a 2 decimali sull'aggregato per aliquota (regola fiscale:
    DPR 633/72 art. 21 + DM 24/12/93, identica a preventivi/ordini). Lettura
    pura dalla view derivata `vendite.vw_ddt_riepilogo_iva_dettaglio`, nessun
    side-effect; le righe con prezzo NULL (DDT solo di trasporto) sono escluse
    in vista: DDT non valorizzato -> riepilogo vuoto.

    Area `vendite` livello LETTURA sufficiente.
    """,
)


class ApiDdtRighe(DomainAPIView):
    """GET/POST /api/v1/vendite/ddt/<ddt_id>/righe/."""

    area_funzionale = "vendite"

    # Scopo: Lista righe del DDT.
    def get(self, request: Request, ddt_id: int) -> JsonResponse:
        return success_response(ddt_service.list_righe(int(ddt_id)))

    # Scopo: Aggiunge una riga (solo DRAFT). Pricing via BB condiviso.
    def post(self, request: Request, ddt_id: int) -> JsonResponse:
        auth_user_id = get_scope_user_id(request)
        return handle_post_json(
            request,
            handler=lambda payload: ddt_service.gestisci_riga(
                int(ddt_id), payload, auth_user_id=auth_user_id,
            ),
        )


class ApiDdtRigaDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/ddt/<ddt_id>/righe/<riga_id>/."""

    area_funzionale = "vendite"

    # Scopo: Aggiorna una riga del DDT (solo DRAFT).
    def patch(self, request: Request, ddt_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            ddt_service.aggiorna_riga(
                int(ddt_id), int(riga_id), dict(request.data),
                auth_user_id=get_scope_user_id(request),
            ),
        )

    # Scopo: Elimina una riga del DDT (hard delete, solo DRAFT).
    def delete(self, request: Request, ddt_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            ddt_service.elimina_riga(int(ddt_id), int(riga_id)),
        )


class ApiDdtRigaPreviewComponenti(DomainAPIView):
    """POST /api/v1/vendite/ddt/<ddt_id>/righe/preview-componenti/.

    Preview read-only dei componenti BoM per il drawer riga (pre-save).
    """

    area_funzionale = "vendite"

    # Scopo: Preview read-only dei componenti BoM (nessuna persistenza: il gate
    #        L1 sugli override e' applicato al salvataggio riga).
    def post(self, request: Request, ddt_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            righe = ddt_service.preview_componenti_riga(
                int(ddt_id),
                articolo_id=str(payload.get("articolo_id")),
                uom_operativa_id=payload.get("uom_operativa_id"),
                quantita=payload.get("quantita"),
            )
            return {"componenti": righe}

        return handle_post_json(request, handler=_handler)


class ApiDdtRigaComponentiList(DomainAPIView):
    """GET /api/v1/vendite/ddt/<ddt_id>/righe/<riga_id>/componenti/."""

    area_funzionale = "vendite"

    # Scopo: Lista componenti BoM persistiti della riga.
    def get(self, request: Request, ddt_id: int, riga_id: int) -> JsonResponse:
        solo_attivi = qp_bool(request.query_params.get("solo_attivi"), default=True)
        return success_response(
            ddt_service.list_componenti_riga(
                int(ddt_id), int(riga_id), solo_attivi=solo_attivi,
            ),
        )


class ApiDdtRigaComponenteDetail(DomainAPIView):
    """PATCH/DELETE /.../righe/<riga_id>/componenti/<componente_id>/."""

    area_funzionale = "vendite"

    # Scopo: Aggiorna un componente BoM (prezzo/attivo/meta, solo DRAFT).
    def patch(
        self, request: Request, ddt_id: int, riga_id: int, componente_id: int,
    ) -> JsonResponse:
        return success_response(
            ddt_service.update_componente(
                int(ddt_id), int(riga_id), int(componente_id), dict(request.data),
            ),
        )

    # Scopo: Disattiva (soft) un componente BoM (solo DRAFT).
    def delete(
        self, request: Request, ddt_id: int, riga_id: int, componente_id: int,
    ) -> JsonResponse:
        return success_response(
            ddt_service.delete_componente(
                int(ddt_id), int(riga_id), int(componente_id),
            ),
        )
