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
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.permissions import PassaggioDocumento
from apps.core.api.payload_validators import (
    corpo_oggetto,
    optional_iso_date,
    paginated_envelope,
    parse_list_params,
    qp_int_optional,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api._list_filters_helpers import extract_doc_list_filters
from apps.vendite.services import resi_service
from apps.vendite.services._annullo_con_legami import STATO_ANNULLATO
from apps.ui.api.lista_figlia_views import EMITTENTE_DOCUMENTO_PARAM, build_lista_figlia_views
from apps.vendite.db.resi_repository import ResiRepository
from apps.core.api.openapi_params import param_ricerca_full
from apps.vendite.api._schema_da_contratto import schema_da_contratto

# Codici lista config (ui.lista_definizione) delle liste resi: guidano la
# risoluzione colonne visibili/ordine/permessi dell'export (DEF-1).
_LISTA_CODICE_RESI = "vendite.resi"
_LISTA_CODICE_DA_ACCREDITARE = "vendite.resi_da_accreditare"
_LISTA_CODICE_DA_RICONSEGNARE = "vendite.resi_da_riconsegnare"


# ── Schemi OpenAPI dei corpi: le chiavi dal contratto del service ──────────
_RESO_RIGA_CREATE_REQUEST = schema_da_contratto(
    "VenditeResoRigaCreateReq", resi_service.CREATE_KEYS_RIGA,
    obbligatorie=("ddt_riga_id", "tipo_reso_id", "qta_operativa"),
)
_RESO_RIGA_UPDATE_REQUEST = schema_da_contratto(
    "VenditeResoRigaUpdateReq", resi_service.UPDATE_KEYS_RIGA,
)
# Il reso nasce da un DDT; con `righe` la testata e le righe in un colpo solo.
_RESO_CREATE_REQUEST = schema_da_contratto(
    "VenditeResoCreateReq", resi_service.CREATE_KEYS_RESO,
    obbligatorie=("ddt_id",),
    speciali={"righe": serializers.ListField(
        child=type(_RESO_RIGA_CREATE_REQUEST)(), required=False,
    )},
)
_RESO_UPDATE_REQUEST = schema_da_contratto(
    "VenditeResoUpdateReq", resi_service.UPDATE_KEYS_RESO,
)
_RESO_RIENTRO_CREATE_REQUEST = schema_da_contratto(
    "VenditeResoRientroCreateReq", resi_service.CREATE_KEYS_RIENTRO,
    obbligatorie=("ddt_riga_prelievo_id", "qta"),
)
_RESO_RIENTRO_UPDATE_REQUEST = schema_da_contratto(
    "VenditeResoRientroUpdateReq", resi_service.UPDATE_KEYS_RIENTRO,
)


# Una riga di ri-consegna, come la legge `_parse_righe_riconsegna` (unita'
# BASE). ⚠️ UNA sola CLASSE, un'istanza per uso: tre `inline_serializer` con lo
# stesso nome sono tre classi diverse (drf-spectacular avverte che lo schema e'
# sbagliato), e un'istanza gia' legata a un campo non si riusa come `child=`.
_RigaRiconsegna = type(inline_serializer(
    name="VenditeResoRigaRiconsegna",
    fields={
        "resi_riga_id": serializers.IntegerField(),
        "qta": serializers.DecimalField(max_digits=22, decimal_places=10),
    },
))


# Scopo: il campo `righe` delle tre azioni di ri-consegna. Omesso: tutta la
#        copertura residua. Fabbrica: il ListField e' per serializer.
def _righe_riconsegna_field() -> serializers.Field:
    return serializers.ListField(
        required=False,
        help_text="Omessa: tutta la copertura residua del reso.",
        child=_RigaRiconsegna(),
    )


_RESO_GENERA_DDT_RICONSEGNA_REQUEST = inline_serializer(
    name="VenditeResoGeneraDdtRiconsegnaReq",
    fields={
        "righe": _righe_riconsegna_field(),
        "data": serializers.DateField(required=False, allow_null=True),
    },
)
_RESO_CHIUDI_RICONSEGNA_REQUEST = inline_serializer(
    name="VenditeResoChiudiRiconsegnaReq",
    fields={
        "righe": _righe_riconsegna_field(),
        "note": serializers.CharField(required=False, allow_null=True),
    },
)
_RESO_RIAPRI_RICONSEGNA_REQUEST = inline_serializer(
    name="VenditeResoRiapriRiconsegnaReq",
    fields={"righe": _righe_riconsegna_field()},
)
_RESO_RESPONSE = inline_serializer(
    name="VenditeResoResp", fields={"data": serializers.DictField()},
)
_RESO_LISTA_RESPONSE = inline_serializer(
    name="VenditeResoListaResp",
    fields={"data": serializers.ListField(child=serializers.DictField())},
)

# Scopo: Estrae i filtri delle due code: gli stessi della lista (BB
#        extract_doc_list_filters) SENZA lo stato (le viste coda si
#        auto-limitano ai resi CONFERMATI pertinenti). Derivato — non
#        copiato — cosi' un filtro comune nuovo vale ovunque.
def _extract_coda_filters(qp) -> dict[str, Any]:
    filters = extract_doc_list_filters(qp)
    filters.pop("stato_codice")
    # Restrizione al documento: e' cio' che rende il collegamento dal pannello
    # situazione merce un percorso intero e non «apri la coda e cercati la riga»
    # (FE-2). ⚠️ `qp_int_optional` e' STRICT: `?ddt_id=banana` risponde 400 e non
    # sparisce come filtro — un filtro che svanisce mostra la coda intera
    # facendola sembrare quella del documento.
    filters["ddt_id"] = qp_int_optional(qp.get("ddt_id"), "ddt_id")
    filters["ordine_id"] = qp_int_optional(qp.get("ordine_id"), "ordine_id")
    return filters


# Scopo: Filtri della sola coda accrediti = filtri coda comuni + `etichetta`
#        (DOVUTA | FACOLTATIVA, normalizzata upper; whitelist nel service).
#        UN punto di estrazione per list ed export: la parita' lista/export
#        (DEF-1 "filtri identici al list") vale per costruzione, non per
#        disciplina dei due call-site.
def _extract_accredito_filters(qp) -> dict[str, Any]:
    filters = _extract_coda_filters(qp)
    filters["etichetta"] = qp_str_upper(qp.get("etichetta"))
    return filters


class ApiResiList(DomainAPIView):
    """GET/POST /api/v1/vendite/resi/ — lista paginata + create reso da DDT."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")
    is_search_endpoint = True
    lista_codice = "vendite.resi"

    @extend_schema(
        operation_id="vendite_resi_list",
        parameters=[
            param_ricerca_full(),
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

    @extend_schema(
        request=_RESO_CREATE_REQUEST,
        responses={200: _RESO_RESPONSE},
    )
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
    model_permission = ("vendite", "reso")
    is_search_endpoint = True
    lista_codice = "vendite.resi"

    @extend_schema(
        operation_id="vendite_resi_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
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
    """GET /api/v1/vendite/resi/da-accreditare/ — coda righe reso CONFERMATE
    con accredito dovuto (forma contatore: fatturati - tenuti > 0, qualunque
    tipo di reso; vista vw_resi_da_accreditare). `etichetta` distingue le NC
    DOVUTE (a credito, lavoro arretrato) dalle FACOLTATIVE (per ri-consegna,
    opzione DL-26). Il consumo arriva con la slice NC."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")
    is_search_endpoint = True
    lista_codice = "vendite.resi_da_accreditare"

    @extend_schema(
        operation_id="vendite_resi_da_accreditare",
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="etichetta", type=str, required=False,
                             description="DOVUTA | FACOLTATIVA (default: tutte)."),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="ddt_id", type=int, required=False,
                             description="Restringe la coda al DDT indicato "
                                         "(collegamento dal pannello situazione "
                                         "merce). Alternativo a ordine_id."),
            OpenApiParameter(name="ordine_id", type=int, required=False,
                             description="Restringe la coda all'ordine indicato, via "
                                         "fulfillment della riga di DDT resa. "
                                         "Alternativo a ddt_id."),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="campo_sorgente catalogo "
                                         "'vendite.resi_da_accreditare' "
                                         "(reso_numero | data | destinatario_denominazione | "
                                         "descrizione | ddt_numero | accredito_dovuto | "
                                         "etichetta | ...)."),
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
            **_extract_accredito_filters(qp),
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


