# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per vendite.resi (CRUD testata + righe, conferma/annullo,
#        generazione DDT di ri-consegna, code da-accreditare/da-riconsegnare).
#        Clone strutturale ridotto di views_ddt: niente componenti/push/PDF.
#        NIENTE cambia-stato generico: conferma e annullo hanno effetti
#        (residuo, proiezione stato ordine, flip DDT) e passano SEMPRE dalle
#        fn madri DB via endpoint dedicati. Numero assegnato a CONFERMATO dal
#        trigger DB (non passato dal client).
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
    optional_iso_date,
    paginated_envelope,
    parse_list_params,
)
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api._list_filters_helpers import extract_doc_list_filters
from apps.vendite.services import resi_service

# Codici lista config (ui.lista_definizione) delle liste resi: guidano la
# risoluzione colonne visibili/ordine/permessi dell'export (DEF-1).
_LISTA_CODICE_RESI = "vendite.resi"
_LISTA_CODICE_DA_ACCREDITARE = "vendite.resi_da_accreditare"
_LISTA_CODICE_DA_RICONSEGNARE = "vendite.resi_da_riconsegnare"


# Scopo: Estrae i filtri delle due code: gli stessi della lista (BB
#        extract_doc_list_filters) SENZA lo stato (le viste coda si
#        auto-limitano ai resi CONFERMATI pertinenti). Derivato — non
#        copiato — cosi' un filtro comune nuovo vale ovunque.
def _extract_coda_filters(qp) -> dict[str, Any]:
    filters = extract_doc_list_filters(qp)
    filters.pop("stato_codice")
    return filters


