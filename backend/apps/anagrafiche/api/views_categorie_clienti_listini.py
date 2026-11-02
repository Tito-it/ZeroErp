# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views admin per la matrice anagrafiche.categorie_clienti_listini.
#        CRUD admin. Chiave di lookup dello STADIO 2 del resolver prezzi v5:
#        categoria x utility x emittente x classe_utenza (opz) -> listino.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.anagrafiche.services.categorie_clienti_listini_service import (
    CategorieClientiListiniService,
)
from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.payload_validators import (
    corpo_oggetto,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
)
from apps.core.api.request_parsers import parse_iso_date
from apps.core.api.success_responses import success_response


# =================================================================
# Lista + creazione
# =================================================================


class CategorieClientiListiniView(AdminAPIView):
    """GET lista paginata, POST crea riga matrice (admin only)."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="attivo", type=bool, required=False),
            OpenApiParameter(name="categoria_cliente_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="emittente_soggetto_ruolo_id", type=int, required=False),
            OpenApiParameter(name="listino_id", type=int, required=False),
            OpenApiParameter(name="valid_at", type=str, required=False,
                             description="Data ISO YYYY-MM-DD: filtra righe la cui validita contiene questa data."),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False,
                             description="categoria_codice | categoria_descrizione | utility_codice | "
                                         "utility_descrizione | listino_codice | listino_descrizione | "
                                         "valido_dal | valido_al | attivo | data_insert | data_update"),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="AnagCategorieClientiListiniListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata matrice categoria/listino con filtri dimensionali.
    #        Envelope arricchito con `non_editable_fields` (Fase 4 — A9):
    #        il FE costruisce drawer di edit usando la lista al livello
    #        envelope, no round-trip aggiuntivo.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="valido_dal")
        valid_at_raw = request.query_params.get("valid_at")
        valid_at: date | None = (
            parse_iso_date(valid_at_raw) if valid_at_raw else None
        )
        svc = CategorieClientiListiniService()
        results, total = svc.list_matrice(
            search=p["search"],
            attivo=qp_bool_optional(request.query_params.get("attivo"), "attivo"),
            categoria_cliente_id=qp_int_optional(
                request.query_params.get("categoria_cliente_id"), "categoria_cliente_id"
            ),
            utility_id=qp_int_optional(
                request.query_params.get("utility_id"), "utility_id"
            ),
            emittente_soggetto_ruolo_id=qp_int_optional(
                request.query_params.get("emittente_soggetto_ruolo_id"),
                "emittente_soggetto_ruolo_id",
            ),
            listino_id=qp_int_optional(
                request.query_params.get("listino_id"), "listino_id"
            ),
            valid_at=valid_at,
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        envelope = paginated_envelope(results, total, p["page"], p["limit"])
        envelope["non_editable_fields"] = svc.get_non_editable_fields()
        return success_response(envelope)

    @extend_schema(
        request=inline_serializer(
            name="AnagCategorieClientiListiniCreateReq",
            fields={
                "categoria_cliente_id": serializers.IntegerField(),
                "utility_id": serializers.IntegerField(),
                "emittente_soggetto_ruolo_id": serializers.IntegerField(),
                "listino_id": serializers.IntegerField(),
                "classe_utenza_id": serializers.IntegerField(required=False, allow_null=True),
                "tipo_variazione": serializers.CharField(required=False, allow_null=True),
                "valore_variazione": serializers.DecimalField(
                    max_digits=10, decimal_places=4, required=False, allow_null=True,
                ),
                "valido_dal": serializers.DateField(),
                "valido_al": serializers.DateField(required=False, allow_null=True),
                "meta": serializers.JSONField(required=False, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="AnagCategorieClientiListiniCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea una nuova riga matrice categoria/listino.
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=CategorieClientiListiniService().create_matrice,
        )


# =================================================================
# Dettaglio + patch
# =================================================================


class CategorieClientiListiniDetailView(AdminAPIView):
    """GET dettaglio, PATCH aggiorna (dimensioni immutabili)."""

    @extend_schema(
        responses={200: inline_serializer(
            name="AnagCategorieClientiListiniDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio singola riga matrice.
    def get(self, request: Request, record_id: int) -> JsonResponse:
        del request
        svc = CategorieClientiListiniService()
        return success_response(svc.get_matrice(record_id))

    @extend_schema(
        request=inline_serializer(
            name="AnagCategorieClientiListiniPatchReq",
            fields={
                "listino_id": serializers.IntegerField(required=False),
                "tipo_variazione": serializers.CharField(required=False, allow_null=True),
                "valore_variazione": serializers.DecimalField(
                    max_digits=10, decimal_places=4, required=False, allow_null=True,
                ),
                "valido_dal": serializers.DateField(required=False),
                "valido_al": serializers.DateField(required=False, allow_null=True),
                "meta": serializers.JSONField(required=False, allow_null=True),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="AnagCategorieClientiListiniPatchResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna una riga matrice (dimensioni immutabili).
    def patch(self, request: Request, record_id: int) -> JsonResponse:
        svc = CategorieClientiListiniService()
        return success_response(svc.update_matrice(record_id, corpo_oggetto(request)))


# =================================================================
# Lookup statici (Fase 4)
# =================================================================


class CategorieClientiListiniTipiVariazioneLookupView(AdminAPIView):
    """GET lookup statico tipi di variazione ammessi per la matrice.

    Single source of truth in
    `categorie_clienti_listini_service._TIPI_VARIAZIONE_DESCRIZIONI`.
    Niente DB: l'enum (PERCENTUALE/VALORE_FISSO) e' un CHECK constraint,
    non una tabella. Pattern simmetrico a `EmittenteRoundingModesLookupView`
    (Fase 3 — A6).
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="AnagCategorieClientiListiniTipiVariazioneResp",
            fields={
                "data": serializers.ListField(child=serializers.DictField()),
                "meta": serializers.DictField(required=False),
            },
        )},
    )
    # Scopo: Restituisce lista statica {codice, descrizione, ordering}.
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response(
            CategorieClientiListiniService().list_tipi_variazione()
        )
