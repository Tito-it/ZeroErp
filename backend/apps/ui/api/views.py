# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#          - POST   /liste/<codice>/preferenza/ignore-preset-update
#                                                 -> tombstone DEF-2 "preset aggiornato"
#          - GET    /misure-pagina                -> fn_get_misure_pagina
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.services import perimetro_emittente
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name=perimetro_emittente.PARAM_EMITTENTE_ESPLICITO,
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Emittente gia' fissato dal contesto che apre la lista (un "
                    "tab dentro il drawer di un emittente). Se c'e', la lista "
                    "non e' ambigua e `richiede_scelta_emittente` resta falsa "
                    "anche su una lista non certificata multi-emittente."
                ),
            ),
        ],
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: Restituisce la configurazione effettiva della lista per l'utente.
    # ⭐ L'emittente esplicito viaggia insieme al codice: il pannello di
    #    perimetro lo calcola il backend (`richiede_scelta_emittente`), e senza
    #    questo parametro direbbe «scegli un emittente» proprio dentro il
    #    drawer dell'emittente che l'operatore ha gia' aperto.
    def get(self, request: Request, codice: str) -> JsonResponse:
        config = UiService().get_lista_config_per_video(
            request.user,
            codice,
            emittente_esplicito=perimetro_emittente.emittente_esplicito_da_query(
                request.query_params,
                nome=perimetro_emittente.PARAM_EMITTENTE_ESPLICITO,
            ),
        )
        return success_response(config)


class ApiMisurePaginaView(DomainAPIView):
    """
    GET /api/v1/ui/misure-pagina/

    Le misure «righe per pagina» che ogni paginatore offre e i due default
    (`default_compatta` per drawer e dialog, `default_pagina` per le pagine),
    dal catalogo `ui.misure_pagina`. Servite a TUTTA l'applicazione, non
    dentro la configurazione di una lista: le usano anche tabelle grezze,
    dialog e cruscotti. Il frontend le legge una volta per sessione.
    """

    skip_area_check = True

    @extend_schema(
        responses={
            200: inline_serializer(
                name="UiMisurePaginaResponse",
                fields={
                    "data": inline_serializer(
                        name="UiMisurePagina",
                        fields={
                            "misure": serializers.ListField(
                                child=serializers.IntegerField(),
                            ),
                            "default_compatta": serializers.IntegerField(),
                            "default_pagina": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            ),
        },
    )
    # Scopo: Restituisce misure ammesse e default dal catalogo DB.
    def get(self, request: Request) -> JsonResponse:
        return success_response(UiService().get_misure_pagina())


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
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
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


class ApiListaIgnorePresetUpdateView(DomainAPIView):
    """
    POST /api/v1/ui/liste/<codice>/preferenza/ignore-preset-update

    Tombstone "Ignora banner preset aggiornato" (DEF-2): setta
    `preset_aggiornato_ignored_at = NOW()` sulla preferenza utente per
    (request.user, lista_codice). Il flag `preset_aggiornato` di
    `fn_resolve_lista_config` torna FALSE finche' il preset non viene
    modificato di nuovo.

    Body vuoto ammesso. `handle_post_json` + `require_idempotency_key=True`
    per allineamento al pattern POST di api.md (envelope uniforme, strong
    idempotency replay su `dbops.idempotency_keys`).
    """

    skip_area_check = True

    @extend_schema(
        request=None,
        responses={200: _DATA_RESPONSE},
    )
    # Scopo: Setta il tombstone "ignore" del banner DEF-2 per (user, lista).
    def post(self, request: Request, codice: str) -> JsonResponse:
        def _handler(_payload: dict[str, Any]) -> dict[str, Any]:
            return ListaPreferenzaService().ignore_preset_update(
                request.user, codice,
            )

        return handle_post_json(
            request,
            handler=_handler,
            require_idempotency_key=True,
        )