class ApiResiList(DomainAPIView):
    """GET/POST /api/v1/vendite/resi/ — lista paginata + create reso da DDT."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_resi_list",
        parameters=[
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False,
                             description="codice_interno stato (DRAFT | CONFERMATO | ANNULLATO)"),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False,
                             description="Data ISO; default anno-1 applicato dalla UI."),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="campo_sorgente catalogo 'vendite.resi' "
                                         "(numero | data | destinatario_denominazione | "
                                         "ba_codice | stato_descrizione | ...)."),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeResiListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata resi con filtri standard + scope emittente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data")
        f = extract_doc_list_filters(qp)
        results, total = resi_service.list_resi_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            **f,
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    # Scopo: Crea nuovo reso da DDT (DRAFT). Payload {ddt_id, data?, righe?}.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=resi_service.crea_reso)


class ApiResiExport(DomainAPIView):
    """GET /api/v1/vendite/resi/export/?formato=csv|xlsx (DEF-1).

    Export CSV/XLSX della lista resi. Filtri/sort identici al list; colonne
    visibili/ordine/permessi dalla config lista `vendite.resi`. NB: parametro
    `formato` (italiano), NON `format` (magic param DRF).
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_resi_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="stato_codice_interno", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
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
    # Scopo: Export della lista resi. Fetcha fino a EXPORT_MAX_ROWS+1 (max_limit)
    #        per intercettare l'overflow senza troncare in silenzio.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)
        p = parse_list_params(qp, default_order="data")
        f = extract_doc_list_filters(qp)
        results, total = resi_service.list_resi_rows(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            max_limit=EXPORT_MAX_ROWS + 1,
            **f,
        )
        filtri_applicati = resi_service.resolve_filtri_export_label(
            search=p["search"],
            stato_codice=f["stato_codice"],
            billing_account_id=f["billing_account_id"],
            data_da=f["data_da"],
            data_al=f["data_al"],
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_RESI,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


class ApiResiDaAccreditare(DomainAPIView):
    """GET /api/v1/vendite/resi/da-accreditare/ — coda righe reso CONFERMATE a
    credito (vista vw_resi_da_accreditare). Predisposizione slice nota di
    credito: la coda e' interrogabile, il consumo arriva con la slice NC."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_resi_da_accreditare",
        parameters=[
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="campo_sorgente catalogo "
                                         "'vendite.resi_da_accreditare' "
                                         "(reso_numero | data | destinatario_denominazione | "
                                         "descrizione | ddt_numero | qta_operativa | ...)."),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeResiDaAccreditareResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Coda "da accreditare" paginata con scope emittente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data")
        results, total = resi_service.list_da_accreditare(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            **_extract_coda_filters(qp),
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


class ApiResiDaAccreditareExport(DomainAPIView):
    """GET /api/v1/vendite/resi/da-accreditare/export/?formato=csv|xlsx (DEF-1).

    Export CSV/XLSX della coda "da accreditare". Filtri/sort identici al list;
    colonne visibili/ordine/permessi dalla config lista `vendite.resi_da_accreditare`.
    NB: parametro `formato` (italiano), NON `format` (magic param DRF).
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_resi_da_accreditare_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
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
    # Scopo: Export della coda "da accreditare". Fetcha fino a EXPORT_MAX_ROWS+1
    #        (max_limit) per intercettare l'overflow senza troncare in silenzio.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)
        p = parse_list_params(qp, default_order="data")
        f = _extract_coda_filters(qp)
        results, total = resi_service.list_da_accreditare(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            max_limit=EXPORT_MAX_ROWS + 1,
            **f,
        )
        filtri_applicati = resi_service.resolve_filtri_coda_export_label(
            search=p["search"],
            billing_account_id=f["billing_account_id"],
            data_da=f["data_da"],
            data_al=f["data_al"],
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_DA_ACCREDITARE,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


class ApiResiDaRiconsegnare(DomainAPIView):
    """GET /api/v1/vendite/resi/da-riconsegnare/ — coda righe reso CONFERMATE
    per ri-consegna con copertura incompleta (vista vw_resi_da_riconsegnare,
    stato_riconsegna derivato). Si auto-svuota a copertura completa."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_resi_da_riconsegnare",
        parameters=[
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="campo_sorgente catalogo "
                                         "'vendite.resi_da_riconsegnare' "
                                         "(reso_numero | data | destinatario_denominazione | "
                                         "descrizione | ddt_numero | qta_resa | "
                                         "qta_riconsegnata | qta_residua | stato_riconsegna)."),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="VenditeResiDaRiconsegnareResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Coda "da ri-consegnare" paginata con scope emittente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="data")
        results, total = resi_service.list_da_riconsegnare(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            **_extract_coda_filters(qp),
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


class ApiResiDaRiconsegnareExport(DomainAPIView):
    """GET /api/v1/vendite/resi/da-riconsegnare/export/?formato=csv|xlsx (DEF-1).

    Export CSV/XLSX della coda "da ri-consegnare". Filtri/sort identici al list;
    colonne visibili/ordine/permessi dalla config lista `vendite.resi_da_riconsegnare`.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_resi_da_riconsegnare_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
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
    # Scopo: Export della coda "da ri-consegnare". Fetcha fino a EXPORT_MAX_ROWS+1
    #        (max_limit) per intercettare l'overflow senza troncare in silenzio.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        fmt = parse_export_format(request)
        p = parse_list_params(qp, default_order="data")
        f = _extract_coda_filters(qp)
        results, total = resi_service.list_da_riconsegnare(
            search=p["search"],
            auth_user_id=get_scope_user_id(request),
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            max_limit=EXPORT_MAX_ROWS + 1,
            **f,
        )
        filtri_applicati = resi_service.resolve_filtri_coda_export_label(
            search=p["search"],
            billing_account_id=f["billing_account_id"],
            data_da=f["data_da"],
            data_al=f["data_al"],
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_DA_RICONSEGNARE,
            results=results,
            total=total,
            filtri_applicati=filtri_applicati,
            fmt=fmt,
        )


class ApiResoDetail(DomainAPIView):
    """GET/PATCH/DELETE /api/v1/vendite/resi/<reso_id>/."""

    area_funzionale = "vendite"

    # Scopo: Dettaglio testata reso + capability data-driven.
    def get(self, request: Request, reso_id: int) -> JsonResponse:
        return success_response(resi_service.get_reso(int(reso_id)))

    # Scopo: Aggiorna testata reso (solo DRAFT; data/meta). PATCH usa
    #        request.data (DRF ha gia' parsato il body).
    def patch(self, request: Request, reso_id: int) -> JsonResponse:
        return success_response(
            resi_service.aggiorna_reso(int(reso_id), dict(request.data)),
        )

    # Scopo: Hard-delete reso (abbandono bozza, solo DRAFT + 0 righe).
    def delete(self, request: Request, reso_id: int) -> JsonResponse:
        return success_response(resi_service.elimina_reso(int(reso_id)))


class ApiResoConferma(DomainAPIView):
    """POST /api/v1/vendite/resi/<reso_id>/conferma/ — DRAFT->CONFERMATO via
    fn madre `fn_conferma_reso` (numero, riapertura residuo, proiezione stato
    ordine, flip DDT se reso totale). Body vuoto."""

    area_funzionale = "vendite"

    # Scopo: Conferma il reso (fn madre atomica DB).
    def post(self, request: Request, reso_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: resi_service.conferma_reso(int(reso_id)),
        )


class ApiResoAnnulla(DomainAPIView):
    """POST /api/v1/vendite/resi/<reso_id>/annulla/ — annullo (da DRAFT o
    CONFERMATO) via fn madre `fn_annulla_reso` (storno effetti). Body vuoto."""

    area_funzionale = "vendite"

    # Scopo: Annulla il reso (fn madre atomica DB, storno post-conferma).
    def post(self, request: Request, reso_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: resi_service.annulla_reso(int(reso_id)),
        )


class ApiResoGeneraDdtRiconsegna(DomainAPIView):
    """POST /api/v1/vendite/resi/<reso_id>/genera-ddt-riconsegna/ — genera il
    DDT di ri-spedizione via fn madre `fn_genera_ddt_riconsegna`. Body:
    `{righe?: [{resi_riga_id, qta}], data?}` — `qta` in UNITA' BASE; righe
    assente/null = tutta la copertura residua. `righe` degeneri (non-lista,
    lista vuota, elementi malformati) = 400, NON "ri-spedisci tutto":
    validazione nel service (_parse_righe_riconsegna)."""

    area_funzionale = "vendite"

    # Scopo: Genera il DDT di ri-consegna (parziale/multiplo) dal reso.
    def post(self, request: Request, reso_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return resi_service.genera_ddt_riconsegna(
                int(reso_id),
                payload.get("righe"),
                optional_iso_date(payload, "data"),
            )

        return handle_post_json(request, handler=_handler)


class ApiResoRighe(DomainAPIView):
    """GET/POST /api/v1/vendite/resi/<reso_id>/righe/."""

    area_funzionale = "vendite"

    # Scopo: Lista righe del reso (con copertura ri-consegna derivata).
    def get(self, request: Request, reso_id: int) -> JsonResponse:
        return success_response(resi_service.list_righe(int(reso_id)))

    # Scopo: Aggiunge una riga (solo DRAFT, snapshot dalla riga DDT).
    def post(self, request: Request, reso_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: resi_service.gestisci_riga(
                int(reso_id), payload,
            ),
        )


class ApiResoRigaDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/resi/<reso_id>/righe/<riga_id>/."""

    area_funzionale = "vendite"

    # Scopo: Aggiorna una riga del reso (solo DRAFT; qta/tipo/motivo/meta).
    def patch(self, request: Request, reso_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            resi_service.aggiorna_riga(
                int(reso_id), int(riga_id), dict(request.data),
            ),
        )

    # Scopo: Elimina una riga del reso (hard delete, solo DRAFT).
    def delete(self, request: Request, reso_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            resi_service.elimina_riga(int(reso_id), int(riga_id)),
        )
