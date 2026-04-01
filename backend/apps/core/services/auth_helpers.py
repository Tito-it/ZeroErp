# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper riutilizzabili per flussi autenticazione:
#        - validate_and_extract_token: validazione token senza consumo
#        - apply_new_password: set password + reset flag + blacklist JWT
#        Eliminano duplicazione tra password_reset, attivazione, change_password.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.db.auth_repository import AuthRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.token_service import TokenService

logger = logging.getLogger("security")


# Scopo: Valida un token monouso senza consumarlo. Estrae auth_user_id e meta.
#        Lancia ServiceError se il token non e' valido, scaduto o gia' utilizzato.
def validate_and_extract_token(
    token: str,
    tipo: str,
    error_code: str,
    token_service: TokenService | None = None,
) -> tuple[int, dict[str, Any]]:
    svc = token_service or TokenService()
    token_result = svc.validate(token, tipo)
    ErrorManager.require(
        token_result is not None,
        code=error_code,
        message="Token non valido, scaduto o gia' utilizzato.",
    )
    assert token_result is not None
    return token_result


# Scopo: Applica nuova password, resetta flag deve_cambiare_password,
#        opzionalmente blacklista tutti i refresh token JWT precedenti.
#        Tutto in un'unica transazione atomica.
def apply_new_password(
    user: User,
    new_password: str,
    *,
    blacklist_tokens: bool = True,
    auth_repo: AuthRepository | None = None,
) -> None:
    repo = auth_repo or AuthRepository()
    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password"])
        repo.set_deve_cambiare_password(user.id, False)

        if blacklist_tokens:
            for ot in OutstandingToken.objects.filter(user=user):
                try:
                    RefreshToken(ot.token).blacklist()
                except TokenError:
                    logger.debug(
                        "Blacklist token fallita per user_id=%s: token gia' invalido",
                        user.id,
                    )
