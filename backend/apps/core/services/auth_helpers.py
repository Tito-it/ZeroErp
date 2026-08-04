# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper riutilizzabili per flussi autenticazione:
#        - extract_identita_id_from_request: claim `identita_id` dal JWT
#        - extract_identita_id_from_token_meta: `identita_id` dal meta token monouso
#        - validate_and_extract_token: validazione token senza consumo
#        - apply_new_password: set password + reset flag + blacklist JWT
#        Eliminano duplicazione tra password_reset, attivazione, change_password
#        e middleware (§8.4.1).
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_constants import (
    JWT_CLAIM_EMITTENTE_ATTIVO_ID,
    JWT_CLAIM_IDENTITA_ID,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.token_service import TokenService

logger = logging.getLogger("security")


# Scopo: Cast difensivo di un valore arbitrario a int | None. Usato per
#        estrarre `identita_id` da sorgenti non tipate (claim JWT, meta
#        JSONB del token monouso): se il valore manca o ha tipo
#        incompatibile (es. dict, stringa non numerica) ritorna None
#        invece di sollevare 500. Il chiamante decide il fallback.
def _safe_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning(
            "auth_helpers._safe_int_or_none: valore non intero ignorato "
            "(type=%s)", type(value).__name__,
        )
        return None


# Scopo: Estrae `identita_id` dal JWT validato presente su `request.auth`
#        (popolato da JwtAuditAuthentication §8.3.4). Pattern condiviso da
#        middleware e view autenticate che devono puntare la veste del
#        JWT corrente. Ritorna None se:
#          - la request non ha `auth` (flussi non autenticati);
#          - il claim e' assente (token pre-§8.3.2);
#          - il claim non e' int-castabile (defensive).
def extract_identita_id_from_request(request: Any) -> int | None:
    claim = getattr(request, "auth", None)
    if claim is None:
        return None
    return _safe_int_or_none(claim.get(JWT_CLAIM_IDENTITA_ID))


# Scopo: Estrae `emittente_attivo_id` dal JWT validato — l'emittente dentro
#        cui l'utente sta lavorando in QUESTA sessione (impersonazione di
#        scope). None = modalita' «Tutti gli emittenti», o token emesso prima
#        del cantiere.
#
#        Serve a CONGELARE l'emittente nei lavori accodati: il worker esegue
#        minuti dopo, su un processo che non ha ne' il browser ne' il token, e
#        senza questo valore girerebbe come se l'utente fosse in modalita'
#        globale. Il lavoro deve fare cio' che e' stato chiesto NEL MOMENTO in
#        cui e' stato chiesto — anche se nel frattempo l'utente ha cambiato
#        emittente, o ha fatto logout.
def extract_emittente_attivo_from_request(request: Any) -> int | None:
    claim = getattr(request, "auth", None)
    if claim is None:
        return None
    return _safe_int_or_none(claim.get(JWT_CLAIM_EMITTENTE_ATTIVO_ID))


# Scopo: Estrae `identita_id` dal meta JSONB di un token monouso
#        (iniettato da InvitoOperatoreService / InvitoPortaleService
#        §8.4.1). Il meta arriva tipicamente come dict Python dal
#        TokenService.validate, ma a seconda dell'adapter psycopg (v2
#        registra il default json decoder, v3 puo' restituire jsonb come
#        str) puo' essere una stringa JSON serializzata. Gestiamo
#        entrambi i casi + fail-soft su input incoerente.
def extract_identita_id_from_token_meta(meta: Any) -> int | None:
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (ValueError, TypeError):
            return None
    if not isinstance(meta, dict):
        return None
    return _safe_int_or_none(meta.get("identita_id"))


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
# Post modello 1:N (§8.4.1) il flag `deve_cambiare_password` e' per veste
# (ogni identita_digitali ha il proprio); `identita_id` kw-only:
#   - valorizzato: reset flag solo sulla veste specifica (es. cambio
#     password autenticato tocca la veste del JWT corrente, attivazione
#     invito tocca la veste che si sta attivando).
#   - None: reset flag su tutte le identita attive dell'utente (semantica
#     corretta per password reset self-service — l'utente non ha una
#     veste corrente, sta rientrando su tutto il suo account).
def apply_new_password(
    user: User,
    new_password: str,
    *,
    identita_id: int | None = None,
    blacklist_tokens: bool = True,
    auth_repo: AuthRepository | None = None,
) -> None:
    repo = auth_repo or AuthRepository()
    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password"])
        repo.set_deve_cambiare_password(
            user.id, False, identita_id=identita_id
        )

        if blacklist_tokens:
            for ot in OutstandingToken.objects.filter(user=user):
                try:
                    RefreshToken(ot.token).blacklist()
                except TokenError:
                    logger.debug(
                        "Blacklist token fallita per user_id=%s: token gia' invalido",
                        user.id,
                    )
