# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint admin-side per invitare al portale un cliente o un
#        fornitore. Vive in `apps/anagrafiche` per coerenza con il CRUD
#        dei rispettivi domini, ma delega al service `InvitoPortaleService`
#        dell'app portale (single source of truth).
# ⭐ Gli accessi portale/shop sono una PARTE della scheda cliente o fornitore
#    (il tab «Accessi» del suo drawer): ogni view chiede l'oggetto, non la sola
#    area (brief-db-be-fe-catalogo-oggetti-permessi §1, dal 2026-09-28).
#    Prima un `BLOCCATO` sul cliente nascondeva il tab e lasciava aperta l'API.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json, utente_autenticato_id
from apps.core.api.payload_validators import optional_bool
from apps.core.services.service_errors import E_VALIDATION_INPUT
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.api.success_responses import success_response
from apps.core.services.auth_constants import (
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)
from apps.portale.services.invito_portale_service import InvitoPortaleService

# Il corpo delle disattivazioni: la veste del referente da spegnere.
_CORPO = PayloadValidator(validation_code=E_VALIDATION_INPUT)

# Lo schema del corpo delle tre disattivazioni (una veste per referente, D-M7).
_DISATTIVA_REQ_FIELDS: dict[str, serializers.Field] = {
    "identita_id": serializers.IntegerField(
        help_text="La veste del referente da spegnere: una voce dell'elenco "
        "dello stato accessi. Una veste di un altro soggetto o di un altro "
        "tipo e' un 404 `E_VESTE_NON_TROVATA`."
    ),
}


