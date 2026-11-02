# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio token monouso generico — generazione, validazione, consumo.
#        Riutilizzabile per inviti, reset password, conferme email.
#        Il token in chiaro viene ritornato una sola volta al momento
#        della creazione. In DB si salva solo l'hash SHA-256.
# ------------------------------------------------------------

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from apps.core.db.token_repository import TokenRepository
from apps.core.services.error_manager import ErrorManager

E_TOKEN = "E_TOKEN"  # noqa: S105 — codice errore, non un segreto


class TokenService:
    """Gestione token monouso: create, validate, consume, invalidate."""

    def __init__(self) -> None:
        self._repo = TokenRepository()

    # Scopo: Genera un token casuale e ne salva l'hash SHA-256 in DB.
    #        ⚠️ NON invalida i token precedenti: lo fa il chiamante, nella
    #        stessa transazione (invalidate_all per tipo e credenziale,
    #        invalidate_for_identita per una veste).
    #        Ritorna il token in chiaro (unica volta — non recuperabile).
    def create(
        self,
        *,
        tipo: str,
        auth_user_id: int,
        scadenza_ore: int = 24,
        meta: dict[str, Any] | None = None,
    ) -> str:
        # Genera 32 bytes casuali → 64 caratteri hex
        token_plain = secrets.token_hex(32)
        token_hash = self._hash(token_plain)

        scadenza = datetime.now(timezone.utc) + timedelta(hours=scadenza_ore)

        self._repo.create(
            token_hash=token_hash,
            tipo=tipo,
            auth_user_id=auth_user_id,
            scadenza_iso=scadenza.isoformat(),
            meta=meta,
        )

        return token_plain

    # Scopo: Valida un token senza consumarlo. Ritorna (auth_user_id, meta) o None.
    def validate(self, token: str, tipo: str) -> tuple[int, dict[str, Any]] | None:
        token_hash = self._hash(token)
        row = self._repo.find_valid(token_hash, tipo)
        if not row:
            return None
        return row["auth_user_id"], row.get("meta") or {}

    # Scopo: Consuma un token (segna come utilizzato). Ritorna auth_user_id.
    #        Lancia ServiceError se il token non e' valido.
    def consume(self, token: str, tipo: str, ip: str | None = None) -> int:
        token_hash = self._hash(token)
        row = self._repo.find_valid(token_hash, tipo)
        ErrorManager.require(
            row is not None,
            code=E_TOKEN,
            message="Token non valido, scaduto o gia' utilizzato.",
        )
        assert row is not None

        consumed = self._repo.consume(row["id"], ip=ip)
        ErrorManager.require(consumed, code=E_TOKEN, message="Impossibile consumare il token.")

        return row["auth_user_id"]

    # Scopo: Invalida tutti i token di un tipo per un utente.
    def invalidate_all(self, tipo: str, auth_user_id: int) -> int:
        return self._repo.invalidate_all(tipo, auth_user_id)

    # Scopo: Invalida i token pendenti di una sola veste (tipi della porta +
    # `identita_id` nel meta). Vedi TokenRepository.invalidate_for_identita.
    def invalidate_for_identita(
        self, tipi: tuple[str, ...], auth_user_id: int, identita_id: int
    ) -> int:
        return self._repo.invalidate_for_identita(list(tipi), auth_user_id, identita_id)

    # Scopo: Calcola SHA-256 di un token in chiaro.
    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