class ApiResiDaAccreditareExport(DomainAPIView):
    """GET /api/v1/vendite/resi/da-accreditare/export/?formato=csv|xlsx (DEF-1).

    Export CSV/XLSX della coda "da accreditare". Filtri/sort identici al list;
    colonne visibili/ordine/permessi dalla config lista `vendite.resi_da_accreditare`.
    NB: parametro `formato` (italiano), NON `format` (magic param DRF).
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")
    is_search_endpoint = True
    lista_codice = "vendite.resi_da_accreditare"

    @extend_schema(
        operation_id="vendite_resi_da_accreditare_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="etichetta", type=str, required=False,
                             description="DOVUTA | FACOLTATIVA (default: tutte)."),
            OpenApiParameter(name="ddt_id", type=int, required=False,
                             description="Restringe la coda al DDT indicato "
                                         "(collegamento dal pannello situazione "
                                         "merce). Alternativo a ordine_id."),
            OpenApiParameter(name="ordine_id", type=int, required=False,
                             description="Restringe la coda all'ordine indicato, via "
                                         "fulfillment della riga di DDT resa. "
                                         "Alternativo a ddt_id."),
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
        f = _extract_accredito_filters(qp)
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
            billing_account_id=f["billing_account_id"],
            data_da=f["data_da"],
            data_al=f["data_al"],
            etichetta=f["etichetta"],
            ddt_id=f["ddt_id"],
            ordine_id=f["ordine_id"],
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
    model_permission = ("vendite", "reso")
    is_search_endpoint = True
    lista_codice = "vendite.resi_da_riconsegnare"

    @extend_schema(
        operation_id="vendite_resi_da_riconsegnare",
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="ddt_id", type=int, required=False,
                             description="Restringe la coda al DDT indicato "
                                         "(collegamento dal pannello situazione "
                                         "merce). Alternativo a ordine_id."),
            OpenApiParameter(name="ordine_id", type=int, required=False,
                             description="Restringe la coda all'ordine indicato, via "
                                         "fulfillment della riga di DDT resa. "
                                         "Alternativo a ddt_id."),
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
    model_permission = ("vendite", "reso")
    is_search_endpoint = True
    lista_codice = "vendite.resi_da_riconsegnare"

    @extend_schema(
        operation_id="vendite_resi_da_riconsegnare_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            param_ricerca_full(),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="ddt_id", type=int, required=False,
                             description="Restringe la coda al DDT indicato "
                                         "(collegamento dal pannello situazione "
                                         "merce). Alternativo a ordine_id."),
            OpenApiParameter(name="ordine_id", type=int, required=False,
                             description="Restringe la coda all'ordine indicato, via "
                                         "fulfillment della riga di DDT resa. "
                                         "Alternativo a ddt_id."),
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
            billing_account_id=f["billing_account_id"],
            data_da=f["data_da"],
            data_al=f["data_al"],
            ddt_id=f["ddt_id"],
            ordine_id=f["ordine_id"],
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
    model_permission = ("vendite", "reso")

    @extend_schema(
        responses={200: _RESO_RESPONSE},
    )
    # Scopo: Dettaglio testata reso + capability data-driven.
    def get(self, request: Request, reso_id: int) -> JsonResponse:
        return success_response(resi_service.get_reso(int(reso_id)))

    @extend_schema(
        request=_RESO_UPDATE_REQUEST,
        responses={200: _RESO_RESPONSE},
    )
    # Scopo: Aggiorna testata reso (data, note, magazzino di rientro; quali in
    #        quale stato lo decide il lock di testata del DB). Corpo da
    #        `corpo_oggetto` (api.md §«Quando usare handle_post_json»).
    def patch(self, request: Request, reso_id: int) -> JsonResponse:
        return success_response(
            resi_service.aggiorna_reso(int(reso_id), corpo_oggetto(request)),
        )

    @extend_schema(
        responses={200: _RESO_RESPONSE},
    )
    # Scopo: Hard-delete reso (abbandono bozza, solo DRAFT + 0 righe).
    def delete(self, request: Request, reso_id: int) -> JsonResponse:
        return success_response(resi_service.elimina_reso(int(reso_id)))


class ApiResoConferma(DomainAPIView):
    """POST /api/v1/vendite/resi/<reso_id>/conferma/ — DRAFT->CONFERMATO via
    fn madre `fn_conferma_reso` (numero, riapertura residuo, proiezione stato
    ordine, flip DDT se reso totale). Body vuoto."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")
    # ⭐ L'azione dalla riga del passaggio, la stessa che legge il verbo (M-3):
    #    oggi `conferma_reso` per la conferma e per l'annullo di un confermato;
    #    l'annullo di una bozza chiede il solo livello sul documento (M-4).
    post_passaggio = PassaggioDocumento(
        testata=resi_service.TESTATA_RESO, documento_kwarg="reso_id",
        stato_chiesto=resi_service.STATO_CONFERMATO,
    )

    @extend_schema(
        request=None,
        responses={200: _RESO_RESPONSE},
    )
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
    model_permission = ("vendite", "reso")
    # ⭐ L'azione dalla riga del passaggio, la stessa che legge il verbo (M-3):
    #    oggi `conferma_reso` per la conferma e per l'annullo di un confermato;
    #    l'annullo di una bozza chiede il solo livello sul documento (M-4).
    post_passaggio = PassaggioDocumento(
        testata=resi_service.TESTATA_RESO, documento_kwarg="reso_id",
        stato_chiesto=STATO_ANNULLATO,
    )

    @extend_schema(
        request=None,
        responses={200: _RESO_RESPONSE},
    )
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
    model_permission = ("vendite", "reso")

    @extend_schema(
        request=_RESO_GENERA_DDT_RICONSEGNA_REQUEST,
        responses={200: _RESO_RESPONSE},
    )
    # Scopo: Genera il DDT di ri-consegna (parziale/multiplo) dal reso.
    def post(self, request: Request, reso_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return resi_service.genera_ddt_riconsegna(
                int(reso_id),
                payload.get("righe"),
                optional_iso_date(payload, "data"),
            )

        return handle_post_json(request, handler=_handler)


class ApiResoChiudiRiconsegna(DomainAPIView):
    """POST /api/v1/vendite/resi/<reso_id>/chiudi-riconsegna/ — dichiara
    DEFINITIVA una quota di merce resa per ri-consegna (non tornera' al
    cliente) via fn madre `fn_chiudi_riconsegna_reso`: il residuo ordine si
    chiude (→ EVASO) e l'accredito in coda passa da FACOLTATIVA a DOVUTA
    **senza cambiare importo**. Body: `{righe?: [{resi_riga_id, qta}], note?}`
    — `qta` in UNITA' BASE (stesso contratto della ri-spedizione: le due uscite
    condividono la copertura); righe assente/null = tutta la copertura residua.
    `righe` degeneri = 400, NON "rendi definitivo tutto"."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")

    @extend_schema(
        request=_RESO_CHIUDI_RICONSEGNA_REQUEST,
        responses={200: _RESO_RESPONSE},
    )
    # Scopo: Chiude la ri-consegna (rinuncia parziale/totale) sul reso.
    def post(self, request: Request, reso_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return resi_service.chiudi_riconsegna(
                int(reso_id),
                payload.get("righe"),
                payload.get("note"),
            )

        return handle_post_json(request, handler=_handler)


class ApiResoRiapriRiconsegna(DomainAPIView):
    """POST /api/v1/vendite/resi/<reso_id>/riapri-riconsegna/ — annulla una
    chiusura via fn madre `fn_riapri_riconsegna_reso`: la quota torna
    ri-spedibile, lo stato ordine torna PARZIALMENTE_EVASO e l'accredito torna
    FACOLTATIVA (round-trip = stato iniziale). Body:
    `{righe?: [{resi_riga_id, qta}]}` — righe assente/null = tutte le rinunce
    del reso; lo scalo parte dalle rinunce piu' RECENTI (LIFO, lato DB)."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")

    @extend_schema(
        request=_RESO_RIAPRI_RICONSEGNA_REQUEST,
        responses={200: _RESO_RESPONSE},
    )
    # Scopo: Riapre una chiusura di ri-consegna (rimedio a una rinuncia errata).
    def post(self, request: Request, reso_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: resi_service.riapri_riconsegna(
                int(reso_id), payload.get("righe")
            ),
        )


class ApiResiAccrediti(DomainAPIView):
    """POST /api/v1/vendite/resi/accrediti/ — accredita N righe di reso
    (genera le rettifiche da cui nascera' la nota di credito).
    Body: `{resi_riga_ids: [5797, 5799, ...]}`.

    ⭐ **Un endpoint solo, e la riga singola e' una lista di uno** (D-NC-7): due
    superfici per lo stesso verbo divergerebbero su permessi, conferme e forma
    della risposta, e il frontend avrebbe due strade da tenere allineate per
    sempre.

    Risposta 200 con un REPORT a tre stati
    (`COMPLETATO` | `PARZIALE` | `ERRORE`), `accrediti` con le rettifiche
    create e `falliti` con codice e messaggio per riga.
    ⚠️ **Anche «tutte fallite» e' 200**: il verbo non e' l'atto fiscale — il
    documento nasce dopo, nel giro di fatturazione — quindi un esito parziale
    non lascia mai mezzo documento, lascia righe che restano in coda. E
    sollevare butterebbe via l'esito delle righe riuscite."""

    area_funzionale = "vendite"
    # Porta di un documento fiscale: il presidio sta qui e non nella madre, che
    # deve restare usabile da un processo autorizzato (P-1, azione id 31).
    post_permission = "accredita_riga_reso"

    @extend_schema(
        summary="Accredita righe di reso (massivo)",
        request=inline_serializer(
            name="ResiAccreditiRequest",
            fields={
                "resi_riga_ids": serializers.ListField(
                    child=serializers.IntegerField(), allow_empty=False,
                ),
            },
        ),
        responses={200: OpenApiTypes.OBJECT},
        tags=["vendite-resi"],
    )
    # Scopo: Accredita le righe di reso selezionate (fan-out isolato per riga).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: resi_service.accredita_righe_reso(
                payload.get("resi_riga_ids"),
            ),
            # Modifica di stato su un documento fiscale: la chiave e'
            # obbligatoria (api.md §Idempotency-Key).
            require_idempotency_key=True,
        )


