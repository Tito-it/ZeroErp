# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint API workflow L3 approvazione prezzo out-of-policy
#        (sviluppo-listini-v5 §14.6 Sprint E).
#
#        Tre endpoint:
#        - POST /vendite/righe/<riga_id>/approva-prezzo/
#        - POST /vendite/righe/<riga_id>/rifiuta-prezzo/
#        - GET  /vendite/approvazioni-prezzo/   (coda approver)
# ------------------------------------------------------------

"""Approvazioni prezzo L3 — view REST."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.api.endpoint_helpers import get_actor_user_id, handle_post_json
from apps.core.api.payload_validators import qp_int, qp_str
from apps.core.api.success_responses import success_response
from apps.core.db._helpers import limiti_pagina
from apps.vendite.services import approvazioni_prezzo_service
from apps.vendite.services._approvazioni_prezzo_constants import (
    META_SORGENTE_CONTRATTO,
    META_SORGENTE_OFFERTA,
)


_APPROVA_REQUEST = inline_serializer(
    name="VenditeApprovaPrezzoReq",
    fields={
        "nota": serializers.CharField(required=False, allow_blank=True, allow_null=True),
    },
)

_RIFIUTA_REQUEST = inline_serializer(
    name="VenditeRifiutaPrezzoReq",
    fields={
        "motivazione": serializers.CharField(required=False, allow_blank=True, allow_null=True),
    },
)

_APPROVAZIONE_RESULT = inline_serializer(
    name="VenditeApprovazionePrezzoResp",
    fields={
        "riga_id": serializers.IntegerField(),
        "pratica_id": serializers.IntegerField(),
        "stato": serializers.CharField(),
    },
)

_CODA_RESPONSE = inline_serializer(
    name="VenditeApprovazioniPrezzoCodaResp",
    fields={
        "results": serializers.ListField(child=serializers.JSONField()),
        "count": serializers.IntegerField(),
        "limit": serializers.IntegerField(),
        "offset": serializers.IntegerField(),
    },
)


class ApprovaPrezzoView(DomainAPIView):
    """POST /api/v1/vendite/righe/<riga_id>/approva-prezzo/

    Approva l'override prezzo su una riga preventivo PENDING.
    Richiede azione processo `approva_prezzo_override` (oppure superuser bypass).
    """

    area_funzionale = "vendite"
    post_permission = "approva_prezzo_override"

    @extend_schema(
        request=_APPROVA_REQUEST,
        responses={200: _APPROVAZIONE_RESULT},
        tags=["vendite"],
        summary="Approva richiesta override prezzo (L3)",
    )
    def post(self, request: Request, riga_id: int):
        auth_user_id = get_actor_user_id(request)

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return approvazioni_prezzo_service.approva(
                riga_id=riga_id,
                auth_user_id=auth_user_id,
                nota=payload.get("nota") if isinstance(payload.get("nota"), str) else None,
            )

        return handle_post_json(request, handler=_handler)


class RifiutaPrezzoView(DomainAPIView):
    """POST /api/v1/vendite/righe/<riga_id>/rifiuta-prezzo/

    Rifiuta l'override prezzo. Richiede azione `approva_prezzo_override`.
    Motivazione opzionale registrata in nota interna pratica.
    """

    area_funzionale = "vendite"
    post_permission = "approva_prezzo_override"

    @extend_schema(
        request=_RIFIUTA_REQUEST,
        responses={200: _APPROVAZIONE_RESULT},
        tags=["vendite"],
        summary="Rifiuta richiesta override prezzo (L3)",
    )
    def post(self, request: Request, riga_id: int):
        auth_user_id = get_actor_user_id(request)

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            motivazione = payload.get("motivazione")
            return approvazioni_prezzo_service.rifiuta(
                riga_id=riga_id,
                auth_user_id=auth_user_id,
                motivazione=motivazione if isinstance(motivazione, str) else None,
            )

        return handle_post_json(request, handler=_handler)


class ApprovaPrezzoContrattoView(DomainAPIView):
    """POST /api/v1/vendite/righe-contratto/<riga_id>/approva-prezzo/

    Approva l'override prezzo su una riga **contratto** PENDING (refactor
    2026-05-19 BE porting gate riga contratti). Speculare a
    `ApprovaPrezzoView` per i preventivi. Stesso permission `approva_prezzo_override`,
    stesso shape risposta. La sorgente=`contratto` viene passata al service
    che fa dispatch su `vendite.contratti_righe`.
    """

    area_funzionale = "vendite"
    post_permission = "approva_prezzo_override"

    @extend_schema(
        request=_APPROVA_REQUEST,
        responses={200: _APPROVAZIONE_RESULT},
        tags=["vendite"],
        summary="Approva richiesta override prezzo su riga contratto (L3)",
    )
    def post(self, request: Request, riga_id: int):
        auth_user_id = get_actor_user_id(request)

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return approvazioni_prezzo_service.approva(
                riga_id=riga_id,
                auth_user_id=auth_user_id,
                nota=payload.get("nota") if isinstance(payload.get("nota"), str) else None,
                sorgente=META_SORGENTE_CONTRATTO,
            )

        return handle_post_json(request, handler=_handler)


class RifiutaPrezzoContrattoView(DomainAPIView):
    """POST /api/v1/vendite/righe-contratto/<riga_id>/rifiuta-prezzo/

    Rifiuta l'override prezzo su una riga **contratto** PENDING. Speculare
    a `RifiutaPrezzoView` per i preventivi.
    """

    area_funzionale = "vendite"
    post_permission = "approva_prezzo_override"

    @extend_schema(
        request=_RIFIUTA_REQUEST,
        responses={200: _APPROVAZIONE_RESULT},
        tags=["vendite"],
        summary="Rifiuta richiesta override prezzo su riga contratto (L3)",
    )
    def post(self, request: Request, riga_id: int):
        auth_user_id = get_actor_user_id(request)

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            motivazione = payload.get("motivazione")
            return approvazioni_prezzo_service.rifiuta(
                riga_id=riga_id,
                auth_user_id=auth_user_id,
                motivazione=motivazione if isinstance(motivazione, str) else None,
                sorgente=META_SORGENTE_CONTRATTO,
            )

        return handle_post_json(request, handler=_handler)


class ApprovaPrezzoOffertaView(DomainAPIView):
    """POST /api/v1/vendite/eccezioni-offerta/<riga_id>/approva-prezzo/

    Approva l'override prezzo su una **eccezione offerta** PENDING (refactor
    2026-06-01 gate prezzi offerte). Speculare a `ApprovaPrezzoContrattoView`.
    `riga_id` e' l'id dell'eccezione; sorgente=`offerta` → dispatch su
    `vendite.offerte_commerciali_eccezioni`.
    """

    area_funzionale = "vendite"
    post_permission = "approva_prezzo_override"

    @extend_schema(
        request=_APPROVA_REQUEST,
        responses={200: _APPROVAZIONE_RESULT},
        tags=["vendite"],
        summary="Approva richiesta override prezzo su eccezione offerta (L3)",
    )
    def post(self, request: Request, riga_id: int):
        auth_user_id = get_actor_user_id(request)

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return approvazioni_prezzo_service.approva(
                riga_id=riga_id,
                auth_user_id=auth_user_id,
                nota=payload.get("nota") if isinstance(payload.get("nota"), str) else None,
                sorgente=META_SORGENTE_OFFERTA,
            )

        return handle_post_json(request, handler=_handler)


class RifiutaPrezzoOffertaView(DomainAPIView):
    """POST /api/v1/vendite/eccezioni-offerta/<riga_id>/rifiuta-prezzo/

    Rifiuta l'override prezzo su una **eccezione offerta** PENDING. Speculare
    a `RifiutaPrezzoContrattoView`.
    """

    area_funzionale = "vendite"
    post_permission = "approva_prezzo_override"

    @extend_schema(
        request=_RIFIUTA_REQUEST,
        responses={200: _APPROVAZIONE_RESULT},
        tags=["vendite"],
        summary="Rifiuta richiesta override prezzo su eccezione offerta (L3)",
    )
    def post(self, request: Request, riga_id: int):
        auth_user_id = get_actor_user_id(request)

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            motivazione = payload.get("motivazione")
            return approvazioni_prezzo_service.rifiuta(
                riga_id=riga_id,
                auth_user_id=auth_user_id,
                motivazione=motivazione if isinstance(motivazione, str) else None,
                sorgente=META_SORGENTE_OFFERTA,
            )

        return handle_post_json(request, handler=_handler)


class ApprovazioniPrezzoCodaView(DomainAPIView):
    """GET /api/v1/vendite/approvazioni-prezzo/

    Lista paginata della coda approver: pratiche tipo APPROVAZIONE_PREZZO
    in stato APERTA filtrate per scope emittente dell'utente.
    Area funzionale `vendite` LETTURA + azione processo
    `approva_prezzo_override`: la coda e' una pagina operativa per approver,
    non una lista consultiva generale.
    """

    area_funzionale = "vendite"
    get_permission = "approva_prezzo_override"
    is_search_endpoint = True
    lista_codice = "vendite.approvazioni_prezzo"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(
                name="order_by", type=str, required=False,
                description="Colonna di ordinamento (whitelist pratiche).",
            ),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: _CODA_RESPONSE},
        tags=["vendite"],
        summary="Coda approvazioni prezzo (workflow L3)",
    )
    def get(self, request: Request):
        auth_user_id = get_actor_user_id(request)
        # Clamp dal BB `limiti_pagina` (tetto `MAX_LIMIT` di core).
        limit, offset = limiti_pagina(
            qp_int(request.query_params.get("limit"), default=DEFAULT_LIMIT),
            qp_int(request.query_params.get("offset"), default=0),
        )
        # `order_by`/`order_dir` passano al service, che li valida contro la
        # whitelist delle pratiche. Prima del 2026-08-02 la view non li leggeva
        # e il service inchiodava `data_insert desc`: la lista non ordinava.
        data = approvazioni_prezzo_service.lista_coda(
            auth_user_id=auth_user_id,
            limit=limit,
            offset=offset,
            order_by=qp_str(request.query_params.get("order_by")),
            order_dir=qp_str(request.query_params.get("order_dir")),
        )
        return success_response(data)
