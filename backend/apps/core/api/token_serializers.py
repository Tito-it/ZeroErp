# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Serializer JWT custom — aggiunge claim `sid` (session ID)
#        stabile che persiste su access token e refresh rotation.
#        Risolve il problema di identificazione univoca della sessione
#        quando i JTI cambiano ad ogni rotazione del refresh token.
# ------------------------------------------------------------

from __future__ import annotations

import uuid

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken


class SidTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Aggiunge `sid` (session ID) al refresh token al momento del login.

    Il claim `sid` viene automaticamente copiato:
    - nell'access token (SimpleJWT copia tutti i claim non in no_copy_claims)
    - nei refresh token ruotati (SimpleJWT modifica solo jti/exp/iat)
    """

    @classmethod
    # Scopo: Genera il refresh token con il claim `sid` aggiuntivo.
    # Nota: super().get_token() chiama RefreshToken.for_user() che crea
    # l'OutstandingToken PRIMA che sid venga aggiunto. Serve aggiornare
    # il JWT salvato nell'OutstandingToken per includere il claim sid.
    def get_token(cls, user):
        token = super().get_token(user)
        token["sid"] = str(uuid.uuid4())
        # Aggiorna l'OutstandingToken con il JWT che ora include sid.
        jti = token[api_settings.JTI_CLAIM]
        OutstandingToken.objects.filter(jti=jti).update(token=str(token))
        return token
