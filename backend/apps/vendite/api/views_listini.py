# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view vendite/listini per CRUD listini, versioni, righe, associazioni e test resolver.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import paginated_envelope, parse_list_params, qp_bool, qp_int_strict, qp_str
from apps.core.api.search_validators import require_min_search_length
from apps.core.api.success_responses import success_response
from apps.vendite.services.listini_service import (
    fn_alert_scadenze,
    fn_applica_variazione_percentuale,
    fn_change_versione_state,
    fn_rettifica_controllata_riga,
    fn_clone_versione,
    fn_create_associazione,
    fn_create_listino,
    fn_create_riga,
    fn_create_versione,
    fn_delete_associazione,
    fn_delete_listino,
    fn_delete_riga,
    fn_delete_versione,
    fn_get_listino_dettaglio,
    fn_get_versione,
    fn_list_associazioni,
    fn_list_listini,
    fn_list_righe,
    fn_list_versioni,
    fn_test_resolver_prezzo,
    fn_update_associazione,
    fn_update_listino,
    fn_update_riga,
    fn_update_versione,
)


# Scopo: Estrae un bool opzionale da query string con validazione rigorosa.
def _optional_qp_bool_strict(request: Request, key: str) -> bool | None:
    raw_value = request.query_params.get(key)
    if raw_value is None:
        return None
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{key}_invalid")


