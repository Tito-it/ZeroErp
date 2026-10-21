# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view vendite/listini per CRUD listini, versioni, righe.
#        F2-BE-13: rimossi endpoint `associazioni` e `test-prezzo` (resolver
#        vecchio sostituito da `fn_resolve_prezzo_listino_v2` in pricing_service).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import corpo_oggetto, paginated_envelope, parse_list_params, qp_bool_optional, qp_int_optional, qp_int_strict, qp_str
from apps.core.api.success_responses import success_response
from apps.vendite.services.listini_service import (
    fn_alert_scadenze,
    fn_applica_variazione_percentuale,
    fn_change_versione_state,
    fn_rettifica_controllata_riga,
    fn_clone_versione,
    fn_create_listino,
    fn_create_riga,
    fn_create_versione,
    fn_delete_bundle,
    fn_delete_listino,
    fn_delete_riga,
    fn_delete_versione,
    fn_get_listino_dettaglio,
    fn_get_versione,
    fn_list_listini,
    fn_list_righe,
    fn_list_tipologie_per_utility,
    fn_list_versioni,
    fn_preview_bundle,
    fn_save_bundle,
    fn_update_listino,
    fn_update_riga,
    fn_update_versione,
)


# Scopo: Definisce i campi write listino per lo schema OpenAPI.
#        Schemi separati per create/patch: in create `utility_id` e
#        `tipologia_id` sono obbligatori (la colonna DB e' NOT NULL); in patch
#        sono opzionali ma se inviati non-nullable. La validazione applicativa
#        resta nel service.
def _listino_write_fields_create() -> dict[str, serializers.Field]:
    return {
        "codice": serializers.CharField(required=True),
        "descrizione": serializers.CharField(required=True),
        "utility_id": serializers.IntegerField(required=True),
        "tipologia_id": serializers.IntegerField(required=True),
        "meta": serializers.JSONField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
    }


