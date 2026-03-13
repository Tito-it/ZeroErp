# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint GET /api/v1/core/me/ — profilo utente completo.
#        Restituisce dati utente, soggetto, risorse umane e emittente
#        fiscale associato, chiamando script.fn_get_user_profile.
# ------------------------------------------------------------

from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.api.permissions import ZeroERPPermission
from apps.core.api.success_responses import success_response
from apps.core.db.core_repository import CoreRepository


class UserProfileView(APIView):
    """Profilo utente corrente — dati soggetto, risorse umane, emittente."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    skip_area_check = True

    @extend_schema(
        summary="Profilo utente corrente",
        description=(
            "Restituisce il profilo completo dell'utente autenticato: "
            "dati anagrafici (soggetto), risorse umane, ruolo_sistema "
            "e dati emittente fiscale associato (se presente). "
            "Il payload e' prodotto dalla funzione DB script.fn_get_user_profile."
        ),
        responses={
            200: inline_serializer(
                name="UserProfileResponse",
                fields={
                    "data": inline_serializer(
                        name="UserProfileData",
                        fields={
                            "utente": serializers.DictField(
                                help_text="Dati auth_user: id, username, first_name, last_name, email."
                            ),
                            "ruolo_sistema": serializers.CharField(
                                allow_null=True,
                                help_text="ADMIN | OPERATIVO | DISABILITATO | null.",
                            ),
                            "risorse_umane": serializers.DictField(
                                help_text="Dati risorsa umana: qualifica, UO, validita'."
                            ),
                            "soggetto": serializers.DictField(
                                help_text="Dati soggetto dell'utente (da fn_get_soggetto_dati_by_ruolo)."
                            ),
                            "emittente": serializers.DictField(
                                allow_null=True,
                                help_text="Dati emittente fiscale + soggetto ditta (null se non associato).",
                            ),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il profilo completo dell'utente autenticato.
    # Chiama script.fn_get_user_profile(auth_user_id) e restituisce il JSONB.
    def get(self, request: Request):
        repo = CoreRepository()
        profile = repo.get_user_profile(request.user.id)
        return success_response(profile)
