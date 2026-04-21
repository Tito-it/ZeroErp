# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint namespace `/api/v1/portale/*` — flussi auth portale
#        (attivazione invito) + futuri endpoint MVP (me, billing-account,
#        fatture, scadenze, ordini-ricevuti, pagamenti). Gli endpoint
#        pubblici (attivazione-validate + attivazione) non richiedono JWT
#        e usano AllowAny. Gli endpoint autenticati usano PortaleAPIView.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.api.base_views import PortaleAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.api.throttling import PasswordResetRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_helpers import (
    apply_new_password,
    extract_identita_id_from_token_meta,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.request_context import get_client_ip
from apps.core.services.token_service import TokenService
from apps.portale.db.portale_repository import PortaleRepository
from apps.portale.services.invito_portale_service import (
    ATTIVAZIONE_PORTALE_CROSS_TOKEN_TIPO,
    INVITO_PORTALE_TOKEN_TIPO,
    resolve_portale_token,
)
from apps.shop.api.views import shop_not_available_response

logger = logging.getLogger("security")

E_ATTIVAZIONE_PORTALE = "E_ATTIVAZIONE_PORTALE"

_auth_repo = AuthRepository()
_portale_repo = PortaleRepository()
_token_service = TokenService()


class AttivazionePortaleValidateView(APIView):
    """GET: verifica se un token attivazione portale e' ancora valido
    (no consume). Distingue INVITO vs CROSS per guidare la UX (§8.4.2)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Verifica token attivazione portale",
        responses={200: inline_serializer(
            name="AttivazionePortaleValidateResp",
            fields={
                "data": inline_serializer(
                    name="AttivazionePortaleValidateData",
                    fields={
                        "valid": serializers.BooleanField(),
                        "token_type": serializers.CharField(required=False),
                        "requires_password": serializers.BooleanField(required=False),
                        "message": serializers.CharField(required=False),
                    },
                ),
            },
        )},
    )
    # Scopo: Usato dal frontend per decidere quale UI mostrare:
    #        - token_type=INVITO_PORTALE → form scegli password (primo accesso)
    #        - token_type=ATTIVAZIONE_PORTALE_CROSS → conferma un-click
    #          (utente gia' ha password sulla veste operatore/altra veste)
    #        `requires_password` e' derivato (True solo per INVITO) —
    #        e' esposto perche' il FE lo usa come feature flag senza
    #        dover conoscere i nomi dei token type.
    def get(self, request: Request, token: str) -> JsonResponse:
        resolved = resolve_portale_token(token, _token_service)
        if resolved is None:
            return success_response({
                "valid": False,
                "message": "Token non valido, scaduto o gia' utilizzato.",
            })
        _, _, token_type = resolved
        return success_response({
            "valid": True,
            "token_type": token_type,
            "requires_password": token_type == INVITO_PORTALE_TOKEN_TIPO,
        })


class AttivazionePortaleView(APIView):
    """POST: attivazione portale. Gestisce entrambi i token type §8.4.2:
    - INVITO_PORTALE (email nuova): consume token + set password + reset
      flag; l'identita era gia' stata creata attiva dall'invito.
    - ATTIVAZIONE_PORTALE_CROSS (email esistente): consume token + riattiva
      identita; la password preesistente dell'utente resta valida,
      nessuna nuova password richiesta."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(
        summary="Attivazione portale cliente/fornitore (INVITO o CROSS)",
        request=inline_serializer(
            name="AttivazionePortaleReq",
            fields={
                "token": serializers.CharField(),
                # Opzionali: obbligatori solo per token_type=INVITO_PORTALE.
                # Il BE valida la coerenza.
                "new_password": serializers.CharField(required=False),
                "new_password_confirm": serializers.CharField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="AttivazionePortaleResp",
            fields={
                "data": inline_serializer(
                    name="AttivazionePortaleData",
                    fields={
                        "message": serializers.CharField(),
                        "token_type": serializers.CharField(),
                    },
                ),
            },
        )},
    )
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            token = (payload.get("token") or "").strip()
            ErrorManager.require(
                bool(token),
                code=E_ATTIVAZIONE_PORTALE,
                message="Token obbligatorio.",
            )

            # Risolve il token tentando entrambi i tipi. Fallback unico
            # "Token non valido" evita enumeration (attaccante non distingue
            # tipo scaduto vs tipo inesistente).
            resolved = resolve_portale_token(token, _token_service)
            ErrorManager.require(
                resolved is not None,
                code=E_ATTIVAZIONE_PORTALE,
                message="Token non valido, scaduto o gia' utilizzato.",
            )
            assert resolved is not None
            auth_user_id, meta, token_type = resolved

            user = User.objects.filter(id=auth_user_id).first()
            ErrorManager.require(
                user is not None,
                code=E_ATTIVAZIONE_PORTALE,
                message="Utente non trovato.",
            )
            assert user is not None

            # identita_id dal meta del token (iniettato in §8.4.1) — punta
            # la veste portale specifica, critico per modello 1:N.
            identita_id = extract_identita_id_from_token_meta(meta)
            ErrorManager.require(
                identita_id is not None,
                code=E_ATTIVAZIONE_PORTALE,
                message=(
                    "Token privo di riferimento identita. "
                    "Richiedere un nuovo invito dall'amministratore."
                ),
            )
            assert identita_id is not None

            ip = get_client_ip(
                request._request if hasattr(request, "_request") else request
            )

            if token_type == INVITO_PORTALE_TOKEN_TIPO:
                self._attiva_flow_invito(
                    token=token,
                    user=user,
                    identita_id=identita_id,
                    payload=payload,
                    ip=ip,
                )
                msg = (
                    "Account portale attivato con successo. "
                    "Effettua il login con la nuova password."
                )
            else:
                # ATTIVAZIONE_PORTALE_CROSS
                self._attiva_flow_cross(
                    token=token,
                    identita_id=identita_id,
                    ip=ip,
                )
                msg = (
                    "Accesso portale attivato. "
                    "Effettua il login con le tue credenziali esistenti."
                )

            logger.info(
                "security.portale_attivato user_id=%s identita_id=%s token_type=%s",
                auth_user_id, identita_id, token_type,
            )
            return {"message": msg, "token_type": token_type}

        return handle_post_json(request, handler=_handler)

    # Scopo: Flow INVITO — valida password, consume token, setta password
    # + reset flag in transazione atomica.
    def _attiva_flow_invito(
        self,
        *,
        token: str,
        user: User,
        identita_id: int,
        payload: dict[str, Any],
        ip: str | None,
    ) -> None:
        new_password = (payload.get("new_password") or "").strip()
        new_password_confirm = (payload.get("new_password_confirm") or "").strip()

        ErrorManager.require(
            bool(new_password),
            code=E_ATTIVAZIONE_PORTALE,
            message="Nuova password obbligatoria per questo token.",
        )
        ErrorManager.require(
            new_password == new_password_confirm,
            code=E_ATTIVAZIONE_PORTALE,
            message="La nuova password e la conferma non coincidono.",
        )

        # Valida policy PRIMA di consumare (evita bruciare token su policy fail).
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            ErrorManager.require(
                False,
                code=E_ATTIVAZIONE_PORTALE,
                message=" ".join(exc.messages),
            )

        with transaction.atomic():
            _token_service.consume(token, INVITO_PORTALE_TOKEN_TIPO, ip=ip)
            # blacklist_tokens=False: primo accesso, nessuna sessione attiva.
            apply_new_password(
                user,
                new_password,
                identita_id=identita_id,
                blacklist_tokens=False,
                auth_repo=_auth_repo,
            )

    # Scopo: Flow CROSS — l'utente ha gia' una password sulla veste
    # preesistente (operatore o altra veste portale). L'attivazione solo
    # consume il token e riattiva l'identita portale (creata `attivo=false`
    # dall'invito §8.4.1). NON tocca password ne' flag deve_cambiare.
    def _attiva_flow_cross(
        self,
        *,
        token: str,
        identita_id: int,
        ip: str | None,
    ) -> None:
        # Difesa: se il payload contiene new_password, lo ignoriamo
        # silenziosamente — non vogliamo sovrascrivere per errore la
        # password operativa dell'utente con quella digitata per sbaglio
        # in un form CROSS. Il FE, informato da `requires_password=False`,
        # non dovrebbe inviarla.
        with transaction.atomic():
            _token_service.consume(
                token, ATTIVAZIONE_PORTALE_CROSS_TOKEN_TIPO, ip=ip
            )
            updated = _portale_repo.riattiva_identita(identita_id)
            if not updated:
                # Rowcount=0 significa identita rimossa / ruolo cambiato
                # tra emissione invito e consume. Il token e' gia' marcato
                # utilizzato DENTRO questa transazione: sollevare ServiceError
                # fa rollback atomico (consume + UPDATE) lasciando il token
                # ancora consumabile da un futuro retry — oppure, piu'
                # realisticamente, l'admin ri-invitera' rigenerando token.
                logger.warning(
                    "security.cross_riattiva_fallita identita_id=%s — "
                    "riga non trovata, rollback consume token",
                    identita_id,
                )
                ErrorManager.require(
                    False,
                    code=E_ATTIVAZIONE_PORTALE,
                    message=(
                        "Identita portale non piu' disponibile. "
                        "Contattare l'amministratore per un nuovo invito."
                    ),
                )


class ProfileActivateShopView(PortaleAPIView):
    """POST /api/v1/portale/profile/activate-shop/ — §8.4.3 stub.

    Il portale user (cliente/fornitore) richiede di attivare anche la
    veste SHOP_CUSTOMER sullo stesso auth_user. Il flusso reale (creazione
    identita shop + email conferma) arriva con PR-C. Per ora risponde 501
    con codice dedicato: il FE mostra un banner "funzione in arrivo".
    """

    skip_area_check = True

    @extend_schema(
        summary="Attiva accesso shop per utente portale (stub PR-C)",
        responses={501: inline_serializer(
            name="ActivateShopStubResp",
            fields={
                "error": inline_serializer(
                    name="ActivateShopStubErr",
                    fields={
                        "code": serializers.CharField(),
                        "message": serializers.CharField(),
                    },
                ),
            },
        )},
    )
    def post(self, request: Request) -> JsonResponse:
        # Stub puro: nessun body da parsare, nessuna idempotency key
        # (il consumer e' idempotent per definizione — sempre 501).
        # Helper condiviso con gli stub shop per uniformita' codice errore.
        return shop_not_available_response(
            "Attivazione accesso shop non ancora disponibile. "
            "Sara' abilitata con PR-C."
        )
