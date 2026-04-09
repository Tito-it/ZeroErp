# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view catalogo per lista, dettaglio e lookup articoli/UoM.
# ------------------------------------------------------------

from __future__ import annotations

from uuid import UUID

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.catalogo.services.catalogo_service import (
    fn_create_articolo,
    fn_create_componente,
    fn_create_nota_articolo,
    fn_create_uom_operativa,
    fn_create_unita_misura,
    fn_delete_componente,
    fn_delete_nota,
    fn_delete_uom_operativa,
    fn_disattiva_articolo,
    fn_disattiva_unita_misura,
    fn_get_articolo,
    fn_get_unita_misura,
    fn_list_componenti,
    fn_list_articoli,
    fn_list_note_articolo,
    fn_list_uom_operative,
    fn_list_unita_misura,
    fn_lookup_articoli,
    fn_update_componente,
    fn_update_nota,
    fn_update_articolo,
    fn_update_uom_operativa,
    fn_update_unita_misura,
    fn_list_conversioni,
    fn_get_conversione,
    fn_create_conversione,
    fn_update_conversione,
    fn_list_note_componente,
    fn_create_nota_componente,
)
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    optional_iso_date,
    paginated_envelope,
    parse_list_params,
    qp_bool,
    qp_int_strict,
    qp_str,
)
from apps.core.api.search_validators import require_min_search_length
from apps.core.api.success_responses import success_response


# Scopo: Estrae un bool opzionale da query string, preservando None se assente.
def _optional_qp_bool(request: Request, key: str) -> bool | None:
    raw_value = request.query_params.get(key)
    if raw_value is None:
        return None
    return qp_bool(raw_value, True)


# Scopo: Estrae un intero opzionale da query string con validazione rigorosa.
def _optional_qp_int_strict(request: Request, key: str) -> int | None:
    raw_value = request.query_params.get(key)
    if raw_value is None:
        return None
    return qp_int_strict(raw_value, key, 0)


# Scopo: Estrae una data ISO opzionale da query string.
def _optional_qp_iso_date(request: Request, key: str):
    return optional_iso_date({key: request.query_params.get(key)}, key)


# Scopo: Definisce in un solo punto i campi write articolo per schema API.
# for_create=True abilita codice e uom_id come obbligatori (NOT NULL DDL).
# for_create=False (PATCH) li esclude entrambi: sono immutabili dopo create
# (lock_columns DDL trg_articoli_a10_protect_codice_upd / _protect_uom_id_upd).
def _articolo_write_fields(*, for_create: bool) -> dict[str, serializers.Field]:
    fields: dict[str, serializers.Field] = {
        "descrizione": serializers.CharField(required=False),
        "descrizione_breve": serializers.CharField(required=False, allow_blank=True, allow_null=True),
        "tipo_voce_id": serializers.IntegerField(required=False, allow_null=True),
        "gruppo_voce_id": serializers.IntegerField(required=False, allow_null=True),
        "spesa_id": serializers.IntegerField(required=False, allow_null=True),
        "iva_id": serializers.IntegerField(required=False, allow_null=True),
        "conto_contabile_vendita_id": serializers.IntegerField(required=False, allow_null=True),
        "conto_contabile_acquisto_id": serializers.IntegerField(required=False, allow_null=True),
        "is_composito": serializers.BooleanField(required=False),
        "is_solo_componente": serializers.BooleanField(required=False),
        "requires_serial": serializers.BooleanField(required=False),
        "voce_utility": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    }
    if for_create:
        fields = {
            "codice": serializers.CharField(required=True),
            "uom_id": serializers.IntegerField(required=True),
            **fields,
        }
    return fields


# Scopo: Definisce i campi write UoM operativa per schema API.
def _uom_write_fields(*, include_uom_id: bool) -> dict[str, serializers.Field]:
    fields: dict[str, serializers.Field] = {
        "is_base": serializers.BooleanField(required=False),
        "factor_to_base": serializers.DecimalField(required=False, max_digits=18, decimal_places=6),
        "is_sell_uom": serializers.BooleanField(required=False),
        "is_purchase_uom": serializers.BooleanField(required=False),
        "is_logistic_uom": serializers.BooleanField(required=False),
        "qty_step": serializers.DecimalField(required=False, max_digits=18, decimal_places=6, allow_null=True),
        "rounding_mode": serializers.CharField(required=False),
        "max_decimals": serializers.IntegerField(required=False, allow_null=True),
        "forbid_fraction": serializers.BooleanField(required=False),
        "require_lot": serializers.BooleanField(required=False),
        "gtin": serializers.CharField(required=False, allow_blank=True, allow_null=True),
        "valido_dal": serializers.DateField(required=False, allow_null=True),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    }
    if include_uom_id:
        fields = {"uom_id": serializers.IntegerField(required=True), **fields}
    return fields


