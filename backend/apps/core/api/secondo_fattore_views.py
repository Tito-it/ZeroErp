# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il secondo fattore della PROPRIA credenziale (brief sicurezza
#        §3.4-bis, T-3), sotto /api/v1/auth/secondo-fattore/:
#          GET  /                 lo stato (device, obbligo e motivo, codici rimasti)
#          POST registra/         avvia (o ricomincia) la configurazione, dietro la
#                                 password: QR, segreto e codici di recupero,
#                                 mostrati UNA volta
#          POST conferma/         chiude la configurazione col primo codice
#          POST codici-recupero/  codici nuovi, dietro un codice dell'app
#          POST disattiva/        dietro un codice dell'app o di recupero
# Note: Sono la strada che soddisfa l'obbligo del secondo fattore: le view
#       dichiarano `obblighi_ammessi`, cosi' il cancello le lascia aperte a chi
#       deve ancora configurarlo. La logica sta in `SecondoFattoreService`.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.cancello_obblighi import OBBLIGO_SECONDO_FATTORE
from apps.core.api.endpoint_helpers import handle_post_json, utente_autenticato, utente_autenticato_id
from apps.core.api.success_responses import success_response
from apps.core.db.secondo_fattore_repository import STATI_DEVICE
from apps.core.services.request_context import provenienza_obbligatoria, richiesta_django
from apps.core.services.secondo_fattore_service import SecondoFattoreService

_STATO = inline_serializer(
    name="CoreSecondoFattoreStatoResp",
    fields={
        "stato": serializers.ChoiceField(choices=STATI_DEVICE),
        "obbligatorio": serializers.BooleanField(),
        "motivo": serializers.CharField(allow_null=True),
        "codici_recupero_rimasti": serializers.IntegerField(),
    },
)
_CONFIGURAZIONE = inline_serializer(
    name="CoreSecondoFattoreConfigurazioneResp",
    fields={
        "qr_data_uri": serializers.CharField(),
        "segreto": serializers.CharField(),
        "codici_recupero": serializers.ListField(child=serializers.CharField()),
    },
)
_CODICI = inline_serializer(
    name="CoreSecondoFattoreCodiciResp",
    fields={"codici_recupero": serializers.ListField(child=serializers.CharField())},
)
_CON_CODICE = inline_serializer(
    name="CoreSecondoFattoreCodiceReq", fields={"codice": serializers.CharField()},
)
_CON_PASSWORD = inline_serializer(
    name="CoreSecondoFattorePasswordReq", fields={"password": serializers.CharField()},
)
_CON_PROVA = inline_serializer(
    name="CoreSecondoFattoreProvaReq",
    fields={
        "codice": serializers.CharField(required=False),
        "codice_recupero": serializers.CharField(required=False),
    },
)


class _SecondoFattoreProprioView(DomainAPIView):
    """Base: la credenziale su se stessa, aperta anche con l'obbligo pendente."""

    skip_area_check = True
    obblighi_ammessi = frozenset({OBBLIGO_SECONDO_FATTORE})


class SecondoFattoreStatoView(_SecondoFattoreProprioView):
    @extend_schema(responses={200: _STATO}, summary="Secondo fattore: lo stato del proprio accesso")
    # Scopo: Lo stato del proprio secondo fattore.
    def get(self, request: Request) -> JsonResponse:
        return success_response(SecondoFattoreService().stato(utente_autenticato_id(request)))


class SecondoFattoreRegistraView(_SecondoFattoreProprioView):
    @extend_schema(request=_CON_PASSWORD, responses={200: _CONFIGURAZIONE}, summary="Secondo fattore: avvia la configurazione")
    # Scopo: Avvia la configurazione, dietro la password della credenziale: QR,
    #        segreto e codici di recupero, una volta.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return SecondoFattoreService().avvia_configurazione(
                utente_autenticato(request), payload.get("password"), request=request,
            )

        return handle_post_json(request, handler=_handler)


class SecondoFattoreConfermaView(_SecondoFattoreProprioView):
    @extend_schema(request=_CON_CODICE, responses={200: _STATO}, summary="Secondo fattore: conferma col primo codice")
    # Scopo: Chiude la configurazione col primo codice dell'app.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return SecondoFattoreService().conferma_configurazione(utente_autenticato(request), payload.get("codice"))

        return handle_post_json(request, handler=_handler)


class SecondoFattoreCodiciRecuperoView(_SecondoFattoreProprioView):
    @extend_schema(request=_CON_CODICE, responses={200: _CODICI}, summary="Secondo fattore: codici di recupero nuovi")
    # Scopo: Codici di recupero nuovi, dietro un codice dell'app.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return SecondoFattoreService().rigenera_codici_recupero(
                utente_autenticato(request), payload.get("codice"), provenienza=provenienza_obbligatoria(request),
            )

        return handle_post_json(request, handler=_handler)


class SecondoFattoreDisattivaView(_SecondoFattoreProprioView):
    @extend_schema(request=_CON_PROVA, responses={200: _STATO}, summary="Secondo fattore: disattiva il proprio")
    # Scopo: Disattiva il proprio secondo fattore, dietro un codice dell'app o
    #        di recupero (decisione 7).
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return SecondoFattoreService().disattiva_propria(
                utente_autenticato(request),
                codice=payload.get("codice"),
                codice_recupero=payload.get("codice_recupero"),
                provenienza=provenienza_obbligatoria(request),
                request=richiesta_django(request),
            )

        return handle_post_json(request, handler=_handler)
