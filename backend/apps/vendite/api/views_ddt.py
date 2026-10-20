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
from apps.core.api.endpoint_helpers import get_actor_user_id, get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    paginated_envelope,
    parse_list_params,
    qp_bool,
)
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api._list_filters_helpers import extract_doc_list_filters
from apps.vendite.api.indirizzi_documento_views import (
    build_indirizzi_documento_views,
)
from apps.vendite.api.riepilogo_iva_views import build_riepilogo_iva_view
from apps.vendite.services import ddt_service
from apps.ui.api.lista_figlia_views import EMITTENTE_DOCUMENTO_PARAM, build_lista_figlia_views
from apps.vendite.db.ddt_repository import DdtRepository
from apps.core.api.openapi_params import param_ricerca_full
from apps.vendite.api._componenti_schema import (
    COMPONENTE_PATCH_REQUEST,
    COMPONENTI_LIST_PARAMETERS,
    COMPONENTI_LIST_RESPONSE,
    PREVIEW_COMPONENTI_REQUEST,
    PREVIEW_COMPONENTI_RESPONSE,
    componenti_overrides_field,
)
from apps.vendite.api._schema_da_contratto import (
    CAMBIA_STATO_CON_CONFERMA_REQUEST,
    schema_da_contratto,
)

# Codice lista (ui.lista_definizione) usato dall'export per risolvere
# colonne visibili/ordine/permessi dell'utente.
_LISTA_CODICE_DDT = "vendite.ddt"


# ── Schemi OpenAPI dei corpi: le chiavi dal contratto del service ──────────
_DDT_CREATE_REQUEST = schema_da_contratto(
    "VenditeDdtCreateReq", ddt_service.CREATE_KEYS_DDT,
    obbligatorie=("billing_account_id",),
)
_DDT_UPDATE_REQUEST = schema_da_contratto(
    "VenditeDdtUpdateReq", ddt_service.UPDATE_KEYS_DDT,
)
_DDT_RIGA_CREATE_REQUEST = schema_da_contratto(
    "VenditeDdtRigaCreateReq", ddt_service.CREATE_KEYS_RIGA,
    obbligatorie=("articolo_id",),
    speciali={"componenti_overrides": componenti_overrides_field()},
)
_DDT_RIGA_UPDATE_REQUEST = schema_da_contratto(
    "VenditeDdtRigaUpdateReq", ddt_service.UPDATE_KEYS_RIGA,
)
_DDT_RIGA_QTA_EVASA_REQUEST = schema_da_contratto(
    "VenditeDdtRigaQtaEvasaReq", ("qta_operativa",),
    obbligatorie=("qta_operativa",),
)
_DDT_PRELIEVO_CREATE_REQUEST = schema_da_contratto(
    "VenditeDdtPrelievoCreateReq", ddt_service.CREATE_KEYS_PRELIEVO,
    obbligatorie=("qta",),
)
_DDT_PRELIEVO_UPDATE_REQUEST = schema_da_contratto(
    "VenditeDdtPrelievoUpdateReq", ddt_service.UPDATE_KEYS_PRELIEVO,
)
_DDT_RESPONSE = inline_serializer(
    name="VenditeDdtResp", fields={"data": serializers.DictField()},
)
_DDT_LISTA_RESPONSE = inline_serializer(
    name="VenditeDdtListaResp",
    fields={"data": serializers.ListField(child=serializers.DictField())},
)

