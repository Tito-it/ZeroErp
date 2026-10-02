# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il secondo fattore di un operatore, dal lato dell'amministratore
#        (brief sicurezza §3.4-bis, T-3), sotto
#        /api/v1/amm-software/operatori/<auth_user_id>/secondo-fattore/:
#          GET  /            lo stato, e se l'obbligo viene dalla credenziale
#          POST obbligo/     accende o spegne l'obbligo sulla CREDENZIALE
#          POST disattiva/   cancella il device (telefono perso), motivo obbligatorio
# Note: `AdminAPIView` (binding SUPER_ADMIN), e i verbi del DB lo ricontrollano
#       (`fn_guard_super_admin`). La credenziale e' una: l'obbligo e il device
#       valgono per tutte le porte, non per la sola veste di operatore.
#       Disattivare NON chiude le sessioni aperte (decisione 8, Tid 2026-09-30).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.amm_software.services.amm_software_service import E_AMM_VALIDAZIONE, AmmSoftwareService
from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.db.secondo_fattore_repository import STATI_DEVICE
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.request_context import richiesta_django
from apps.core.services.secondo_fattore_service import SecondoFattoreService

_STATO = inline_serializer(
    name="AmmSecondoFattoreStatoResp",
    fields={
        "stato": serializers.ChoiceField(choices=STATI_DEVICE),
        "obbligatorio": serializers.BooleanField(),
        "motivo": serializers.CharField(allow_null=True),
        "obbligo_sulla_credenziale": serializers.BooleanField(),
        "codici_recupero_rimasti": serializers.IntegerField(),
    },
)


# Scopo: L'operatore deve esistere: su un id inesistente il DB risponderebbe
#        «nessun obbligo, nessun device», plausibile e sbagliato.
def _operatore_esistente(auth_user_id: int) -> None:
    AmmSoftwareService().get_operatore(auth_user_id)


class OperatoreSecondoFattoreView(AdminAPIView):
    @extend_schema(responses={200: _STATO}, summary="Secondo fattore di un operatore")
    # Scopo: Lo stato del secondo fattore dell'operatore.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        _operatore_esistente(auth_user_id)
        return success_response(SecondoFattoreService().stato_per_admin(auth_user_id))


class OperatoreSecondoFattoreObbligoView(AdminAPIView):
    @extend_schema(
        request=inline_serializer(name="AmmSecondoFattoreObbligoReq", fields={"valore": serializers.BooleanField()}),
        responses={200: _STATO},
        summary="Secondo fattore: obbligo sulla credenziale",
    )
    # Scopo: Accende o spegne l'obbligo sulla credenziale dell'operatore.
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            valore = PayloadValidator(validation_code=E_AMM_VALIDAZIONE).require_bool(payload, "valore")
            _operatore_esistente(auth_user_id)
            return SecondoFattoreService().imposta_obbligo(auth_user_id, valore)

        return handle_post_json(request, handler=_handler)


class OperatoreSecondoFattoreDisattivaView(AdminAPIView):
    @extend_schema(
        request=inline_serializer(name="AmmSecondoFattoreDisattivaReq", fields={"motivo": serializers.CharField()}),
        responses={200: _STATO},
        summary="Secondo fattore: disattiva il device di un operatore",
    )
    # Scopo: Cancella il device dell'operatore (telefono perso). Il motivo lo
    #        pretende il DB (E_TOTP_MOTIVO_OBBLIGATORIO); la traccia la scrive
    #        il servizio, nella stessa transazione.
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            _operatore_esistente(auth_user_id)
            return SecondoFattoreService().disattiva_da_admin(
                auth_user_id,
                motivo=payload.get("motivo"),
                chi_agisce=request.user.id,
                request=richiesta_django(request),
            )

        return handle_post_json(request, handler=_handler)