class ClientiInvitaPortaleView(DomainAPIView):
    """POST admin: invita al portale il cliente (billing_account) indicato."""

    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "cliente")

    @extend_schema(
        summary="Invita un cliente al portale",
        request=inline_serializer(
            name="ClienteInvitaPortaleReq",
            fields={
                "email": serializers.CharField(
                    help_text="Email destinatario. Il sistema crea "
                    "auth_user+identita se mancanti."
                ),
                "reinvio": serializers.BooleanField(
                    required=False,
                    help_text="Se true, invalida token precedenti prima di "
                    "generare il nuovo invito.",
                ),
            },
        ),
        responses={200: inline_serializer(
            name="ClienteInvitaPortaleResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Admin-only endpoint per invitare un cliente al portale.
    #        Input: email destinatario + flag reinvio. Delega al service.
    def post(self, request: Request, cliente_id: int) -> JsonResponse:
        service = InvitoPortaleService()

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            email = str(payload.get("email") or "")
            reinvio = optional_bool(payload, "reinvio", default=False)
            fn = (
                service.reinvia_invito_cliente
                if reinvio
                else service.invia_invito_cliente
            )
            return fn(
                cliente_id=cliente_id,
                email=email,
                invitato_da_user_id=utente_autenticato_id(request),
            )

        return handle_post_json(request, handler=_handler)


class ClientiInvitaShopView(DomainAPIView):
    """POST admin: invita allo shop lo SHOP_CUSTOMER del cliente indicato.

    Simmetrico a ClientiInvitaPortaleView ma crea identita SHOP_CUSTOMER
    invece di CLIENTE_PORTALE, riusando lo stesso service
    InvitoPortaleService (B1 §13.7 admin-driven). Stesso cliente, stesso
    soggetto_ruolo (ruolo CL) — SHOP_CUSTOMER e CLIENTE_PORTALE condividono
    il ruolo anagrafico CL (vedi guida architettura-multi-face-auth §4.3).
    Il branching email nuova/esistente (INVITO vs CROSS) e' ereditato dal
    flow comune.
    """

    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "cliente")

    @extend_schema(
        summary="Invita un cliente come shop customer",
        request=inline_serializer(
            name="ClienteInvitaShopReq",
            fields={
                "email": serializers.CharField(
                    help_text="Email destinatario. Il sistema crea "
                    "auth_user+identita SHOP_CUSTOMER se mancanti."
                ),
                "reinvio": serializers.BooleanField(
                    required=False,
                    help_text="Se true, invalida token precedenti prima di "
                    "generare il nuovo invito.",
                ),
            },
        ),
        responses={200: inline_serializer(
            name="ClienteInvitaShopResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Admin-only endpoint per invitare un cliente come shop customer.
    #        Delega al service InvitoPortaleService (gestisce anche SHOP).
    def post(self, request: Request, cliente_id: int) -> JsonResponse:
        service = InvitoPortaleService()

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            email = str(payload.get("email") or "")
            reinvio = optional_bool(payload, "reinvio", default=False)
            fn = (
                service.reinvia_invito_shop_customer
                if reinvio
                else service.invia_invito_shop_customer
            )
            return fn(
                cliente_id=cliente_id,
                email=email,
                invitato_da_user_id=utente_autenticato_id(request),
            )

        return handle_post_json(request, handler=_handler)


class FornitoriInvitaPortaleView(DomainAPIView):
    """POST admin: invita al portale il fornitore indicato."""

    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "fornitore")

    @extend_schema(
        summary="Invita un fornitore al portale",
        request=inline_serializer(
            name="FornitoreInvitaPortaleReq",
            fields={
                "email": serializers.CharField(),
                "reinvio": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="FornitoreInvitaPortaleResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Admin-only endpoint per invitare un fornitore al portale.
    def post(self, request: Request, fornitore_id: int) -> JsonResponse:
        service = InvitoPortaleService()

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            email = str(payload.get("email") or "")
            reinvio = optional_bool(payload, "reinvio", default=False)
            fn = (
                service.reinvia_invito_fornitore
                if reinvio
                else service.invia_invito_fornitore
            )
            return fn(
                fornitore_id=fornitore_id,
                email=email,
                invitato_da_user_id=utente_autenticato_id(request),
            )

        return handle_post_json(request, handler=_handler)


# ── Stato + disattivazione veste (§6.2.4 + §6.2.6) ──────────────────


class ClientiStatoAccessiView(DomainAPIView):
    """GET admin: i referenti del cliente, per veste (portale + shop)."""

    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "cliente")

    @extend_schema(
        summary="Stato accessi portale + shop del cliente",
        description=(
            "`portale` e `shop`: i referenti per tipo di veste, una voce per "
            "veste (anche spenta) con `identita_id`, `username`, `email`, "
            "`stato` (`script.fn_stato_veste`), `utilizzabile` "
            "(`script.fn_veste_utilizzabile`), date e invito. Elenco vuoto: "
            "nessuno invitato. `email_suggerita`: l'email da proporre "
            "nell'invito (il primo referente, poi il contatto PRINCIPALE del "
            "ruolo, poi quello di default), o null."
        ),
        responses={200: inline_serializer(
            name="ClienteStatoAccessiResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def get(self, request: Request, cliente_id: int) -> JsonResponse:
        stato = InvitoPortaleService().get_stato_accessi_cliente(cliente_id)
        return success_response(stato)


class FornitoriStatoAccessiView(DomainAPIView):
    """GET admin: i referenti del fornitore (veste FORNITORE_PORTALE)."""

    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "fornitore")

    @extend_schema(
        summary="Stato accesso portale del fornitore",
        description=(
            "`portale`: i referenti, una voce per veste (stessa forma del "
            "cliente). `email_suggerita`: l'email da proporre nell'invito (il "
            "primo referente, poi il contatto PRINCIPALE del ruolo, poi quello "
            "di default), o null."
        ),
        responses={200: inline_serializer(
            name="FornitoreStatoAccessiResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def get(self, request: Request, fornitore_id: int) -> JsonResponse:
        stato = InvitoPortaleService().get_stato_accessi_fornitore(fornitore_id)
        return success_response(stato)


class ClientiDisattivaPortaleView(DomainAPIView):
    """POST admin: revoca la veste CLIENTE_PORTALE di un referente del cliente."""

    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "cliente")

    @extend_schema(
        request=inline_serializer(name="ClienteDisattivaPortaleReq", fields=_DISATTIVA_REQ_FIELDS),
        summary="Disattiva l'accesso portale di un referente del cliente",
        responses={200: inline_serializer(
            name="ClienteDisattivaPortaleResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def post(self, request: Request, cliente_id: int) -> JsonResponse:
        service = InvitoPortaleService()

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return service.disattiva_veste_cliente(
                cliente_id=cliente_id,
                ruolo_applicativo=RUOLO_APPLICATIVO_CLIENTE_PORTALE,
                identita_id=_CORPO.require_positive_int(payload, "identita_id"),
                disattivato_da_user_id=utente_autenticato_id(request),
            )

        return handle_post_json(request, handler=_handler)


class ClientiDisattivaShopView(DomainAPIView):
    """POST admin: revoca la veste SHOP_CUSTOMER di un referente del cliente."""

    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "cliente")

    @extend_schema(
        request=inline_serializer(name="ClienteDisattivaShopReq", fields=_DISATTIVA_REQ_FIELDS),
        summary="Disattiva l'accesso shop di un referente del cliente",
        responses={200: inline_serializer(
            name="ClienteDisattivaShopResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def post(self, request: Request, cliente_id: int) -> JsonResponse:
        service = InvitoPortaleService()

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return service.disattiva_veste_cliente(
                cliente_id=cliente_id,
                ruolo_applicativo=RUOLO_APPLICATIVO_SHOP_CUSTOMER,
                identita_id=_CORPO.require_positive_int(payload, "identita_id"),
                disattivato_da_user_id=utente_autenticato_id(request),
            )

        return handle_post_json(request, handler=_handler)


class FornitoriDisattivaPortaleView(DomainAPIView):
    """POST admin: revoca la veste FORNITORE_PORTALE di un referente del fornitore."""

    area_funzionale = "anagrafiche"
    model_permission = ("anagrafiche", "fornitore")

    @extend_schema(
        request=inline_serializer(name="FornitoreDisattivaPortaleReq", fields=_DISATTIVA_REQ_FIELDS),
        summary="Disattiva l'accesso portale di un referente del fornitore",
        responses={200: inline_serializer(
            name="FornitoreDisattivaPortaleResp",
            fields={"data": serializers.DictField()},
        )},
    )
    def post(self, request: Request, fornitore_id: int) -> JsonResponse:
        service = InvitoPortaleService()

        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return service.disattiva_veste_fornitore(
                fornitore_id=fornitore_id,
                identita_id=_CORPO.require_positive_int(payload, "identita_id"),
                disattivato_da_user_id=utente_autenticato_id(request),
            )

        return handle_post_json(request, handler=_handler)
