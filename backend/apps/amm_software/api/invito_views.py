# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API admin per invito operatore al primo accesso.
#        Solo ruolo ADMIN.
# ------------------------------------------------------------

from __future__ import annotations


from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from apps.core.api.base_views import AdminAPIView
from apps.core.api.success_responses import success_response
from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService
from apps.core.api.endpoint_helpers import utente_autenticato_id


class InvitaOperatoreView(AdminAPIView):
    """POST: invia invito al primo accesso per un operatore."""

    @extend_schema(request=None, summary="Invia invito operatore", responses={200: dict})
    # Scopo: Genera token invito, imposta password temporanea, invia email.
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        service = InvitoOperatoreService()
        result = service.invia_invito(auth_user_id, invitato_da_user_id=utente_autenticato_id(request))
        return success_response(result)


class ReinviaInvitoView(AdminAPIView):
    """POST: reinvia invito (invalida token precedente, genera nuovo)."""

    @extend_schema(request=None, summary="Reinvia invito operatore", responses={200: dict})
    # Scopo: Invalida token invito precedente e ne genera uno nuovo.
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        service = InvitoOperatoreService()
        result = service.reinvia_invito(auth_user_id, invitato_da_user_id=utente_autenticato_id(request))
        return success_response(result)
