# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import password_digitata
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import ConfermaTokenRateThrottle, PasswordResetRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_constants import NOME_SISTEMA_EMAIL
from apps.core.services.auth_helpers import (
    apply_new_password,
    valida_nuova_password,
    validate_and_extract_token,
)
from apps.core.services.credenziale_ingresso import credenziale_per_email, credenziale_per_nome_utente
from apps.core.services.email_service import EmailDispatchService
from apps.core.services.error_manager import ErrorManager
from apps.core.services.invito_veste import nome_visualizzato
from apps.core.services.locale_formatters import format_datetime
from apps.core.services.request_context import get_client_ip, richiesta_django
from apps.core.services.token_service import TokenService

logger = logging.getLogger("security")

E_RESET = "E_RESET_PASSWORD"
_RESET_TOKEN_TIPO = "RESET_PASSWORD"  # noqa: S105 — codice del tipo token, non un segreto
_RESET_SCADENZA_ORE = 1
_TEMPLATE_RESET = "RESET_PASSWORD"
_TEMPLATE_CONFERMA = "CAMBIO_PASSWORD_CONFERMA"

_auth_repo = AuthRepository()
_token_service = TokenService()
_email_service = EmailDispatchService()


# I corpi che i due gestori leggono. La richiesta risponde sempre lo stesso
# messaggio (anche senza `identificativo`): nessun dato su chi esiste.
_RESET_REQUEST_REQUEST = inline_serializer(
    name="CorePasswordResetRequestReq",
    fields={"identificativo": serializers.CharField(help_text="Nome utente o email")},
)

_RESET_CONFIRM_REQUEST = inline_serializer(
    name="CorePasswordResetConfirmReq",
    fields={
        "token": serializers.CharField(),
        "new_password": serializers.CharField(),
        "new_password_confirm": serializers.CharField(),
    },
)


# Scopo: La credenziale di chi chiede il reset, dal nome utente O dall'email
# (L-4, D-9: chi entra dal portale o dallo shop conosce la sua email, non un
# nome utente). Con una «@» si cerca prima l'email (`credenziale_per_email`,
# la regola del login per email); se non trova niente, il nome utente esatto,
# perche' il modello non vieta una «@» in un nome utente. Vale per ogni
# credenziale: la prova e' il possesso dell'email a cui arriva il link, e
# restringere l'email ad alcune porte non proteggerebbe niente.
def _credenziale_del_reset(identificativo: str) -> User | None:
    if "@" in identificativo:
        user = credenziale_per_email(identificativo)
        if user is not None:
            return user
    return credenziale_per_nome_utente(identificativo)


class PasswordResetRequestView(APIView):
    """POST: richiesta reset password — invia email con link.
    Sempre 200, anche se email non esiste (sicurezza: non rivelare email registrate)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(request=_RESET_REQUEST_REQUEST, summary="Richiesta reset password", responses={200: dict})
    # Scopo: Riceve nome utente o email, cerca utente attivo con email configurata,
    #        genera token e invia email con link reset.
    #        Risponde sempre 200 per non rivelare se l'utente esiste.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            # Un valore che non e' testo (numero, lista) vale come assente: la
            # risposta resta la stessa, mai un 500 su un endpoint pubblico.
            grezzo = payload.get("identificativo")
            identificativo = grezzo.strip() if isinstance(grezzo, str) else ""
            _MSG = "Se l'utente esiste e ha un'email configurata, ricevera' un link per reimpostare la password."
            if not identificativo:
                return {"message": _MSG}

            user = _credenziale_del_reset(identificativo)
            if user and user.is_active and user.email:
                # Genera token reset: vale solo l'ultimo link chiesto, e i
                # precedenti si spengono nella stessa transazione del nuovo.
                with transaction.atomic():
                    _token_service.invalidate_all(_RESET_TOKEN_TIPO, user.id)
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
                frontend_url = settings.FRONTEND_URL
                link = f"{frontend_url}/reset-password/{token_plain}"

                # Invia email (console mode in DEBUG)
                try:
                    _email_service.send_email(
                        codice_template=_TEMPLATE_RESET,
                        destinatario=user.email,
                        variabili={
                            "nome": nome_visualizzato(user.id, _auth_repo),
                            "azienda": NOME_SISTEMA_EMAIL,
                            "link": link,
                            "scadenza_ore": str(_RESET_SCADENZA_ORE),
                        },
                        unita_organizzativa_id=uo_id,
                        ambito="SISTEMA",
                        auth_user_id=user.id,
                    )
                except Exception:
                    logger.exception("Errore invio email reset per user_id=%s", user.id)

                # La credenziale per id, mai il valore digitato: puo' essere
                # un'email, o una password finita nel campo sbagliato (B-11).
                logger.info("security.password_reset_requested user_id=%s", user.id)

            # Risposta identica sia che l'utente esista o no
            return {"message": _MSG}

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
    throttle_classes = [ConfermaTokenRateThrottle]

    @extend_schema(request=_RESET_CONFIRM_REQUEST, summary="Conferma reset password", responses={200: dict})
    # Scopo: Consuma token, imposta nuova password, blacklista token JWT,
    #        invia email di conferma, ritorna messaggio (senza nuovi token).
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            token = (payload.get("token") or "").strip()
            new_password = password_digitata(payload, "new_password")
            new_password_confirm = password_digitata(payload, "new_password_confirm")

            ErrorManager.require(bool(token), code=E_RESET, message="Token obbligatorio.")

            # Valida token SENZA consumarlo
            auth_user_id, _ = validate_and_extract_token(
                token, _RESET_TOKEN_TIPO, E_RESET, _token_service,
            )

            # Trova utente
            user = User.objects.filter(id=auth_user_id).first()
            ErrorManager.require(user is not None, code=E_RESET, message="Utente non trovato.")
            assert user is not None

            # Valida nuova password PRIMA di consumare il token
            valida_nuova_password(new_password, new_password_confirm, user=user, code=E_RESET)

            # Consuma token + applica password + spegne il cambio obbligatorio
            # + blacklist + azzera i tentativi falliti (atomico).
            # ⭐ D-2: chi dimostra di possedere l'email ha superato la prova
            # che il freno protegge — i tentativi si azzerano su TUTTE le
            # provenienze. ⛔ Il blocco dell'admin resta (D-B3): il reset
            # dimostra il possesso dell'email, non annulla una decisione.
            ip = get_client_ip(richiesta_django(request))
            with transaction.atomic():
                _token_service.consume(token, _RESET_TOKEN_TIPO, ip=ip)
                apply_new_password(
                    user,
                    new_password,
                    blacklist_tokens=True,
                    auth_repo=_auth_repo,
                )
                _auth_repo.azzera_tentativi_credenziale(user.id)

            # Invia email conferma
            uo_id = _auth_repo.get_unita_organizzativa_id(auth_user_id)
            try:
                _email_service.send_email(
                    codice_template=_TEMPLATE_CONFERMA,
                    destinatario=user.email,
                    variabili={
                        "nome": nome_visualizzato(user.id, _auth_repo),
                        "azienda": NOME_SISTEMA_EMAIL,
                        # Ora dell'AZIENDA, formato del BB: fino al 2026-10-09
                        # l'email scriveva l'ora UTC (B-6).
                        "data_cambio": format_datetime(timezone.now()),
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

