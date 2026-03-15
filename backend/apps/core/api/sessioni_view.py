# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint sessioni attive utente:
#        GET  /api/v1/core/me/sessioni/           — lista altre sessioni attive
#        POST /api/v1/core/me/sessioni/<jti>/revoca/ — revoca sessione specifica
# ------------------------------------------------------------

from __future__ import annotations

import jwt
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from apps.core.api.base_views import DomainAPIView
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from apps.core.api.success_responses import success_response
from apps.core.db.session_audit_repository import SessionAuditRepository
from apps.core.services import session_audit_service
from apps.core.services.service_errors import ServiceError


# Scopo: Estrae il SID (session ID) dal token JWT di accesso nella request corrente.
def _get_current_sid(request: Request) -> str | None:
    auth = request.auth
    return str(auth.get("sid", "")) if auth else None


class SessioniAttiveListView(DomainAPIView):
    """Lista sessioni attive dell'utente corrente, escludendo quella corrente."""

    skip_area_check = True

    @extend_schema(
        summary="Lista altre sessioni attive utente",
        responses={
            200: inline_serializer(
                name="SessioniAttiveResponse",
                fields={
                    "data": inline_serializer(
                        name="SessioniAttiveData",
                        fields={
                            "sessioni": serializers.ListField(
                                help_text="Lista sessioni attive (esclusa la corrente)."
                            ),
                            "count": serializers.IntegerField(
                                help_text="Numero sessioni restituite."
                            ),
                        },
                    ),
                },
            )
        },
    )
    # Scopo: Lista le sessioni attive dell'utente corrente, escludendo quella corrente.
    # Il frontend mostra il pannello solo se la lista non e' vuota.
    def get(self, request: Request) -> Response:
        repo = SessionAuditRepository()
        sessioni = repo.list_sessioni_attive(request.user.id)
        current_sid = _get_current_sid(request)
        altre = [s for s in sessioni if s["jti"] != current_sid]
        return success_response({"sessioni": altre, "count": len(altre)})


class SessioneRevocaView(DomainAPIView):
    """Revoca una sessione specifica (non la corrente) — blacklist + evento REVOCA."""

    skip_area_check = True

    @extend_schema(summary="Revoca sessione specifica", responses={204: None})
    # Scopo: Revoca una sessione per sid — blacklista tutti i token JWT associati.
    def post(self, request: Request, jti: str) -> Response:
        sid = jti  # il parametro URL si chiama jti ma ora contiene un sid
        current_sid = _get_current_sid(request)
        if current_sid and sid == current_sid:
            raise ServiceError(
                code="E_SESSIONE_REVOCA_CORRENTE",
                message="Non puoi revocare la sessione corrente. Usa il logout.",
            )
        # Cerca OutstandingToken dell'utente con claim sid corrispondente.
        found = False
        for ot in OutstandingToken.objects.filter(user_id=request.user.id):
            try:
                payload = jwt.decode(
                    ot.token, options={"verify_exp": False, "verify_signature": False}
                )
                if payload.get("sid") == sid:
                    BlacklistedToken.objects.get_or_create(token=ot)
                    found = True
            except Exception:
                continue
        if not found:
            raise ServiceError(
                code="E_SESSIONE_NOT_FOUND",
                message="Sessione non trovata o gia' revocata.",
            )
        session_audit_service.record_revoca(
            user_id=request.user.id,
            request=request._request,
            jti=sid,
        )
        return Response(status=204)