# Scopo: Definisce in un solo punto i campi write listino per schema API.
def _listino_write_fields(*, include_codice: bool) -> dict[str, serializers.Field]:
    fields: dict[str, serializers.Field] = {
        "descrizione": serializers.CharField(required=False),
        "utility_id": serializers.IntegerField(required=False, allow_null=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
    }
    if include_codice:
        fields = {"codice": serializers.CharField(required=True), **fields}
    return fields


# Scopo: Definisce i campi write versione listino per schema API.
def _versione_write_fields() -> dict[str, serializers.Field]:
    return {
        "codice_versione": serializers.CharField(required=False),
        "valido_dal": serializers.DateField(required=False),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
    }


# Scopo: Definisce i campi write riga listino per schema API.
def _riga_write_fields(*, include_identity: bool) -> dict[str, serializers.Field]:
    fields: dict[str, serializers.Field] = {
        "billing_account_id": serializers.IntegerField(required=False, allow_null=True),
        "utility_id": serializers.IntegerField(required=False, allow_null=True),
        "emittente_soggetto_ruolo_id": serializers.IntegerField(required=False, allow_null=True),
        "prezzo": serializers.DecimalField(required=False, max_digits=22, decimal_places=10),
        "meta": serializers.JSONField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
    }
    if include_identity:
        fields = {
            "articolo_id": serializers.UUIDField(required=True),
            "uom_id": serializers.IntegerField(required=True),
            **fields,
        }
    return fields


# Scopo: Definisce i campi write associazione listino per schema API.
def _associazione_write_fields() -> dict[str, serializers.Field]:
    return {
        "billing_account_id": serializers.IntegerField(required=False, allow_null=True),
        "utility_id": serializers.IntegerField(required=False, allow_null=True),
        "emittente_soggetto_ruolo_id": serializers.IntegerField(required=False, allow_null=True),
        "valido_dal": serializers.DateField(required=False),
        "valido_al": serializers.DateField(required=False, allow_null=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
    }


_LISTINO_CREATE_REQUEST = inline_serializer(
    name="VenditeListinoCreateRequest",
    fields=_listino_write_fields(include_codice=True),
)
_LISTINO_PATCH_REQUEST = inline_serializer(
    name="VenditeListinoPatchRequest",
    fields=_listino_write_fields(include_codice=False),
)
_VERSIONE_CREATE_REQUEST = inline_serializer(
    name="VenditeListinoVersioneCreateRequest",
    fields=_versione_write_fields(),
)
_VERSIONE_PATCH_REQUEST = inline_serializer(
    name="VenditeListinoVersionePatchRequest",
    fields=_versione_write_fields(),
)
_VERSIONE_STATO_REQUEST = inline_serializer(
    name="VenditeListinoVersioneStatoRequest",
    fields={
        "stato": serializers.CharField(required=True),
        "dry_run": serializers.BooleanField(required=False),
    },
)
_VERSIONE_CLONA_REQUEST = inline_serializer(
    name="VenditeListinoVersioneClonaRequest",
    fields={
        "codice_versione": serializers.CharField(required=True),
        "valido_dal": serializers.DateField(required=True),
        "valido_al": serializers.DateField(required=False, allow_null=True),
    },
)
_RIGA_CREATE_REQUEST = inline_serializer(
    name="VenditeListinoRigaCreateRequest",
    fields=_riga_write_fields(include_identity=True),
)
_RIGA_PATCH_REQUEST = inline_serializer(
    name="VenditeListinoRigaPatchRequest",
    fields=_riga_write_fields(include_identity=False),
)
_ASSOCIAZIONE_CREATE_REQUEST = inline_serializer(
    name="VenditeListinoAssociazioneCreateRequest",
    fields=_associazione_write_fields(),
)
_RETTIFICA_CONTROLLATA_REQUEST = inline_serializer(
    name="VenditeListinoRettificaControllataRequest",
    fields={
        "prezzo": serializers.DecimalField(required=True, max_digits=22, decimal_places=10),
        "motivo": serializers.CharField(required=True),
    },
)
_VARIAZIONE_PCT_REQUEST = inline_serializer(
    name="VenditeListinoVariazionePercentualeRequest",
    fields={
        "variazione_percentuale": serializers.DecimalField(required=True, max_digits=10, decimal_places=4),
        "arrotondamento_decimali": serializers.IntegerField(required=False),
        "filtro_articoli": serializers.ListField(child=serializers.UUIDField(), required=False, allow_null=True),
        "dry_run": serializers.BooleanField(required=False),
    },
)
_ASSOCIAZIONE_PATCH_REQUEST = inline_serializer(
    name="VenditeListinoAssociazionePatchRequest",
    fields=_associazione_write_fields(),
)
_RESOLVER_TEST_REQUEST = inline_serializer(
    name="VenditeListinoResolverTestRequest",
    fields={
        "articolo_id": serializers.UUIDField(required=True),
        "uom_id": serializers.IntegerField(required=True),
        "data_riferimento": serializers.DateField(required=True),
        "billing_account_id": serializers.IntegerField(required=False, allow_null=True),
        "utility_id": serializers.IntegerField(required=False, allow_null=True),
        "emittente_soggetto_ruolo_id": serializers.IntegerField(required=False, allow_null=True),
    },
)


class ApiListiniList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="utility_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: inline_serializer(
                name="VenditeListiniListResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce via GET la lista paginata dei listini.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="codice")
        require_min_search_length(p["search"], field_name="search")
        results, total = fn_list_listini(
            utility_id=qp_int_strict(qp.get("utility_id"), "utility_id", 0) if qp.get("utility_id") else None,
            attivo=_optional_qp_bool_strict(request, "attivo"),
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=_LISTINO_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Crea un nuovo listino.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=fn_create_listino)


class ApiListinoDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoDetailResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce il dettaglio del listino con versioni e associazioni.
    def get(self, request: Request, listino_id: int) -> JsonResponse:
        del request
        return success_response(fn_get_listino_dettaglio(listino_id))

    @extend_schema(
        request=_LISTINO_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoPatchResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna il listino.
    def patch(self, request: Request, listino_id: int) -> JsonResponse:
        return success_response(fn_update_listino(listino_id, request.data))

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoDeleteResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Elimina un listino mai usato (zero versioni e zero associazioni).
    def delete(self, request: Request, listino_id: int) -> JsonResponse:
        del request
        return success_response(fn_delete_listino(listino_id))


class ApiListinoVersioniList(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoVersioniListResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce via GET la lista versioni del listino.
    def get(self, request: Request, listino_id: int) -> JsonResponse:
        del request
        return success_response(fn_list_versioni(listino_id))

    @extend_schema(
        request=_VERSIONE_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoVersioneCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Crea una nuova versione del listino.
    def post(self, request: Request, listino_id: int) -> JsonResponse:
        return handle_post_json(request, handler=lambda payload: fn_create_versione(listino_id, payload))


class ApiListinoVersioneDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoVersioneDetailResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce il dettaglio singolo della versione.
    def get(self, request: Request, listino_id: int, ver_id: int) -> JsonResponse:
        del request
        return success_response(fn_get_versione(listino_id, ver_id))

    @extend_schema(
        request=_VERSIONE_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoVersionePatchResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna la versione del listino.
    def patch(self, request: Request, listino_id: int, ver_id: int) -> JsonResponse:
        return success_response(fn_update_versione(listino_id, ver_id, request.data))

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoVersioneDeleteResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Elimina una versione in stato BOZZA con tutte le sue righe.
    def delete(self, request: Request, listino_id: int, ver_id: int) -> JsonResponse:
        del request
        return success_response(fn_delete_versione(listino_id, ver_id))


class ApiListinoVersioneStato(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_VERSIONE_STATO_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoVersioneStatoResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Cambia lo stato operativo della versione del listino.
    def post(self, request: Request, listino_id: int, ver_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: fn_change_versione_state(listino_id, ver_id, payload),
        )


class ApiListinoVersioneClona(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_VERSIONE_CLONA_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoVersioneClonaResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Clona una versione esistente in una nuova versione BOZZA dello
    #        stesso listino, copiando le righe attive. Workflow "cambio prezzi".
    def post(self, request: Request, listino_id: int, src_ver_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: fn_clone_versione(listino_id, src_ver_id, payload),
        )


class ApiListinoVersioneRigheList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="billing_account_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="utility_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="attivo", type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: inline_serializer(
                name="VenditeListinoRigheListResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce via GET la lista paginata righe prezzo della versione con filtri.
    def get(self, request: Request, listino_id: int, ver_id: int) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="articolo_descrizione")
        results, total = fn_list_righe(
            listino_id,
            ver_id,
            search=p["search"],
            billing_account_id=qp_int_strict(qp.get("billing_account_id"), "billing_account_id", 0) if qp.get("billing_account_id") else None,
            utility_id=qp_int_strict(qp.get("utility_id"), "utility_id", 0) if qp.get("utility_id") else None,
            attivo=_optional_qp_bool_strict(request, "attivo"),
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        request=_RIGA_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoRigaCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Crea una nuova riga prezzo nella versione.
    def post(self, request: Request, listino_id: int, ver_id: int) -> JsonResponse:
        return handle_post_json(request, handler=lambda payload: fn_create_riga(listino_id, ver_id, payload))


class ApiListinoVersioneRigaDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_RIGA_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoRigaPatchResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna la riga prezzo della versione.
    def patch(self, request: Request, listino_id: int, ver_id: int, riga_id: int) -> JsonResponse:
        return success_response(fn_update_riga(listino_id, ver_id, riga_id, request.data))

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoRigaDeleteResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Elimina la riga prezzo della versione.
    def delete(self, request: Request, listino_id: int, ver_id: int, riga_id: int) -> JsonResponse:
        del request
        return success_response(fn_delete_riga(listino_id, ver_id, riga_id))


class ApiListinoAssociazioniList(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoAssociazioniListResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce via GET la lista associazioni del listino.
    def get(self, request: Request, listino_id: int) -> JsonResponse:
        del request
        return success_response(fn_list_associazioni(listino_id))

    @extend_schema(
        request=_ASSOCIAZIONE_CREATE_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoAssociazioneCreateResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Crea una nuova associazione del listino.
    def post(self, request: Request, listino_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: fn_create_associazione(listino_id, payload),
        )


class ApiListinoAssociazioneDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_ASSOCIAZIONE_PATCH_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoAssociazionePatchResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Aggiorna una associazione listino.
    def patch(self, request: Request, listino_id: int, assoc_id: int) -> JsonResponse:
        return success_response(fn_update_associazione(listino_id, assoc_id, request.data))

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoAssociazioneDeleteResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Elimina una associazione listino.
    def delete(self, request: Request, listino_id: int, assoc_id: int) -> JsonResponse:
        del request
        return success_response(fn_delete_associazione(listino_id, assoc_id))


class ApiListinoTestPrezzo(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_RESOLVER_TEST_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoResolverTestResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Esegue il test del resolver prezzo per uso UI/diagnostica.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=fn_test_resolver_prezzo)


class ApiListinoVersioneRigaRettificaControllata(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_RETTIFICA_CONTROLLATA_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoRettificaControllataResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Rettifica controllata su riga ATTIVA non propagata (N6).
    #        Endpoint dedicato separato dal PATCH ordinario.
    def patch(self, request: Request, listino_id: int, ver_id: int, riga_id: int) -> JsonResponse:
        return success_response(
            fn_rettifica_controllata_riga(listino_id, ver_id, riga_id, request.data)
        )


class ApiListiniAlertScadenze(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="giorni", type=int, required=False, description="Giorni di anticipo (default 15)"),
        ],
        responses={
            200: inline_serializer(
                name="VenditeListiniAlertScadenzeResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce versioni ATTIVE in scadenza senza successore.
    def get(self, request: Request) -> JsonResponse:
        giorni = qp_int_strict(request, "giorni", default=15)
        return success_response(fn_alert_scadenze(giorni))


class ApiListinoVersioneApplicaVariazione(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=_VARIAZIONE_PCT_REQUEST,
        responses={
            200: inline_serializer(
                name="VenditeListinoVariazionePercentualeResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Applica variazione percentuale massa ai prezzi delle righe attive
    #        di una versione BOZZA. Supporta dry_run per preview.
    def post(self, request: Request, listino_id: int, ver_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: fn_applica_variazione_percentuale(listino_id, ver_id, payload),
        )
