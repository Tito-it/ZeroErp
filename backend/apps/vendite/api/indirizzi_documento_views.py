# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory delle API view "indirizzi documento" (pannello slot-per-tipo:
#        GET lista+tipi ammessi, POST upsert uno-per-tipo, DELETE slot).
#        Building block condiviso dai domini vendite (design
#        brief-design-indirizzi-documenti-vendita): ogni dominio dichiara solo
#        i delta via `build_indirizzi_documento_views(...)`.
#
#        Testabilita' (stesso contratto di sorgente_documenti_views e
#        riepilogo_iva_views): i service arrivano come CLOSURE definite nel
#        modulo del dominio — i patch dei test su
#        `apps.vendite.services.<dominio>_service.*` restano validi.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response


# Scopo: Costruisce le 2 view indirizzi per un dominio documento. Ritorna un
#        SimpleNamespace con `lista` (GET+POST su .../indirizzi/) e `detail`
#        (DELETE su .../indirizzi/<indirizzo_id>/).
#        Parametri:
#         - schema_prefix: prefisso nomi OpenAPI (es. "Ddt")
#         - url_kwarg:     kwarg URL del documento (es. "ddt_id")
#         - list_call:     closure (documento_id) -> {tipi_ammessi, indirizzi}
#         - upsert_call:   closure (documento_id, payload) -> riga upsertata
#         - delete_call:   closure (documento_id, indirizzo_id) -> esito
#         - model_permission: oggetto del catalogo permessi del documento
#                          (es. ("vendite", "preventivo")): la view e' una
#                          parte dell'oggetto e ne chiede il livello
#                          (brief-db-be-fe-catalogo-oggetti-permessi §3.2).
#                          None = solo l'area.
def build_indirizzi_documento_views(
    *,
    schema_prefix: str,
    url_kwarg: str,
    list_call: Callable[[int], dict[str, Any]],
    upsert_call: Callable[[int, dict[str, Any]], dict[str, Any]],
    delete_call: Callable[[int, int], dict[str, Any]],
    model_permission: tuple[str, str] | None = None,
) -> SimpleNamespace:
    class _IndirizziView(DomainAPIView):
        area_funzionale = "vendite"

        @extend_schema(
            responses={200: inline_serializer(
                name=f"{schema_prefix}IndirizziListResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: GET pannello: tipi ammessi per l'ambito + indirizzi correnti.
        def get(self, request: Request, **kwargs: int) -> JsonResponse:
            return success_response(list_call(kwargs[url_kwarg]))

        @extend_schema(
            request=inline_serializer(
                name=f"{schema_prefix}IndirizzoUpsertRequest",
                fields={
                    "tipo_indirizzo_id": serializers.IntegerField(),
                    "origine_indirizzo_id": serializers.IntegerField(
                        required=False, allow_null=True),
                    # Provenienza anagrafica layer SOGGETTO (righe senza
                    # aggancio in anagrafiche.indirizzi): validata
                    # anti-tampering contro il cliente del documento.
                    "origine_soggetto_ruolo_id": serializers.IntegerField(
                        required=False, allow_null=True),
                    "snapshot": serializers.DictField(required=False),
                },
            ),
            responses={200: inline_serializer(
                name=f"{schema_prefix}IndirizzoUpsertResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: POST upsert slot (picker con origine_indirizzo_id, oppure
        #        snapshot una-tantum). Uno-per-tipo: sostituisce lo slot.
        #        handle_post_json = parsing/validazione body + envelope
        #        errori uniforme (helper obbligatorio per i POST, api.md).
        def post(self, request: Request, **kwargs: int) -> JsonResponse:
            documento_id = kwargs[url_kwarg]

            def _handler(payload: dict[str, Any]) -> dict[str, Any]:
                return upsert_call(documento_id, payload)

            return handle_post_json(request, handler=_handler)

    class _IndirizzoDetailView(DomainAPIView):
        area_funzionale = "vendite"

        @extend_schema(
            responses={200: inline_serializer(
                name=f"{schema_prefix}IndirizzoDeleteResponse",
                fields={"data": serializers.DictField()},
            )},
        )
        # Scopo: DELETE slot indirizzo (hard delete, guard obbligatorieta'
        #        demandato al DB all'emissione).
        def delete(self, request: Request, **kwargs: int) -> JsonResponse:
            return success_response(
                delete_call(kwargs[url_kwarg], kwargs["indirizzo_id"]))

    _IndirizziView.__doc__ = (
        f"GET/POST /api/v1/vendite/.../indirizzi/ — pannello indirizzi "
        f"{schema_prefix}: slot per tipo ammesso (config.tipi_indirizzi_allowed), "
        f"snapshot congelato + origine soft. POST: picker (origine_indirizzo_id, "
        f"snapshot server-side via fn_snapshot_indirizzo) o una-tantum (snapshot). "
        f"Area vendite."
    )
    _IndirizziView.__name__ = f"Api{schema_prefix}Indirizzi"
    _IndirizziView.__qualname__ = _IndirizziView.__name__
    _IndirizzoDetailView.__doc__ = (
        f"DELETE /api/v1/vendite/.../indirizzi/<id>/ — rimozione slot "
        f"indirizzo {schema_prefix}. Area vendite."
    )
    _IndirizzoDetailView.__name__ = f"Api{schema_prefix}IndirizzoDetail"
    _IndirizzoDetailView.__qualname__ = _IndirizzoDetailView.__name__

    if model_permission is not None:
        _IndirizziView.model_permission = model_permission
        _IndirizzoDetailView.model_permission = model_permission

    return SimpleNamespace(lista=_IndirizziView, detail=_IndirizzoDetailView)