# Scopo: Definisce i campi write componente BoM per schema API.
def _componente_write_fields(*, include_componente_id: bool) -> dict[str, serializers.Field]:
    fields: dict[str, serializers.Field] = {
        "coeff_qta": serializers.DecimalField(required=False, max_digits=18, decimal_places=6),
        "partecipa_qta": serializers.BooleanField(required=False),
        "determina_qta_padre": serializers.BooleanField(required=False),
        "obbligatorio": serializers.BooleanField(required=False),
        "valido_dal": serializers.DateField(required=False),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    }
    if include_componente_id:
        fields = {"componente_id": serializers.UUIDField(required=True), **fields}
    return fields


# Scopo: Definisce i campi write nota catalogo per schema API.
def _nota_write_fields() -> dict[str, serializers.Field]:
    return {
        "target_riga_id": serializers.UUIDField(required=False, allow_null=True),
        "anchor_tipo": serializers.CharField(required=False),
        "posizione": serializers.CharField(required=False),
        "seq": serializers.IntegerField(required=False, allow_null=True),
        "testo": serializers.CharField(required=False, allow_blank=True, allow_null=True),
        "testo_md": serializers.CharField(required=False, allow_blank=True, allow_null=True),
        "id_stile": serializers.IntegerField(required=False),
        "id_lingua": serializers.IntegerField(required=False, allow_null=True),
        "visibile": serializers.BooleanField(required=False),
        "solo_stampa": serializers.BooleanField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
    }

_ARTICOLO_CREATE_REQUEST = inline_serializer(
    name="CatalogoArticoloCreateRequest",
    fields=_articolo_write_fields(for_create=True),
)

_ARTICOLO_PATCH_REQUEST = inline_serializer(
    name="CatalogoArticoloPatchRequest",
    fields=_articolo_write_fields(for_create=False),
)

_UOM_CREATE_REQUEST = inline_serializer(
    name="CatalogoUomOperativaCreateRequest",
    fields=_uom_write_fields(include_uom_id=True),
)

_UOM_PATCH_REQUEST = inline_serializer(
    name="CatalogoUomOperativaPatchRequest",
    fields=_uom_write_fields(include_uom_id=False),
)

_COMPONENTE_CREATE_REQUEST = inline_serializer(
    name="CatalogoComponenteCreateRequest",
    fields=_componente_write_fields(include_componente_id=True),
)

_COMPONENTE_PATCH_REQUEST = inline_serializer(
    name="CatalogoComponentePatchRequest",
    fields=_componente_write_fields(include_componente_id=False),
)

_NOTA_CREATE_REQUEST = inline_serializer(
    name="CatalogoNotaCreateRequest",
    fields=_nota_write_fields(),
)

_NOTA_PATCH_REQUEST = inline_serializer(
    name="CatalogoNotaPatchRequest",
    fields=_nota_write_fields(),
)