class ApiResoRigaAnnullaAccredito(DomainAPIView):
    """POST /api/v1/vendite/resi/<reso_id>/righe/<riga_id>/annulla-accredito/
    — annulla l'accredito di una riga di reso via fn madre
    `fn_annulla_accredito_riga_reso` (D-NC-11). Body: `{motivo: "..."}`,
    obbligatorio.

    E' il caso «ho cliccato la riga sbagliata», e sta **a monte** del
    documento: porta le rettifiche ad ANNULLATA e cancella le righe di ponte,
    cosi' l'accredito torna dovuto in coda.

    ⛔ **Non** e' l'annullo del DOCUMENTO: quello e' gia' la pipeline, ed e' lo
    stesso delle fatture. ⚠️ E il reset di lotto **non** annulla l'accredito:
    la nota di credito viene RIGENERATA al giro dopo, perche' la merce resa non
    e' cambiata. Le due strade restano distinte, e il messaggio del DB dice
    all'operatore quale prendere."""

    area_funzionale = "vendite"
    # Stesso permesso dell'accredito: chi puo' accreditare puo' disfare il
    # proprio click. Due codename per le due facce dello stesso atto si
    # sfilerebbero al primo profilo configurato a mano.
    post_permission = "accredita_riga_reso"

    @extend_schema(
        summary="Annulla l'accredito di una riga di reso",
        request=inline_serializer(
            name="ResoAnnullaAccreditoRequest",
            fields={"motivo": serializers.CharField()},
        ),
        responses={200: OpenApiTypes.OBJECT},
        tags=["vendite-resi"],
    )
    # Scopo: Annulla l'accredito della riga (fn madre atomica DB).
    def post(self, request: Request, reso_id: int, riga_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: resi_service.annulla_accredito_riga_reso(
                int(reso_id), int(riga_id), payload.get("motivo"),
            ),
            require_idempotency_key=True,
        )


