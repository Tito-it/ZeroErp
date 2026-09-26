# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint POST /api/v1/auth/logout/ — revoca la sessione del refresh
#        presentato e registra evento LOGOUT in dbops.sessioni_utente.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

import jwt
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from apps.core.api.base_views import DomainAPIView
from rest_framework_simplejwt.exceptions import TokenBackendError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.state import token_backend

from apps.core.services import session_audit_service
from apps.core.services.auth_constants import JWT_CLAIM_SID
from apps.core.services.revoca_token import blocca_token_sessioni
from apps.core.services.service_errors import ServiceError

logger = logging.getLogger("security")


# Il refresh della sessione da chiudere: senza, `E_LOGOUT_NO_TOKEN`.
_LOGOUT_REQUEST = inline_serializer(
    name="CoreLogoutReq",
    fields={"refresh": serializers.CharField()},
)

# Scopo: i claim del refresh presentato, con la FIRMA verificata e la
#        scadenza no. `None` se il token non e' nostro, e' malformato o non e'
#        un refresh.
# ⛔ La firma si verifica: il `sid` decide QUALE sessione si revoca, e da un
#    token decodificato alla cieca chiunque ne sceglierebbe uno a piacere.
# ⚠️ La scadenza no: il logout con un refresh scaduto deve chiudere lo stesso
#    la sessione — il suo successore, emesso da una rotazione, puo' essere vivo.
# ⚠️ Non `RefreshToken(...)`: rifiuta il token gia' in blacklist, che e'
#    proprio il caso da chiudere (il refresh ruotato da una richiesta in volo).
def _claims_refresh_firmati(refresh_token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            refresh_token,
            token_backend.get_verifying_key(refresh_token),
            algorithms=[token_backend.algorithm],
            audience=token_backend.audience,
            issuer=token_backend.issuer,
            options={
                "verify_aud": token_backend.audience is not None,
                "verify_exp": False,
            },
        )
    except (jwt.PyJWTError, TokenBackendError):
        return None
    if payload.get(api_settings.TOKEN_TYPE_CLAIM) != "refresh":
        return None
    return payload


class LogoutView(DomainAPIView):
    """Logout utente: revoca della sessione del refresh + evento LOGOUT."""

    skip_area_check = True

    @extend_schema(request=_LOGOUT_REQUEST, summary="Logout utente", responses={204: None})
    # Scopo: Revoca la sessione del refresh presentato e registra l'evento LOGOUT.
    # ⭐ Si revoca la SESSIONE (tutti i token col suo `sid`, via il BB
    #    `blocca_token_sessioni`), non il solo token presentato (2026-09-26).
    #    Col solo token, un refresh gia' ruotato da una richiesta in volo era
    #    gia' in blacklist, il logout rispondeva 204 e il SUCCESSORE — stesso
    #    `sid` — restava valido fino a un giorno.
    # ⛔ Il token deve essere dell'utente autenticato (stessa guardia di
    #    `emittente_attivo_views`): l'access token dice chi sei, il refresh nel
    #    body e' un dato in ingresso.
    # ⚠️ Il 204 resta anche quando non c'e' niente da revocare (token non
    #    nostro, altrui, illeggibile): il logout lato client procede comunque,
    #    e il caso anomalo si scrive nel log `security`.
    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh")
        if not refresh_token or not isinstance(refresh_token, str):
            raise ServiceError(
                code="E_LOGOUT_NO_TOKEN",
                message="Refresh token richiesto per il logout.",
            )

        claims = _claims_refresh_firmati(refresh_token)
        if claims is None:
            logger.warning("security.logout_token_non_valido user_id=%s", request.user.id)
            return Response(status=204)
        if str(claims.get(api_settings.USER_ID_CLAIM)) != str(request.user.id):
            logger.warning(
                "security.logout_token_altrui user_id=%s token_user_id=%s",
                request.user.id, claims.get(api_settings.USER_ID_CLAIM),
            )
            return Response(status=204)

        # ⚠️ Un refresh senza `sid` non ha una sessione da chiudere, e non ne
        #    apre nessuna: `JwtAuditAuthentication` rifiuta ogni access token
        #    senza `sid` (401 `E_JWT_SENZA_SID`), quindi cio' che un refresh
        #    cosi' emetterebbe non passa. Nessun ripiego sul token singolo.
        sid = str(claims.get(JWT_CLAIM_SID, "") or "")
        if not sid:
            logger.warning("security.logout_token_senza_sid user_id=%s", request.user.id)
            return Response(status=204)

        blocca_token_sessioni(request.user.id, lambda s: s == sid)
        session_audit_service.record_logout(
            user_id=request.user.id,
            request=request._request if hasattr(request, "_request") else request,
            jti=sid,
        )
        return Response(status=204)
