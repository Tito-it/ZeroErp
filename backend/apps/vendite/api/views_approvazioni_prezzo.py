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

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import qp_int
from apps.core.api.success_responses import success_response
from apps.vendite.services import approvazioni_prezzo_service


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
    Richiede azione processo `approva_prezzo` (oppure superuser bypass).
    """

    area_funzionale = "vendite"
    post_permission = "approva_prezzo"

    @extend_schema(
        request=_APPROVA_REQUEST,
        responses={200: _APPROVAZIONE_RESULT},
        tags=["vendite"],
        summary="Approva richiesta override prezzo (L3)",
    )
    def post(self, request: Request, riga_id: int):
        auth_user_id = request.user.id if request.user.is_authenticated else None

        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return approvazioni_prezzo_service.approva(
                riga_id=riga_id,
                auth_user_id=auth_user_id,
                nota=payload.get("nota") if isinstance(payload.get("nota"), str) else None,
            )

        return handle_post_json(request, handler=_handler)


class RifiutaPrezzoView(DomainAPIView):
    """POST /api/v1/vendite/righe/<riga_id>/rifiuta-prezzo/

    Rifiuta l'override prezzo. Richiede azione `approva_prezzo`.
    Motivazione opzionale registrata in nota interna pratica.
    """

    area_funzionale = "vendite"
    post_permission = "approva_prezzo"

    @extend_schema(
        request=_RIFIUTA_REQUEST,
        responses={200: _APPROVAZIONE_RESULT},
        tags=["vendite"],
        summary="Rifiuta richiesta override prezzo (L3)",
    )
    def post(self, request: Request, riga_id: int):
        auth_user_id = request.user.id if request.user.is_authenticated else None

        def _handler(payload: dict[str, object]) -> dict[str, object]:
            motivazione = payload.get("motivazione")
            return approvazioni_prezzo_service.rifiuta(
                riga_id=riga_id,
                auth_user_id=auth_user_id,
                motivazione=motivazione if isinstance(motivazione, str) else None,
            )

        return handle_post_json(request, handler=_handler)


class ApprovazioniPrezzoCodaView(DomainAPIView):
    """GET /api/v1/vendite/approvazioni-prezzo/

    Lista paginata della coda approver: pratiche tipo APPROVAZIONE_PREZZO
    in stato APERTA filtrate per scope emittente dell'utente.
    Area funzionale `vendite` LETTURA. La visibilita' richiede comunque
    `approva_prezzo` per agire (i POST individuali la verificano).
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        responses={200: _CODA_RESPONSE},
        tags=["vendite"],
        summary="Coda approvazioni prezzo (workflow L3)",
    )
    def get(self, request: Request):
        auth_user_id = request.user.id if request.user.is_authenticated else None
        # Clamp esplicito su DEFAULT_LIMIT/MAX_LIMIT centralizzati (apps/core/api/constants).
        limit = max(1, min(MAX_LIMIT, qp_int(request.query_params.get("limit"), default=DEFAULT_LIMIT)))
        offset = max(0, qp_int(request.query_params.get("offset"), default=0))
        data = approvazioni_prezzo_service.lista_coda(
            auth_user_id=auth_user_id,
            limit=limit,
            offset=offset,
        )
        return success_response(data)