class ApiResoRighe(DomainAPIView):
    """GET/POST /api/v1/vendite/resi/<reso_id>/righe/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")

    @extend_schema(
        responses={200: _RESO_LISTA_RESPONSE},
    )
    # Scopo: Lista righe del reso (con copertura ri-consegna derivata).
    def get(self, request: Request, reso_id: int) -> JsonResponse:
        return success_response(resi_service.list_righe(int(reso_id)))

    @extend_schema(
        request=_RESO_RIGA_CREATE_REQUEST,
        responses={200: _RESO_RESPONSE},
    )
    # Scopo: Aggiunge una riga (solo DRAFT, snapshot dalla riga DDT).
    def post(self, request: Request, reso_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: resi_service.gestisci_riga(
                int(reso_id), payload,
            ),
        )


class ApiResoRientri(DomainAPIView):
    """GET /api/v1/vendite/resi/<reso_id>/rientri/ — i rientri del reso per la
    griglia (3-bis R-1b): se fa rientrare merce, il magazzino di rientro con
    `usa_ubicazioni`, e le voci coi prelievi d'origine e i loro rientri."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")

    @extend_schema(responses={200: dict})
    # Scopo: La situazione dei rientri del reso.
    def get(self, request: Request, reso_id: int) -> JsonResponse:
        return success_response(resi_service.get_rientri(int(reso_id)))


