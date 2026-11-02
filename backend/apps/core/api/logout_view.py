# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint POST /api/v1/auth/logout/ — revoca la sessione del refresh
#        presentato e registra evento LOGOUT in dbops.sessioni_utente.
# ------------------------------------------------------------

from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from apps.core.api.base_views import DomainAPIView
from apps.core.api.cancello_obblighi import TUTTI_GLI_OBBLIGHI
from apps.core.api.refresh_cookie import (
    cancella_refresh_cookie,
    claims_refresh_firmati,
    leggi_refresh_cookie,
)
from rest_framework_simplejwt.settings import api_settings

from apps.core.services import session_audit_service
from apps.core.services.auth_constants import JWT_CLAIM_SID
from apps.core.services.request_context import richiesta_django
from apps.core.services.revoca_token import blocca_token_sessioni
from apps.core.services.service_errors import ServiceError
from apps.core.api.endpoint_helpers import utente_autenticato_id

logger = logging.getLogger("security")


class LogoutView(DomainAPIView):
    """Logout utente: revoca della sessione del refresh + evento LOGOUT."""

    skip_area_check = True
    # Si deve poter uscire anche con un obbligo pendente (cancello_obblighi).
    obblighi_ammessi = TUTTI_GLI_OBBLIGHI

    @extend_schema(request=None, summary="Logout utente", responses={204: None})
    # Scopo: Revoca la sessione del refresh presentato e registra l'evento LOGOUT.
    # ⭐ Si revoca la SESSIONE (tutti i token col suo `sid`, via il BB
    #    `blocca_token_sessioni`), non il solo token presentato (2026-09-26).
    #    Col solo token, un refresh gia' ruotato da una richiesta in volo era
    #    gia' in blacklist, il logout rispondeva 204 e il SUCCESSORE — stesso
    #    `sid` — restava valido fino a un giorno.
    # ⛔ Il token deve essere dell'utente autenticato (stessa guardia di
    #    `emittente_attivo_views`): l'access token dice chi sei, il refresh nel
    #    cookie e' un dato in ingresso.
    # ⭐ Il refresh arriva dal cookie HttpOnly (brief sicurezza §2, 2026-09-28),
    #    e il cookie si CANCELLA in ogni risposta, anche quando non c'e' niente
    #    da revocare: dopo un logout il browser non deve piu' portarlo.
    # ⚠️ Il 204 resta anche quando non c'e' niente da revocare (token non
    #    nostro, altrui, illeggibile): il logout lato client procede comunque,
    #    e il caso anomalo si scrive nel log `security`.
    def post(self, request: Request) -> Response:
        response = self._chiudi(request)
        cancella_refresh_cookie(response)
        return response

    # Scopo: Il logout vero e proprio; `post` ci aggiunge la cancellazione del
    #        cookie, cosi' vale per ogni uscita senza ripeterla a ogni return.
    def _chiudi(self, request: Request) -> Response:
        refresh_token = leggi_refresh_cookie(request)
        if refresh_token is None:
            raise ServiceError(
                code="E_LOGOUT_NO_TOKEN",
                message="Refresh token richiesto per il logout.",
                detail="Nessun cookie di refresh nella richiesta.",
            )

        claims = claims_refresh_firmati(refresh_token)
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

        user_id = utente_autenticato_id(request)
        blocca_token_sessioni(user_id, lambda s: s == sid)
        session_audit_service.record_logout(
            user_id=user_id,
            request=richiesta_django(request),
            jti=sid,
        )
        return Response(status=204)