class ApiDdtList(DomainAPIView):
    """GET/POST /api/v1/vendite/ddt/ — lista paginata + create BOZZA standalone."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")
    is_search_endpoint = True
    lista_codice = "vendite.ddt"

    @extend_schema(
        operation_id="vendite_ddt_list",
        parameters=[
            param_ricerca_full(),
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
        f = extract_doc_list_filters(qp, with_utility=True)
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

    @extend_schema(
        request=_DDT_CREATE_REQUEST,
        responses={200: _DDT_RESPONSE},
    )
    # Scopo: Crea nuovo DDT standalone in stato BOZZA (DRAFT).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=ddt_service.crea_ddt)


class ApiDdtExportView(DomainAPIView):
    """GET /api/v1/vendite/ddt/export/?formato=csv|xlsx (DEF-1).

    NB: parametro `formato` (italiano), NON `format` (magic param DRF —
    memoria feedback_drf_format_magic_param).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")
    is_search_endpoint = True
    lista_codice = "vendite.ddt"

    @extend_schema(
        operation_id="vendite_ddt_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
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
        f = extract_doc_list_filters(qp, with_utility=True)
        results, total = ddt_service.list_ddt_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            max_limit=EXPORT_MAX_ROWS + 1,
            **f,
        )
        filtri_applicati = ddt_service.resolve_filtri_export_label(
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
    model_permission = ("vendite", "ddt")

    @extend_schema(
        responses={200: _DDT_RESPONSE},
    )
    # Scopo: Dettaglio testata DDT + capability.
    def get(self, request: Request, ddt_id: int) -> JsonResponse:
        return success_response(ddt_service.get_ddt(int(ddt_id)))

    @extend_schema(
        request=_DDT_UPDATE_REQUEST,
        responses={200: _DDT_RESPONSE},
    )
    # Scopo: Aggiorna testata DDT. Quali campi si cambiano in quale stato lo
    #        decide il lock di testata del DB (`trg_ddt_a05_lock_fuori_bozza_upd`).
    #        PATCH usa request.data (DRF ha gia' parsato il body;
    #        handle_post_json rileggerebbe il raw consumato).
    def patch(self, request: Request, ddt_id: int) -> JsonResponse:
        return success_response(
            ddt_service.aggiorna_ddt(int(ddt_id), dict(corpo_oggetto(request))),
        )

    @extend_schema(
        responses={200: _DDT_RESPONSE},
    )
    # Scopo: Hard-delete DDT (abbandono bozza, solo DRAFT + 0 righe).
    def delete(self, request: Request, ddt_id: int) -> JsonResponse:
        return success_response(ddt_service.elimina_ddt(int(ddt_id)))


class ApiDdtCambiaStato(DomainAPIView):
    """POST /api/v1/vendite/ddt/<ddt_id>/cambia-stato/ — transizione di stato
    data-driven (SPEDITO / CONSEGNATO / RESO / ANNULLATO). Body: `stato_codice`
    (= `target_state` dell'azione). L'ammissibilita' e' validata dal trigger
    guard DB. Verso ANNULLATO, una bolla con legami risponde
    E_DOC_ANNULLO_CON_LEGAMI (`confirm_and_retry`) finche' il corpo non
    dichiara `legami_confermati` (letto da `…/legami/`)."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(
        request=CAMBIA_STATO_CON_CONFERMA_REQUEST,
        responses={200: _DDT_RESPONSE},
    )
    # Scopo: Esegue la transizione di stato richiesta (validata dal trigger DB).
    def post(self, request: Request, ddt_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: ddt_service.cambia_stato(
                int(ddt_id), payload.get("stato_codice"),
                legami_confermati=payload.get("legami_confermati"),
            ),
        )


class ApiDdtPush(DomainAPIView):
    """POST /api/v1/vendite/ddt/<ddt_id>/push/ — push singolo a commessa
    (sorgente DDT_VENDITA, fatturazione differita)."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(
        request=None,
        responses={200: _DDT_RESPONSE},
    )
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
    model_permission=("vendite", "ddt"),
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
    model_permission=("vendite", "ddt"),
)


class ApiDdtRighePerReso(DomainAPIView):
    """GET /api/v1/vendite/ddt/<ddt_id>/righe-per-reso/.

    Righe del DDT con gia'-reso cumulato e residuo rendibile: alimenta il
    pannello "crea reso" del drawer DDT (slice resi). Vive nel dominio
    sorgente (DDT) ma delega a `resi_service` (import locale, come
    `ApiOrdineGeneraDdt` fa con ddt_service — evita cicli).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(
        responses={200: _DDT_LISTA_RESPONSE},
    )
    # Scopo: Righe DDT + qta_gia_resa/qta_resa_residua per il pannello reso.
    def get(self, request: Request, ddt_id: int) -> JsonResponse:
        from apps.vendite.services import resi_service
        return success_response(
            resi_service.list_righe_ddt_per_reso(int(ddt_id)),
        )


class ApiDdtRighe(DomainAPIView):
    """GET/POST /api/v1/vendite/ddt/<ddt_id>/righe/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(
        responses={200: _DDT_LISTA_RESPONSE},
    )
    # Scopo: Lista righe del DDT.
    def get(self, request: Request, ddt_id: int) -> JsonResponse:
        return success_response(ddt_service.list_righe(int(ddt_id)))

    @extend_schema(
        request=_DDT_RIGA_CREATE_REQUEST,
        responses={200: _DDT_RESPONSE},
    )
    # Scopo: Aggiunge una riga (solo DRAFT). Pricing via BB condiviso.
    def post(self, request: Request, ddt_id: int) -> JsonResponse:
        auth_user_id = get_actor_user_id(request)
        return handle_post_json(
            request,
            handler=lambda payload: ddt_service.gestisci_riga(
                int(ddt_id), payload, auth_user_id=auth_user_id,
            ),
        )


class ApiDdtRigaDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/ddt/<ddt_id>/righe/<riga_id>/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(
        request=_DDT_RIGA_UPDATE_REQUEST,
        responses={200: _DDT_RESPONSE},
    )
    # Scopo: Aggiorna una riga del DDT (solo DRAFT).
    def patch(self, request: Request, ddt_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            ddt_service.aggiorna_riga(
                int(ddt_id), int(riga_id), dict(corpo_oggetto(request)),
                auth_user_id=get_actor_user_id(request),
            ),
        )

    @extend_schema(
        responses={200: _DDT_RESPONSE},
    )
    # Scopo: Elimina una riga del DDT (hard delete, solo DRAFT).
    def delete(self, request: Request, ddt_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            ddt_service.elimina_riga(int(ddt_id), int(riga_id)),
        )


class ApiDdtRigaQtaEvasa(DomainAPIView):
    """POST /api/v1/vendite/ddt/<ddt_id>/righe/<riga_id>/qta-evasa/ — corregge
    la quantita' evasa di una riga legata a un ordine o a un reso (verbo DB
    `vendite.fn_ddt_riga_correggi_qta_evasa`, D-2 di
    brief-db-ddt-righe-evase-dall-ordine). Body: `qta_operativa`. Il pulsante
    segue `correggi_qta_evasa_blocco` della riga (NULL = acceso)."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(
        request=_DDT_RIGA_QTA_EVASA_REQUEST,
        responses={200: _DDT_RESPONSE},
    )
    # Scopo: Nuova quantita' evasa della riga (riga, legami e ordine insieme).
    def post(self, request: Request, ddt_id: int, riga_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: ddt_service.correggi_qta_evasa(
                int(ddt_id), int(riga_id), payload,
            ),
        )


class ApiDdtPrelievi(DomainAPIView):
    """GET /api/v1/vendite/ddt/<ddt_id>/prelievi/ — i prelievi della bolla per
    la griglia (Lotto 3 R-2b): se la bolla muove merce, i magazzini con
    `usa_ubicazioni`, e le voci da movimentare (riga o componente del kit)
    ognuna coi suoi prelievi. Sola lettura."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(responses={200: dict})
    # Scopo: La situazione dei prelievi della bolla.
    def get(self, request: Request, ddt_id: int) -> JsonResponse:
        return success_response(ddt_service.get_prelievi(int(ddt_id)))


class ApiDdtRigaPrelievi(DomainAPIView):
    """POST /api/v1/vendite/ddt/<ddt_id>/righe/<riga_id>/prelievi/ — un prelievo
    sotto la riga (o un suo componente: `ddt_riga_componente_id`). Le regole
    sono dei trigger DB (bozza, kit, ubicazioni, lotto/seriale)."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(request=_DDT_PRELIEVO_CREATE_REQUEST, responses={200: _DDT_RESPONSE})
    # Scopo: Crea il prelievo.
    def post(self, request: Request, ddt_id: int, riga_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: ddt_service.crea_prelievo(
                int(ddt_id), int(riga_id), payload,
            ),
        )


class ApiDdtRigaPrelievoDetail(DomainAPIView):
    """PATCH/DELETE /.../righe/<riga_id>/prelievi/<prelievo_id>/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(request=_DDT_PRELIEVO_UPDATE_REQUEST, responses={200: _DDT_RESPONSE})
    # Scopo: Cambia quantita', lotto, seriale o ubicazioni del prelievo.
    def patch(
        self, request: Request, ddt_id: int, riga_id: int, prelievo_id: int,
    ) -> JsonResponse:
        return success_response(
            ddt_service.aggiorna_prelievo(
                int(ddt_id), int(riga_id), int(prelievo_id), dict(corpo_oggetto(request)),
            ),
        )

    @extend_schema(responses={200: _DDT_RESPONSE})
    # Scopo: Toglie il prelievo.
    def delete(
        self, request: Request, ddt_id: int, riga_id: int, prelievo_id: int,
    ) -> JsonResponse:
        return success_response(
            ddt_service.elimina_prelievo(int(ddt_id), int(riga_id), int(prelievo_id)),
        )