class ApiResoRigaRientri(DomainAPIView):
    """POST /api/v1/vendite/resi/<reso_id>/righe/<riga_id>/rientri/ — un rientro
    sotto la riga: il prelievo d'origine, la quantita', l'ubicazione."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")

    @extend_schema(request=_RESO_RIENTRO_CREATE_REQUEST, responses={200: _RESO_RESPONSE})
    # Scopo: Crea il rientro.
    def post(self, request: Request, reso_id: int, riga_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: resi_service.crea_rientro(
                int(reso_id), int(riga_id), payload,
            ),
        )


class ApiResoRigaRientroDetail(DomainAPIView):
    """PATCH/DELETE /.../righe/<riga_id>/rientri/<rientro_id>/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")

    @extend_schema(request=_RESO_RIENTRO_UPDATE_REQUEST, responses={200: _RESO_RESPONSE})
    # Scopo: Cambia quantita' o ubicazione del rientro.
    def patch(
        self, request: Request, reso_id: int, riga_id: int, rientro_id: int,
    ) -> JsonResponse:
        return success_response(
            resi_service.aggiorna_rientro(
                int(reso_id), int(riga_id), int(rientro_id), corpo_oggetto(request),
            ),
        )

    @extend_schema(responses={200: _RESO_RESPONSE})
    # Scopo: Toglie il rientro.
    def delete(
        self, request: Request, reso_id: int, riga_id: int, rientro_id: int,
    ) -> JsonResponse:
        return success_response(
            resi_service.elimina_rientro(int(reso_id), int(riga_id), int(rientro_id)),
        )


class ApiResoRigaDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/resi/<reso_id>/righe/<riga_id>/."""

    area_funzionale = "vendite"
    model_permission = ("vendite", "reso")

    @extend_schema(
        request=_RESO_RIGA_UPDATE_REQUEST,
        responses={200: _RESO_RESPONSE},
    )
    # Scopo: Aggiorna una riga del reso (solo DRAFT; qta/tipo/motivo/meta).
    def patch(self, request: Request, reso_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            resi_service.aggiorna_riga(
                int(reso_id), int(riga_id), corpo_oggetto(request),
            ),
        )

    @extend_schema(
        responses={200: _RESO_RESPONSE},
    )
    # Scopo: Elimina una riga del reso (hard delete, solo DRAFT).
    def delete(self, request: Request, reso_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            resi_service.elimina_riga(int(reso_id), int(riga_id)),
        )


# ── Righe: la lista configurabile `vendite.reso_righe` ──
# Pagina ed export dal factory condiviso `build_lista_figlia_views`
# (brief-db-liste-righe-documento, lotto A). La closure legge il global di
# modulo a call-time: i patch dei test sul service restano validi.
# ⚠️ `GET …/righe/` resta la lettura COMPLETA: la lista e' su `…/righe/lista/`.
_ResoRigheLista, _ResoRigheListaExport = build_lista_figlia_views(
    schema_prefix="ResoRighe",
    operation_id="vendite_resi_righe_lista",
    area_funzionale="vendite",
    lista_emittente_param=EMITTENTE_DOCUMENTO_PARAM,
    url_kwarg="reso_id",
    model_permission=('vendite', 'reso'),
    pagina_call=lambda documento_id, **kw: resi_service.list_righe_pagina(documento_id, **kw),
    colonne_ordinabili=ResiRepository.righe_colonne_ordinabili(),
    ordine_assente=ResiRepository.righe_ordine_di_partenza(),
)


# ⭐ Il cancello di perimetro come LETTERALE nel corpo della classe: e' la
#    forma che `test_perimetro_emittente_copertura` legge (vedi la factory).
class ApiResoRigheListaView(_ResoRigheLista):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.reso_righe"


class ApiResoRigheListaExportView(_ResoRigheListaExport):  # type: ignore[valid-type, misc]  # base costruita da una fabbrica
    lista_codice = "vendite.reso_righe"