def _listino_write_fields_patch() -> dict[str, serializers.Field]:
    return {
        "descrizione": serializers.CharField(required=False),
        "utility_id": serializers.IntegerField(required=False),
        "tipologia_id": serializers.IntegerField(required=False),
        "meta": serializers.JSONField(required=False, allow_null=True),
        "attivo": serializers.BooleanField(required=False),
    }


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
    # ⛔ Niente `billing_account_id`/`utility_id`/`emittente_soggetto_ruolo_id`:
    #    la riga non li ha piu' (F1-DB-25, il contesto vive su listino e
    #    contratto), e il service li rifiuta con un 400. Fino al 2026-10-20 lo
    #    schema li pubblicava ancora: un client generato li mandava e sbatteva.
    fields: dict[str, serializers.Field] = {
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


_LISTINO_CREATE_REQUEST = inline_serializer(
    name="VenditeListinoCreateRequest",
    fields=_listino_write_fields_create(),
)
_LISTINO_PATCH_REQUEST = inline_serializer(
    name="VenditeListinoPatchRequest",
    fields=_listino_write_fields_patch(),
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
    model_permission = ("vendite", "listino")
    is_search_endpoint = True
    lista_codice = "vendite.listini"

    @extend_schema(
        parameters=[
            # ⛔ Nessun 400 sotto soglia (brief-db-be-fe-ricerca-soglia-per-lista
            #    §6 a, Tid 2026-09-26): il termine corto lo ignora il BB, sulla
            #    soglia del catalogo.
            param_ricerca_full(),
            OpenApiParameter(name="utility_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="tipologia_id", type=int, location=OpenApiParameter.QUERY, required=False),
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
    #        I filtri utility_id/tipologia_id sono normalizzati via qp_str per
    #        trattare stringa vuota come "assente" ed evitare che il filtro
    #        venga ignorato silenziosamente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="codice")
        # BB `qp_int_optional`: vuoto = assente, un non intero e' un 400.
        results, total = fn_list_listini(
            utility_id=qp_int_optional(qp.get("utility_id"), "utility_id"),
            tipologia_id=qp_int_optional(qp.get("tipologia_id"), "tipologia_id"),
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
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
    model_permission = ("vendite", "listino")

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoDetailResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce il dettaglio del listino con versioni.
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
        return success_response(fn_update_listino(listino_id, corpo_oggetto(request)))

    @extend_schema(
        responses={
            200: inline_serializer(
                name="VenditeListinoDeleteResponse",
                fields={"data": serializers.DictField(), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Elimina un listino mai usato (zero versioni).
    def delete(self, request: Request, listino_id: int) -> JsonResponse:
        del request
        return success_response(fn_delete_listino(listino_id))


class ApiListinoVersioniList(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

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
    model_permission = ("vendite", "listino")

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
        return success_response(fn_update_versione(listino_id, ver_id, corpo_oggetto(request)))

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
    model_permission = ("vendite", "listino")

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
    model_permission = ("vendite", "listino")

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
    model_permission = ("vendite", "listino")
    is_search_endpoint = True
    lista_codice = "vendite.listini_righe"

    @extend_schema(
        parameters=[
            param_ricerca_full(),
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
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
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
    model_permission = ("vendite", "listino")

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
        return success_response(fn_update_riga(listino_id, ver_id, riga_id, corpo_oggetto(request)))

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


class ApiListinoVersioneRigaRettificaControllata(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

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
            fn_rettifica_controllata_riga(listino_id, ver_id, riga_id, corpo_oggetto(request))
        )


class ApiListiniAlertScadenze(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

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
        # ⚠️ Il VALORE del parametro, non la request: fino al 2026-10-09 qui si
        #    passava `request`, e l'endpoint rispondeva 400 `giorni_invalid` a ogni
        #    chiamata (il badge di AlertScadenzeWidget non si accendeva mai).
        giorni = qp_int_strict(request.query_params.get("giorni"), "giorni", default=15)
        return success_response(fn_alert_scadenze(giorni))


class ApiListinoVersioneApplicaVariazione(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

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


class ApiListiniTipologiePerUtility(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

    @extend_schema(
        parameters=[
            OpenApiParameter(name="utility_id", type=int, location=OpenApiParameter.QUERY, required=True),
        ],
        responses={
            200: inline_serializer(
                name="VenditeListiniTipologiePerUtilityResponse",
                fields={"data": serializers.ListField(child=serializers.DictField()), "meta": serializers.DictField(required=False)},
            )
        },
    )
    # Scopo: Restituisce le tipologie listino ammesse per una utility dalla
    #        matrice config.listini_tipologie_utilities. Usato dal drawer listino
    #        per popolare il Select tipologia al cambio utility.
    #        Nota: config.listini_tipologie e' tabella globale, non filtrata per
    #        emittente (no scope check). Envelope allineato ai lookup dedicati:
    #        success_response aggiunge il wrap "data" automaticamente.
    def get(self, request: Request) -> JsonResponse:
        raw_utility_id = qp_str(request.query_params.get("utility_id"))
        if raw_utility_id is None:
            from apps.core.services.error_manager import ErrorManager

            ErrorManager.raise_error(
                code="E_VENDITE_VALIDATION",
                message="Parametro utility non valido.",
                detail="utility_id e' obbligatorio.",
                context={"field": "utility_id"},
                function_name="vendite.api.ApiListiniTipologiePerUtility.get",
                log_to_db=True,
            )
        utility_id = qp_int_strict(raw_utility_id, "utility_id", 0)
        return success_response({"results": fn_list_tipologie_per_utility(utility_id)})


# ── Bundle componenti BoM (modello unificato 2026-05-13) ──
#
# 3 endpoint per gestire `listini_righe_componenti` (prezzi bundle dei
# figli BoM di un padre composito in contesto versione listino):
#   - GET  /listini/<lid>/versioni/<vid>/bundle/                lista compositi con bundle definito
#   - GET  /listini/<lid>/versioni/<vid>/bundle/<padre_id>/     preview BoM + prezzi esistenti
#   - POST /listini/<lid>/versioni/<vid>/bundle/<padre_id>/     upsert batch prezzi bundle
#
# Persistenza assoluta (no delta). Solo versioni BOZZA editabili
# (guard service + trigger DB immutabilita' v5).



class ApiListinoVersioneBundleDetail(DomainAPIView):
    """GET / POST `/api/v1/vendite/listini/<lid>/versioni/<vid>/bundle/<padre_id>/`

    GET: preview BoM del padre composito + prezzi bundle gia' definiti
         per quella versione (per popolare il Dialog di editing).
    POST: upsert batch dei prezzi bundle (strategia tabula rasa
         idempotente: soft-disattiva le righe correnti + inserisce le
         nuove). Solo versione BOZZA editabile.
    """

    area_funzionale = "vendite"
    model_permission = ("vendite", "listino")

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeListinoVersioneBundlePreviewResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Preview BoM + prezzi bundle gia' definiti.
    def get(
        self, request: Request, listino_id: int, ver_id: int, padre_id: str,
    ) -> JsonResponse:
        results = fn_preview_bundle(listino_id, ver_id, padre_id)
        return success_response(results)

    @extend_schema(
        request=inline_serializer(
            name="VenditeListinoVersioneBundleSaveRequest",
            fields={
                "rows": serializers.ListField(
                    child=serializers.DictField(),
                    help_text=(
                        "Lista oggetti {articolo_componente_id, "
                        "articolo_figlio_id, prezzo, iva_id?}. Righe con "
                        "`prezzo` null vengono ignorate (non gestite a bundle)."
                    ),
                ),
            },
        ),
        responses={200: inline_serializer(
            name="VenditeListinoVersioneBundleSaveResponse",
            fields={"data": inline_serializer(
                name="VenditeListinoVersioneBundleSaveData",
                fields={
                    "disattivati": serializers.IntegerField(),
                    "inseriti": serializers.IntegerField(),
                },
            )},
        )},
    )
    # Scopo: Upsert batch dei prezzi bundle per il padre composito.
    def post(
        self, request: Request, listino_id: int, ver_id: int, padre_id: str,
    ) -> JsonResponse:
        # ⛔ `rows` passa GREZZO: la forma la giudica il BB `voci` nel service
        #    (assente o non lista = 400). Fino al 2026-10-21 qui un corpo senza
        #    `rows` diventava `[]`, e il salvataggio — che sostituisce il bundle
        #    in blocco — cancellava ogni prezzo rispondendo 200. Una lista
        #    vuota ESPLICITA resta il modo di svuotarlo.
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return fn_save_bundle(listino_id, ver_id, padre_id, payload.get("rows"))

        return handle_post_json(request, handler=_handler)

    @extend_schema(
        responses={200: inline_serializer(
            name="VenditeListinoVersioneBundleDeleteResponse",
            fields={"data": inline_serializer(
                name="VenditeListinoVersioneBundleDeleteData",
                fields={
                    "disattivati": serializers.IntegerField(),
                    "inseriti": serializers.IntegerField(),
                },
            )},
        )},
    )
    # Scopo: Elimina tutti i prezzi bundle del composito dalla versione
    # listino. Tabula rasa idempotente: soft-delete cascade su
    # `listini_righe_componenti` per la coppia (versione, padre).
    # Guard BOZZA-only ereditato dal service. Idempotente: 0 disattivati
    # senza errore se il composito non aveva prezzi bundle.
    def delete(
        self, request: Request, listino_id: int, ver_id: int, padre_id: str,
    ) -> JsonResponse:
        del request
        return success_response(
            fn_delete_bundle(listino_id, ver_id, padre_id)
        )
