# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint attivazione shop customer (B1 §13.7 admin-driven).
#        Pattern simmetrico a AttivazionePortale* (apps/portale/api/views.py)
#        ma con tipi token INVITO_SHOP / ATTIVAZIONE_SHOP_CROSS e codice
#        errore dedicato E_ATTIVAZIONE_SHOP.
#
#        Flow INVITO (email nuova): set password + attiva identita.
#        Flow CROSS (email esistente, gia' operatore o altra veste):
#        solo attiva identita, password preesistente invariata.
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
    ATTIVAZIONE_SHOP_CROSS_TOKEN_TIPO,
    INVITO_SHOP_TOKEN_TIPO,
    resolve_shop_token,
)

logger = logging.getLogger("security")

E_ATTIVAZIONE_SHOP = "E_ATTIVAZIONE_SHOP"

_auth_repo = AuthRepository()
# Scopo: riuso PortaleRepository per `riattiva_identita` — e' generico su
# identita_digitali, non portale-specifico. Il nome storico e' rimasto per
# retrocompat; il metodo lavora su qualsiasi veste.
_portale_repo = PortaleRepository()
_token_service = TokenService()


class AttivazioneShopValidateView(APIView):
    """GET: verifica se un token attivazione shop e' ancora valido
    (no consume). Distingue INVITO vs CROSS per guidare la UX."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Verifica token attivazione shop",
        responses={200: inline_serializer(
            name="AttivazioneShopValidateResp",
            fields={
                "data": inline_serializer(
                    name="AttivazioneShopValidateData",
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
    # Scopo: Il FE decide quale UI mostrare in base al token_type:
    #   - INVITO_SHOP           -> form scegli password (primo accesso)
    #   - ATTIVAZIONE_SHOP_CROSS -> conferma one-click (password preesistente)
    # `requires_password` e' un flag derivato esposto per comodita' FE.
    def get(self, request: Request, token: str) -> JsonResponse:
        resolved = resolve_shop_token(token, _token_service)
        if resolved is None:
            return success_response({
                "valid": False,
                "message": "Token non valido, scaduto o gia' utilizzato.",
            })
        _, _, token_type = resolved
        return success_response({
            "valid": True,
            "token_type": token_type,
            "requires_password": token_type == INVITO_SHOP_TOKEN_TIPO,
        })


class AttivazioneShopView(APIView):
    """POST: attivazione shop. Gestisce entrambi i token type:
    - INVITO_SHOP (email nuova): consume token + set password + reset flag;
      identita SHOP_CUSTOMER era gia' creata attiva dall'invito.
    - ATTIVAZIONE_SHOP_CROSS (email esistente): consume token + riattiva
      identita; password preesistente invariata.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(
        summary="Attivazione shop customer (INVITO o CROSS)",
        request=inline_serializer(
            name="AttivazioneShopReq",
            fields={
                "token": serializers.CharField(),
                # Opzionali: obbligatori solo per token_type=INVITO_SHOP.
                "new_password": serializers.CharField(required=False),
                "new_password_confirm": serializers.CharField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="AttivazioneShopResp",
            fields={
                "data": inline_serializer(
                    name="AttivazioneShopData",
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
                code=E_ATTIVAZIONE_SHOP,
                message="Token obbligatorio.",
            )

            resolved = resolve_shop_token(token, _token_service)
            ErrorManager.require(
                resolved is not None,
                code=E_ATTIVAZIONE_SHOP,
                message="Token non valido, scaduto o gia' utilizzato.",
            )
            assert resolved is not None
            auth_user_id, meta, token_type = resolved

            user = User.objects.filter(id=auth_user_id).first()
            ErrorManager.require(
                user is not None,
                code=E_ATTIVAZIONE_SHOP,
                message="Utente non trovato.",
            )
            assert user is not None

            identita_id = extract_identita_id_from_token_meta(meta)
            ErrorManager.require(
                identita_id is not None,
                code=E_ATTIVAZIONE_SHOP,
                message=(
                    "Token privo di riferimento identita. "
                    "Richiedere un nuovo invito dall'amministratore."
                ),
            )
            assert identita_id is not None

            ip = get_client_ip(
                request._request if hasattr(request, "_request") else request
            )

            if token_type == INVITO_SHOP_TOKEN_TIPO:
                self._attiva_flow_invito(
                    token=token, user=user, identita_id=identita_id,
                    payload=payload, ip=ip,
                )
                msg = (
                    "Account shop attivato con successo. "
                    "Effettua il login con la nuova password."
                )
            else:
                # ATTIVAZIONE_SHOP_CROSS
                self._attiva_flow_cross(
                    token=token, identita_id=identita_id, ip=ip,
                )
                msg = (
                    "Accesso shop attivato. "
                    "Effettua il login con le tue credenziali esistenti."
                )

            logger.info(
                "security.shop_attivato user_id=%s identita_id=%s token_type=%s",
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
            code=E_ATTIVAZIONE_SHOP,
            message="Nuova password obbligatoria per questo token.",
        )
        ErrorManager.require(
            new_password == new_password_confirm,
            code=E_ATTIVAZIONE_SHOP,
            message="La nuova password e la conferma non coincidono.",
        )

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            ErrorManager.require(
                False,
                code=E_ATTIVAZIONE_SHOP,
                message=" ".join(exc.messages),
            )

        with transaction.atomic():
            _token_service.consume(token, INVITO_SHOP_TOKEN_TIPO, ip=ip)
            apply_new_password(
                user, new_password,
                blacklist_tokens=False,
                auth_repo=_auth_repo,
            )
            # L'identita' nasce disattivata anche nel flow INVITO e si
            # attiva QUI, nella stessa transazione del consumo (M-3).
            self._attiva_identita_o_rifiuta(identita_id)

    # Scopo: Flow CROSS — consume token + riattiva identita. Password
    # preesistente invariata (l'utente e' gia' operatore o altra veste).
    def _attiva_flow_cross(
        self,
        *,
        token: str,
        identita_id: int,
        ip: str | None,
    ) -> None:
        with transaction.atomic():
            _token_service.consume(
                token, ATTIVAZIONE_SHOP_CROSS_TOKEN_TIPO, ip=ip
            )
            self._attiva_identita_o_rifiuta(identita_id)

    # Scopo: Attiva l'identita' dell'invito, comune ai due flussi (INVITO e
    # CROSS): la veste nasce disattivata e diventa un accesso solo qui, al
    # consumo del token. Rowcount 0 = identita' rimossa fra l'invito e il
    # consumo: il token e' gia' marcato utilizzato DENTRO la transazione del
    # chiamante, quindi sollevare fa rollback di consumo e password insieme,
    # e l'admin rigenera l'invito.
    def _attiva_identita_o_rifiuta(self, identita_id: int) -> None:
        if _portale_repo.riattiva_identita(identita_id):
            return
        logger.warning(
            "security.shop_attiva_identita_fallita identita_id=%s — "
            "riga non trovata, rollback consume token",
            identita_id,
        )
        ErrorManager.require(
            False,
            code=E_ATTIVAZIONE_SHOP,
            message=(
                "Identita shop non piu' disponibile. "
                "Contattare l'amministratore per un nuovo invito."
            ),
        )
