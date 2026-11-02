# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint namespace `/api/v1/portale/*` — flussi auth portale
#        (attivazione invito) + futuri endpoint MVP (me, billing-account,
#        fatture, scadenze, ordini-ricevuti, pagamenti). Gli endpoint
#        pubblici (attivazione-validate + attivazione) non richiedono JWT:
#        sono il building block `attivazione_veste_views` sulla porta
#        PORTALE. Gli endpoint autenticati usano PortaleAPIView.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.attivazione_veste_views import (
    AttivazioneVesteValidateView,
    AttivazioneVesteView,
)
from apps.core.api.base_views import PortaleAPIView
from apps.core.api.endpoint_helpers import handle_post_json, utente_autenticato_id
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_constants import (
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.invito_veste import PORTA_PORTALE
from apps.core.services.permissions_resolver import PermissionResolver
from apps.portale.db.portale_repository import PortaleRepository

logger = logging.getLogger("security")

E_ATTIVAZIONE_SHOP_CROSS = "E_ATTIVAZIONE_SHOP_CROSS"

_auth_repo = AuthRepository()
_portale_repo = PortaleRepository()


class AttivazionePortaleValidateView(AttivazioneVesteValidateView):
    """GET: verifica se un token attivazione portale e' ancora valido
    (no consume). Dice alla pagina se chiedere la password (§8.4.2)."""

    porta = PORTA_PORTALE


class AttivazionePortaleView(AttivazioneVesteView):
    """POST: attivazione portale cliente/fornitore (con password o con un clic)."""

    porta = PORTA_PORTALE
    messaggio_con_password = (
        "Account portale attivato con successo. "  # noqa: S105 — testo del messaggio, non una password
        "Effettua il login con la nuova password."
    )
    messaggio_cross = (
        "Accesso portale attivato. "
        "Effettua il login con le tue credenziali esistenti."
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
        request=None,
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
                    _auth_repo.attiva_identita(
                        identita_id,
                        auth_user_id=utente_autenticato_id(request),
                        ruoli_applicativi=(RUOLO_APPLICATIVO_SHOP_CUSTOMER,),
                    )
                else:
                    # Prima attivazione veste shop: crea identita
                    # `attivo=True`: la password e' quella gia' usata sul
                    # portale (stesso auth_user, modello SSO multi-veste).
                    identita_id = _portale_repo.create_identita_portale(
                        auth_user_id=utente_autenticato_id(request),
                        soggetto_ruolo_id=soggetto_ruolo_id,
                        ruolo_applicativo=RUOLO_APPLICATIVO_SHOP_CUSTOMER,
                        attivo=True,
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
