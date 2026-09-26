# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint POST /api/v1/auth/change-password/ — cambio password
#        con validazione (vecchia password + 4 validators Django).
#        Resetta flag deve_cambiare_password, blacklista token precedenti,
#        riapre la sessione nella stessa veste (catena del login).
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.jwt_audit_authentication import E_IDENTITA_NON_ATTIVA
from apps.core.api.multi_veste_token_serializer import emetti_refresh_veste
from apps.core.db.auth_repository import AuthRepository
from apps.core.services import session_audit_service
from apps.core.services.auth_constants import JWT_CLAIM_SID
from apps.core.services.auth_helpers import (
    apply_new_password,
    extract_identita_id_from_request,
)
from apps.core.services.error_manager import ErrorManager

logger = logging.getLogger("security")

E_CHANGE_PW = "E_CHANGE_PASSWORD"
_auth_repo = AuthRepository()


# Il corpo che il gestore legge: tutte e tre obbligatorie.
_CHANGE_PASSWORD_REQUEST = inline_serializer(
    name="CoreChangePasswordReq",
    fields={
        "old_password": serializers.CharField(),
        "new_password": serializers.CharField(),
        "new_password_confirm": serializers.CharField(),
    },
)

class ChangePasswordView(DomainAPIView):
    """Cambio password: valida vecchia, applica nuova, resetta flag, rigenera token."""

    skip_area_check = True

    @extend_schema(request=_CHANGE_PASSWORD_REQUEST, summary="Cambio password", responses={200: dict})
    # Scopo: Cambio password con validazione completa. Obiettivo: permettere
    #        all'operatore di cambiare la propria password (sia volontario
    #        che obbligatorio al primo accesso). Resetta flag, invalida
    #        sessioni precedenti, ritorna nuovi token JWT in envelope standard.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            user = request.user

            old_password = (payload.get("old_password") or "").strip()
            new_password = (payload.get("new_password") or "").strip()
            new_password_confirm = (payload.get("new_password_confirm") or "").strip()

            # Validazioni input
            ErrorManager.require(bool(old_password), code=E_CHANGE_PW, message="Password attuale obbligatoria.")
            ErrorManager.require(bool(new_password), code=E_CHANGE_PW, message="Nuova password obbligatoria.")
            ErrorManager.require(
                new_password == new_password_confirm,
                code=E_CHANGE_PW, message="La nuova password e la conferma non coincidono.",
            )
            ErrorManager.require(
                new_password != old_password,
                code=E_CHANGE_PW, message="La nuova password deve essere diversa dalla precedente.",
            )

            # Verifica password attuale
            ErrorManager.require(
                user.check_password(old_password),
                code=E_CHANGE_PW, message="Password attuale non corretta.",
            )

            # Validazione Django (4 validators: lunghezza, complessita', ecc.)
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as exc:
                ErrorManager.require(False, code=E_CHANGE_PW, message=" ".join(exc.messages))

            # La veste della sessione corrente: e' su QUELLA che si resetta il
            # flag deve_cambiare_password (§8.3.2+§8.4.1) ed e' in QUELLA che
            # si riapre la sessione. L'autenticazione ha gia' preteso il claim
            # e l'identita' attiva; la si rilegge qui per il ruolo, e PRIMA di
            # toccare la password: se nel frattempo e' stata revocata, il
            # cambio non avviene e la risposta e' quella di una sessione
            # scaduta, non un token che la richiesta dopo rifiuterebbe.
            identita_id = extract_identita_id_from_request(request)
            identita = (
                _auth_repo.get_identita_dettaglio(identita_id, user.id)
                if identita_id is not None
                else None
            )
            ErrorManager.require(
                identita is not None and bool(identita.get("attivo")),
                code=E_IDENTITA_NON_ATTIVA,
                message="Sessione non piu' valida: effettua nuovamente l'accesso.",
            )
            assert identita is not None

            # Operazioni atomiche: password + flag + blacklist
            apply_new_password(
                user,
                new_password,
                blacklist_tokens=True,
                auth_repo=_auth_repo,
            )

            # Sessione nuova nella stessa veste, con la catena del login
            # (sid nuovo, identita_id, ruolo_applicativo, emittente attivo):
            # le sessioni precedenti sono appena state chiuse dalla blacklist.
            # ⛔ Fino al 2026-09-24 era `RefreshToken.for_user(user)`: un token
            # senza veste, che la richiesta dopo rifiutava con 401
            # E_JWT_SENZA_IDENTITA — proprio nel cambio obbligatorio al primo
            # accesso (M-2 dell'analisi difetti).
            refresh = emetti_refresh_veste(user, identita)

            # Audit: la sessione nuova si identifica col suo `sid`, come al
            # login (prima si registrava il `jti`, che cambia a ogni refresh).
            session_audit_service.record_login(
                user_id=user.id,
                request=request._request if hasattr(request, "_request") else request,
                jti=str(refresh[JWT_CLAIM_SID]),
            )
            logger.info("security.password_changed user_id=%s", user.id)

            return {"access": str(refresh.access_token), "refresh": str(refresh)}

        return handle_post_json(request, handler=_handler)