class ApiDdtRigaPreviewComponenti(DomainAPIView):
    """POST /api/v1/vendite/ddt/<ddt_id>/righe/preview-componenti/.

    Preview read-only dei componenti BoM per il drawer riga (pre-save).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(
        request=PREVIEW_COMPONENTI_REQUEST,
        responses={200: PREVIEW_COMPONENTI_RESPONSE},
    )
    # Scopo: Preview read-only dei componenti BoM (nessuna persistenza: il gate
    #        L1 sugli override e' applicato al salvataggio riga).
    def post(self, request: Request, ddt_id: int) -> JsonResponse:
        # Ritorna la LISTA nuda dei componenti (contratto condiviso col
        # ComponentiDialog FE: `response.data.data` = array). NON avvolgere in
        # {"componenti": ...} — il dialog fa `for...of` sull'array (mirror
        # contratti/preventivi).
        def _handler(payload: dict[str, Any]) -> list[dict[str, Any]]:
            return ddt_service.preview_componenti_riga(
                int(ddt_id),
                articolo_id=str(payload.get("articolo_id")),
                uom_operativa_id=payload.get("uom_operativa_id"),
                quantita=payload.get("quantita"),
            )

        return handle_post_json(request, handler=_handler)


class ApiDdtRigaComponentiList(DomainAPIView):
    """GET /api/v1/vendite/ddt/<ddt_id>/righe/<riga_id>/componenti/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "ddt")

    @extend_schema(
        parameters=COMPONENTI_LIST_PARAMETERS,
        responses={200: COMPONENTI_LIST_RESPONSE},
    )
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
    model_permission = ("vendite", "ddt")

    @extend_schema(request=COMPONENTE_PATCH_REQUEST, responses={200: dict})
    # Scopo: Aggiorna un componente BoM (prezzo/attivo/meta, solo DRAFT).
    def patch(
        self, request: Request, ddt_id: int, riga_id: int, componente_id: int,
    ) -> JsonResponse:
        return success_response(
            ddt_service.update_componente(
                int(ddt_id), int(riga_id), int(componente_id), dict(corpo_oggetto(request)),
                auth_user_id=get_actor_user_id(request),
            ),
        )

    @extend_schema(
        responses={200: _DDT_RESPONSE},
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


# ── Righe: la lista configurabile `vendite.ddt_righe` ──
# Pagina ed export dal factory condiviso `build_lista_figlia_views`
# (brief-db-liste-righe-documento, lotto A). La closure legge il global di
# modulo a call-time: i patch dei test sul service restano validi.
# ⚠️ `GET …/righe/` resta la lettura COMPLETA: la lista e' su `…/righe/lista/`.
_DdtRigheLista, _DdtRigheListaExport = build_lista_figlia_views(
    schema_prefix="DdtRighe",
    operation_id="vendite_ddt_righe_lista",
    area_funzionale="vendite",
    lista_emittente_param=EMITTENTE_DOCUMENTO_PARAM,
    url_kwarg="ddt_id",
    model_permission=('vendite', 'ddt'),
    pagina_call=lambda documento_id, **kw: ddt_service.list_righe_pagina(documento_id, **kw),
    colonne_ordinabili=DdtRepository.righe_colonne_ordinabili(),
    ordine_assente=DdtRepository.righe_ordine_di_partenza(),
)


# ⭐ Il cancello di perimetro come LETTERALE nel corpo della classe: e' la
#    forma che `test_perimetro_emittente_copertura` legge (vedi la factory).
class ApiDdtRigheListaView(_DdtRigheLista):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.ddt_righe"


class ApiDdtRigheListaExportView(_DdtRigheListaExport):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.ddt_righe"
