# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint pubblici per reset password dimenticata:
#        1. POST /password-reset-request/ — richiesta reset (invia email)
#        2. GET  /password-reset-validate/{token}/ — verifica token
#        3. POST /password-reset-confirm/ — conferma con nuova password
#        Tutti non autenticati (AllowAny), con rate limiting.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import PasswordResetRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.email_service import EmailDispatchService
from apps.core.services.error_manager import ErrorManager
from apps.core.services.request_context import get_client_ip
from apps.core.services.token_service import TokenService

logger = logging.getLogger("security")

E_RESET = "E_RESET_PASSWORD"
_RESET_TOKEN_TIPO = "RESET_PASSWORD"
_RESET_SCADENZA_ORE = 1
_TEMPLATE_RESET = "RESET_PASSWORD"
_TEMPLATE_CONFERMA = "CAMBIO_PASSWORD_CONFERMA"

_auth_repo = AuthRepository()
_token_service = TokenService()
_email_service = EmailDispatchService()


class PasswordResetRequestView(APIView):
    """POST: richiesta reset password — invia email con link.
    Sempre 200, anche se email non esiste (sicurezza: non rivelare email registrate)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(summary="Richiesta reset password", responses={200: dict})
    # Scopo: Riceve email, genera token, invia email con link reset.
    #        Risponde sempre 200 per non rivelare se l'email esiste.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            email = (payload.get("email") or "").strip().lower()
            if not email:
                # Risposta generica anche senza email
                return {"message": "Se l'email e' registrata, riceverai un link per reimpostare la password."}

            # Cerca utente con questa email (best-effort)
            user = User.objects.filter(email=email, is_active=True).first()
            if user:
                # Genera token reset
                token_plain = _token_service.create(
                    tipo=_RESET_TOKEN_TIPO,
                    auth_user_id=user.id,
                    scadenza_ore=_RESET_SCADENZA_ORE,
                    meta={"richiesto_da": "self-service"},
                )

                # Risolvi reparto dell'operatore per account email mittente
                uo_id = _auth_repo.get_unita_organizzativa_id(user.id)

                # Costruisci link frontend
                from django.conf import settings
                frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
                link = f"{frontend_url}/reset-password/{token_plain}"

                # Invia email (console mode in DEBUG)
                try:
                    _email_service.send_email(
                        codice_template=_TEMPLATE_RESET,
                        destinatario=email,
                        variabili={
                            "nome": user.first_name or user.username,
                            "azienda": "ZeroErp",
                            "link": link,
                            "scadenza_ore": str(_RESET_SCADENZA_ORE),
                        },
                        unita_organizzativa_id=uo_id,
                        ambito="SISTEMA",
                        auth_user_id=user.id,
                    )
                except Exception:
                    logger.exception("Errore invio email reset per user_id=%s", user.id)

                logger.info("security.password_reset_requested user_id=%s email=%s", user.id, email)

            # Risposta identica sia che l'utente esista o no
            return {"message": "Se l'email e' registrata, riceverai un link per reimpostare la password."}

        return handle_post_json(request, handler=_handler)


class PasswordResetValidateView(APIView):
    """GET: verifica se un token reset e' ancora valido (senza consumarlo)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(summary="Verifica token reset password", responses={200: dict})
    # Scopo: Verifica validita' token senza consumarlo. Usato dal frontend
    #        per mostrare il form o un messaggio di errore/scadenza.
    def get(self, request: Request, token: str) -> JsonResponse:
        result = _token_service.validate(token, _RESET_TOKEN_TIPO)
        if result:
            return success_response({"valid": True})
        return success_response({"valid": False, "message": "Token non valido, scaduto o gia' utilizzato."})


class PasswordResetConfirmView(APIView):
    """POST: conferma reset con nuova password (consuma token)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(summary="Conferma reset password", responses={200: dict})
    # Scopo: Consuma token, imposta nuova password, blacklista token JWT,
    #        invia email di conferma, ritorna messaggio (senza nuovi token).
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            token = (payload.get("token") or "").strip()
            new_password = (payload.get("new_password") or "").strip()
            new_password_confirm = (payload.get("new_password_confirm") or "").strip()

            ErrorManager.require(bool(token), code=E_RESET, message="Token obbligatorio.")
            ErrorManager.require(bool(new_password), code=E_RESET, message="Nuova password obbligatoria.")
            ErrorManager.require(
                new_password == new_password_confirm,
                code=E_RESET, message="La nuova password e la conferma non coincidono.",
            )

            # Consuma token (lancia ServiceError se invalido)
            ip = get_client_ip(request._request)
            auth_user_id = _token_service.consume(token, _RESET_TOKEN_TIPO, ip=ip)

            # Trova utente
            user = User.objects.filter(id=auth_user_id).first()
            ErrorManager.require(user is not None, code=E_RESET, message="Utente non trovato.")
            assert user is not None

            # Valida nuova password (4 validators Django)
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as exc:
                ErrorManager.require(False, code=E_RESET, message=" ".join(exc.messages))

            # Applica nuova password + reset flag (atomico)
            with transaction.atomic():
                user.set_password(new_password)
                user.save(update_fields=["password"])
                _auth_repo.set_deve_cambiare_password(auth_user_id, False)

                # Blacklista refresh token precedenti
                for ot in OutstandingToken.objects.filter(user=user):
                    try:
                        RefreshToken(ot.token).blacklist()
                    except TokenError:
                        pass

            # Invia email conferma
            uo_id = _auth_repo.get_unita_organizzativa_id(auth_user_id)
            try:
                from datetime import datetime, timezone
                _email_service.send_email(
                    codice_template=_TEMPLATE_CONFERMA,
                    destinatario=user.email,
                    variabili={
                        "nome": user.first_name or user.username,
                        "azienda": "ZeroErp",
                        "data_cambio": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"),
                    },
                    unita_organizzativa_id=uo_id,
                    ambito="SISTEMA",
                    auth_user_id=auth_user_id,
                )
            except Exception:
                logger.exception("Errore invio email conferma reset per user_id=%s", auth_user_id)

            logger.info("security.password_reset_confirmed user_id=%s", auth_user_id)
            return {"message": "Password reimpostata con successo. Effettua il login con la nuova password."}

        return handle_post_json(request, handler=_handler)

