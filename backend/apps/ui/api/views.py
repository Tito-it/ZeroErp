# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view per personalizzazioni liste (`/api/v1/ui/*`).
#        Meta-API trasversale: tutte le view usano DomainAPIView con
#        `skip_area_check=True` (schema `ui` non e' in
#        config.aree_funzionali e non lo deve essere — la presentazione
#        e' ortogonale alle aree funzionali di business).
#
#        Endpoint:
#          - GET    /liste/<codice>/config        -> fn_resolve_lista_config
#          - GET    /liste/<codice>/catalogo      -> catalogo colonne (modale)
#          - PUT    /liste/<codice>/preferenza    -> upsert preferenza utente
#          - DELETE /liste/<codice>/preferenza    -> elimina preferenza utente
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.ui.services.lista_preferenza_service import ListaPreferenzaService
from apps.ui.services.ui_service import UiService


# Serializer inline riusato — la response dei 4 endpoint e' sempre
# l'envelope standard `{"data": ..., "meta": ...}`.
_DATA_RESPONSE = inline_serializer(
    name="UiDataResponse",
    fields={
        "data": serializers.JSONField(),
        "meta": serializers.DictField(required=False),
    },
)


class ApiListaConfigView(DomainAPIView):
    """
    GET /api/v1/ui/liste/<codice>/config

    Risolve la configurazione effettiva della lista per l'utente
    autenticato applicando la cascata preset + permessi (fn DB).
    `emittente_fiscale_id` derivato 1:1 dall'utente lato service.
    """

    # Meta-API trasversale: schema `ui` NON e' un'area funzionale.
    # JWT obbligatorio (default DomainAPIView), nessun check area.
    skip_area_check = True

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce la configurazione effettiva della lista per l'utente.
    def get(self, request: Request, codice: str) -> JsonResponse:
        config = UiService().get_lista_config(request.user, codice)
        return success_response(config)


class ApiListaCatalogoView(DomainAPIView):
    """
    GET /api/v1/ui/liste/<codice>/catalogo

    Catalogo delle colonne disponibili per la modale di personalizzazione.
    Filtra le colonne BLOCCATE per il profilo dell'utente: anche la
    modale non deve mostrare cio' che e' proibito.
    """

    skip_area_check = True

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Restituisce il catalogo colonne filtrato per i permessi utente.
    def get(self, request: Request, codice: str) -> JsonResponse:
        catalogo = UiService().get_catalogo(request.user, codice)
        return success_response(catalogo)


class ApiListaPreferenzaView(DomainAPIView):
    """
    PUT    /api/v1/ui/liste/<codice>/preferenza  -> upsert
    DELETE /api/v1/ui/liste/<codice>/preferenza  -> elimina
    """

    skip_area_check = True

    @extend_schema(
        request=inline_serializer(
            name="UiListaPreferenzaUpsertRequest",
            fields={
                "colonne": serializers.ListField(
                    child=serializers.DictField(),
                    required=False,
                ),
                "ordinamento": serializers.ListField(
                    child=serializers.DictField(),
                    required=False,
                ),
                "filtri": serializers.DictField(required=False),
                "pagina_dimensione": serializers.IntegerField(required=False),
            },
        ),
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: UPSERT preferenza utente. Idempotency-Key obbligatoria
    #        per rispettare il pattern api.md su modifiche di stato
    #        ripetibili da retry FE.
    def put(self, request: Request, codice: str) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return ListaPreferenzaService().upsert(
                request.user, codice, dict(payload),
            )

        return handle_post_json(
            request,
            handler=_handler,
            require_idempotency_key=True,
        )

    @extend_schema(responses={200: _DATA_RESPONSE})
    # Scopo: Elimina preferenza utente. Idempotente: 200 anche se
    #        non esisteva (ritorna `deleted: false`).
    def delete(self, request: Request, codice: str) -> JsonResponse:
        result = ListaPreferenzaService().delete(request.user, codice)
        return success_response(result)