class ApiArticoliList(DomainAPIView):
    area_funzionale = "catalogo"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="is_composito", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="voce_utility", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="tipo_voce_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="gruppo_voce_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="data_da", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="data_a", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: inline_serializer(
            name="CatalogoArticoliListResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce via GET la lista paginata articoli con filtri e ricerca.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="descrizione")
        require_min_search_length(p["search"], field_name="search")

        results, total = fn_list_articoli(
            attivo=_optional_qp_bool(request, "attivo"),
            is_composito=_optional_qp_bool(request, "is_composito"),
            voce_utility=_optional_qp_bool(request, "voce_utility"),
            tipo_voce_id=_optional_qp_int_strict(request, "tipo_voce_id"),
            gruppo_voce_id=_optional_qp_int_strict(request, "gruppo_voce_id"),
            search=p["search"],
            data_da=_optional_qp_iso_date(request, "data_da"),
            data_a=_optional_qp_iso_date(request, "data_a"),
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=_ARTICOLO_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Crea un nuovo articolo e restituisce il dettaglio completo.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=fn_create_articolo)


class ApiArticoloDetail(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloDetailResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce il dettaglio singolo di un articolo.
    def get(self, request: Request, articolo_id: UUID) -> JsonResponse:
        del request
        return success_response(fn_get_articolo(articolo_id))

    @extend_schema(
        request=_ARTICOLO_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUpdateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna un articolo sui soli campi presenti, con codice immutabile.
    def patch(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return success_response(fn_update_articolo(articolo_id, request.data))


class ApiArticoloDisattiva(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        request=inline_serializer(name="CatalogoArticoloDisattivaRequest", fields={}),
        responses={
            200: inline_serializer(
                name="CatalogoArticoloDisattivaResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Disattiva soft un articolo e restituisce il dettaglio aggiornato.
    def post(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return handle_post_json(request, handler=lambda _payload: fn_disattiva_articolo(articolo_id))


class ApiArticoloUomList(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUomListResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Lista le UoM operative di un articolo.
    def get(self, request: Request, articolo_id: UUID) -> JsonResponse:
        del request
        return success_response(fn_list_uom_operative(articolo_id))

    @extend_schema(
        request=_UOM_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUomCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiunge una UoM operativa all'articolo.
    def post(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return handle_post_json(request, handler=lambda payload: fn_create_uom_operativa(articolo_id, payload))


class ApiArticoloUomDetail(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        request=_UOM_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUomUpdateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna una UoM operativa dell'articolo.
    def patch(self, request: Request, articolo_id: UUID, uom_op_id: int) -> JsonResponse:
        return success_response(fn_update_uom_operativa(articolo_id, uom_op_id, request.data))

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloUomDeleteResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Elimina una UoM operativa dell'articolo.
    def delete(self, request: Request, articolo_id: UUID, uom_op_id: int) -> JsonResponse:
        del request
        return success_response(fn_delete_uom_operativa(articolo_id, uom_op_id))


class ApiArticoloComponentiList(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloComponentiListResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Lista i componenti BoM dell'articolo.
    def get(self, request: Request, articolo_id: UUID) -> JsonResponse:
        del request
        return success_response(fn_list_componenti(articolo_id))

    @extend_schema(
        request=_COMPONENTE_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloComponenteCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiunge un componente BoM all'articolo.
    def post(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return handle_post_json(request, handler=lambda payload: fn_create_componente(articolo_id, payload))


class ApiArticoloComponenteDetail(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        request=_COMPONENTE_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloComponenteUpdateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna un componente BoM dell'articolo.
    def patch(self, request: Request, articolo_id: UUID, comp_id: UUID) -> JsonResponse:
        return success_response(fn_update_componente(articolo_id, comp_id, request.data))

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloComponenteDeleteResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Elimina un componente BoM dell'articolo.
    def delete(self, request: Request, articolo_id: UUID, comp_id: UUID) -> JsonResponse:
        del request
        return success_response(fn_delete_componente(articolo_id, comp_id))


class ApiArticoloNoteList(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoArticoloNoteListResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Lista le note articolo.
    def get(self, request: Request, articolo_id: UUID) -> JsonResponse:
        del request
        return success_response(fn_list_note_articolo(articolo_id))

    @extend_schema(
        request=_NOTA_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoArticoloNotaCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Crea una nuova nota articolo.
    def post(self, request: Request, articolo_id: UUID) -> JsonResponse:
        return handle_post_json(request, handler=lambda payload: fn_create_nota_articolo(articolo_id, payload))


class ApiNotaDetail(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        request=_NOTA_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="CatalogoNotaUpdateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna una nota catalogo esistente.
    def patch(self, request: Request, nota_id: int) -> JsonResponse:
        return success_response(fn_update_nota(nota_id, request.data))

    @extend_schema(
        responses={
            200: inline_serializer(
                name="CatalogoNotaDeleteResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Elimina una nota catalogo esistente.
    def delete(self, request: Request, nota_id: int) -> JsonResponse:
        del request
        return success_response(fn_delete_nota(nota_id))


class ApiComponenteNoteList(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        responses={200: inline_serializer(
            name="CatalogoComponenteNoteListResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Lista le note di un componente articolo.
    def get(self, request: Request, articolo_id: UUID, comp_id: UUID) -> JsonResponse:
        del request, articolo_id
        return success_response(fn_list_note_componente(comp_id))

    @extend_schema(
        request=_NOTA_CREATE_REQUEST,
        responses={200: inline_serializer(
            name="CatalogoComponenteNotaCreateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Crea una nota per un componente articolo.
    def post(self, request: Request, articolo_id: UUID, comp_id: UUID) -> JsonResponse:
        del articolo_id
        return handle_post_json(request, handler=lambda payload: fn_create_nota_componente(comp_id, payload))


class ApiArticoliLookup(DomainAPIView):
    area_funzionale = "catalogo"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="voce_utility", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="is_composito", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="is_solo_componente", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: inline_serializer(
                name="CatalogoArticoliLookupResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce il lookup articoli per autocomplete cross-dominio.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        search = qp_str(qp.get("search"))
        require_min_search_length(search, field_name="search")

        data = fn_lookup_articoli(
            search=search,
            voce_utility=_optional_qp_bool(request, "voce_utility"),
            attivo=qp_bool(qp.get("attivo"), True),
            is_composito=_optional_qp_bool(request, "is_composito"),
            is_solo_componente=_optional_qp_bool(request, "is_solo_componente"),
            limit=qp_int_strict(qp.get("limit"), "limit", 20),
        )
        return success_response(data)


    # Nota: il lookup UoM usa l'endpoint generico /api/v1/core/lookup/codici/?rel=catalogo.unita_misura


# --- CRUD Unita' di Misura ---


class ApiUnitaMisuraList(DomainAPIView):
    area_funzionale = "catalogo"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraListResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce lista paginata unita' di misura.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="codice")
        require_min_search_length(p["search"], field_name="search")
        results, total = fn_list_unita_misura(
            attivo=_optional_qp_bool(request, "attivo"),
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=inline_serializer(
            name="CatalogoUnitaMisuraCreateRequest",
            fields={
                "codice": serializers.CharField(required=True),
                "descrizione": serializers.CharField(required=True),
                "descrizione_fattura": serializers.CharField(required=False, allow_blank=True, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraCreateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Crea una nuova unita' di misura.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=fn_create_unita_misura)


class ApiUnitaMisuraDetail(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraDetailResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce dettaglio singola unita' di misura.
    def get(self, request: Request, uom_id: int) -> JsonResponse:
        del request
        return success_response(fn_get_unita_misura(uom_id))

    @extend_schema(
        request=inline_serializer(
            name="CatalogoUnitaMisuraPatchRequest",
            fields={
                "descrizione": serializers.CharField(required=False),
                "descrizione_fattura": serializers.CharField(required=False, allow_blank=True, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraUpdateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Aggiorna una unita' di misura.
    def patch(self, request: Request, uom_id: int) -> JsonResponse:
        return success_response(fn_update_unita_misura(uom_id, request.data))


class ApiUnitaMisuraDisattiva(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        request=inline_serializer(name="CatalogoUnitaMisuraDisattivaRequest", fields={}),
        responses={200: inline_serializer(
            name="CatalogoUnitaMisuraDisattivaResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Disattiva una unita' di misura.
    def post(self, request: Request, uom_id: int) -> JsonResponse:
        return handle_post_json(request, handler=lambda _payload: fn_disattiva_unita_misura(uom_id))


# =================================================================
# Conversioni UoM
# =================================================================

class ApiConversioniList(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="attivo", type=bool, required=False, description="Filtro attivo (null=tutti)"),
            OpenApiParameter(name="uom_id", type=int, required=False, description="Filtra conversioni per UoM (from o to)"),
        ],
        responses={200: inline_serializer(
            name="CatalogoConversioniListResponse",
            fields={"data": serializers.ListField(child=serializers.DictField()), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Lista completa conversioni UoM (dataset piccolo, no paginazione).
    #        Filtro opzionale uom_id per mostrare conversioni di una specifica UoM.
    def get(self, request: Request) -> JsonResponse:
        uom_id_raw = request.query_params.get("uom_id")
        uom_id = int(uom_id_raw) if uom_id_raw else None
        result = fn_list_conversioni(uom_id=uom_id)
        return success_response(result)

    @extend_schema(
        request=inline_serializer(
            name="CatalogoConversioneCreateRequest",
            fields={
                "uom_from_id": serializers.IntegerField(required=True),
                "uom_to_id": serializers.IntegerField(required=True),
                "fattore": serializers.DecimalField(max_digits=18, decimal_places=6, required=True),
                "valido_dal": serializers.DateField(required=False, allow_null=True),
                "valido_al": serializers.DateField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoConversioneCreateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Crea una nuova conversione UoM.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=fn_create_conversione)


class ApiConversioneDetail(DomainAPIView):
    area_funzionale = "catalogo"

    @extend_schema(
        responses={200: inline_serializer(
            name="CatalogoConversioneDetailResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Restituisce dettaglio singola conversione UoM.
    def get(self, request: Request, conv_id: int) -> JsonResponse:
        del request
        return success_response(fn_get_conversione(conv_id))

    @extend_schema(
        request=inline_serializer(
            name="CatalogoConversionePatchRequest",
            fields={
                "fattore": serializers.DecimalField(max_digits=18, decimal_places=6, required=False),
                "valido_dal": serializers.DateField(required=False, allow_null=True),
                "valido_al": serializers.DateField(required=False, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="CatalogoConversioneUpdateResponse",
            fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
        )},
    )
    # Scopo: Aggiorna una conversione UoM.
    def patch(self, request: Request, conv_id: int) -> JsonResponse:
        return success_response(fn_update_conversione(conv_id, request.data))
