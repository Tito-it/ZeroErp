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
from apps.core.services.auth_constants import (
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)
from apps.core.services.auth_helpers import (
    apply_new_password,
    extract_identita_id_from_token_meta,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.request_context import get_client_ip
from apps.core.services.token_service import TokenService
from apps.portale.db.portale_repository import PortaleRepository
from apps.portale.services.invito_portale_service import (
    ATTIVAZIONE_PORTALE_CROSS_TOKEN_TIPO,
    INVITO_PORTALE_TOKEN_TIPO,
    resolve_portale_token,
)

logger = logging.getLogger("security")

E_ATTIVAZIONE_PORTALE = "E_ATTIVAZIONE_PORTALE"
E_ATTIVAZIONE_SHOP_CROSS = "E_ATTIVAZIONE_SHOP_CROSS"

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
            # L'identita' nasce disattivata anche nel flow INVITO e si
            # attiva QUI, nella stessa transazione del consumo (M-3).
            self._attiva_identita_o_rifiuta(identita_id)

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
            "security.portale_attiva_identita_fallita identita_id=%s — "
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
    """POST /api/v1/portale/profile/activate-shop/ — attivazione cross-veste
    self-service (B1 §13.7).

    L'utente CLIENTE_PORTALE autenticato aggiunge la veste SHOP_CUSTOMER
    sul proprio soggetto_ruolo (CL). Attivazione immediata, no email/token:
    il consenso e' implicito nel click. Idempotente (se esiste gia' attiva,
    ritorna `already_active`).

    Solo CLIENTE_PORTALE: FORNITORE_PORTALE non puo' attivare shop (B2C
    consumer-only). SHOP_CUSTOMER e CLIENTE_PORTALE condividono il ruolo
    anagrafico CL — la nuova identita vive sullo stesso soggetto_ruolo
    della veste portale corrente.
    """

    skip_area_check = True

    @extend_schema(
        summary="Attiva veste SHOP_CUSTOMER per utente portale cliente",
        responses={200: inline_serializer(
            name="ActivateShopResp",
            fields={
                "data": inline_serializer(
                    name="ActivateShopData",
                    fields={
                        "activated": serializers.BooleanField(required=False),
                        "already_active": serializers.BooleanField(required=False),
                        "identita_id": serializers.IntegerField(),
                        "message": serializers.CharField(),
                    },
                ),
            },
        )},
    )
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            # Filtro veste: solo CLIENTE_PORTALE puo' attivare shop.
            # FORNITORE_PORTALE blocca a 400 (lo shop e' B2C consumer).
            ruolo = PermissionResolver.get_ruolo_applicativo(request.user)
            ErrorManager.require(
                ruolo == RUOLO_APPLICATIVO_CLIENTE_PORTALE,
                code=E_ATTIVAZIONE_SHOP_CROSS,
                message="Solo i clienti portale possono attivare l'accesso shop.",
            )

            # Soggetto_ruolo dell'identita corrente — letto dalla GUC
            # `app.soggetto_ruolo_id` propagata da JwtAuditAuthentication
            # (5 GUC settate insieme post §8.3.4). Fail-closed se vuota.
            soggetto_ruolo_id = self._read_soggetto_ruolo_from_guc()
            ErrorManager.require(
                soggetto_ruolo_id is not None,
                code=E_ATTIVAZIONE_SHOP_CROSS,
                message="Identita corrente non risolvibile.",
            )
            assert soggetto_ruolo_id is not None

            # Idempotente: se la veste SHOP_CUSTOMER esiste gia' attiva
            # sullo stesso soggetto_ruolo, ritorna conferma senza modifiche.
            existing = _portale_repo.find_identita_portale(
                soggetto_ruolo_id, RUOLO_APPLICATIVO_SHOP_CUSTOMER
            )

            # Guard anti-tampering: se l'identita SHOP esistente e' collegata
            # a un auth_user diverso dal corrente, blocchiamo. Stato anomalo
            # (soggetto_ruolo riassegnato manualmente o migrazione incoerente)
            # che richiede intervento admin, non auto-resolve.
            if existing is not None:
                existing_auth = existing.get("auth_user_id")
                ErrorManager.require(
                    existing_auth is None or int(existing_auth) == request.user.id,
                    code=E_ATTIVAZIONE_SHOP_CROSS,
                    message=(
                        "Veste shop gia' collegata a un altro utente. "
                        "Contattare l'amministratore."
                    ),
                )

            if existing is not None and existing.get("attivo"):
                return {
                    "already_active": True,
                    "identita_id": int(existing["identita_id"]),
                    "message": (
                        "Accesso shop gia' attivo. "
                        "Effettua il login dal canale shop con le tue credenziali."
                    ),
                }

            # Creazione o riattivazione, in transazione atomica.
            with transaction.atomic():
                if existing is not None:
                    # Identita SHOP_CUSTOMER esisteva ma disattivata
                    # (es. precedente attivazione poi sospesa) — riattiva.
                    identita_id = int(existing["identita_id"])
                    _portale_repo.riattiva_identita(identita_id)
                else:
                    # Prima attivazione veste shop: crea identita
                    # `attivo=True, deve_cambiare_password=False` perche'
                    # la password e' quella gia' usata sul portale (stesso
                    # auth_user, modello SSO multi-veste).
                    identita_id = _portale_repo.create_identita_portale(
                        auth_user_id=request.user.id,
                        soggetto_ruolo_id=soggetto_ruolo_id,
                        ruolo_applicativo=RUOLO_APPLICATIVO_SHOP_CUSTOMER,
                        attivo=True,
                        deve_cambiare_password=False,
                    )

            logger.info(
                "security.shop_attivato_cross user_id=%s identita_id=%s "
                "soggetto_ruolo_id=%s",
                request.user.id, identita_id, soggetto_ruolo_id,
            )
            return {
                "activated": True,
                "identita_id": identita_id,
                "message": (
                    "Accesso shop attivato. "
                    "Effettua il login dal canale shop con le stesse credenziali."
                ),
            }

        return handle_post_json(request, handler=_handler)

    # Scopo: Legge soggetto_ruolo_id dalla GUC PG settata da
    # JwtAuditAuthentication. Mockabile nei test che non passano dalla
    # auth chain reale.
    def _read_soggetto_ruolo_from_guc(self) -> int | None:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT NULLIF(current_setting('app.soggetto_ruolo_id', true), '')::int"
            )
            row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None
