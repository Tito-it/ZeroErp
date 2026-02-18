# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Persistenza idempotency-key su dbops.idempotency_keys.
# ------------------------------------------------------------

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from django.db import connection


@dataclass(frozen=True)
class IdempotencyDecision:
    should_execute: bool
    replay_payload: dict[str, Any] | None = None
    in_progress: bool = False


class IdempotencyStore:
    """Store idempotenza forte: claim key, replay risposta, finalize esito."""

    # Scopo: Gestisce claim idempotency-key e restituisce replay/in-progress in base allo stato esistente.
    @staticmethod
    def claim_or_replay(*, idempotency_key: str, request_id: str | None) -> IdempotencyDecision:
        with connection.cursor() as cursor:
            # Primo tentativo: claim atomico della chiave.
            cursor.execute(
                """
                INSERT INTO dbops.idempotency_keys (
                    idempotency_key, request_id, status
                )
                VALUES (%s, %s::uuid, 'in_progress')
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING idempotency_key
                """,
                [idempotency_key, request_id],
            )
            row = cursor.fetchone()
            if row is not None:
                return IdempotencyDecision(should_execute=True)

            # Chiave gia` presente: decidi replay / in-progress / retry dopo failed.
            cursor.execute(
                """
                SELECT status, response_payload
                FROM dbops.idempotency_keys
                WHERE idempotency_key = %s
                """,
                [idempotency_key],
            )
            row = cursor.fetchone()
            if row is None:
                # Fallback difensivo in caso di race non prevista.
                return IdempotencyDecision(should_execute=True)

            status, response_payload = row
            normalized_payload = IdempotencyStore._normalize_response_payload(response_payload)
            if status == "completed" and normalized_payload is not None:
                return IdempotencyDecision(should_execute=False, replay_payload=normalized_payload)
            if status == "in_progress":
                return IdempotencyDecision(should_execute=False, in_progress=True)

            # Stato failed: consenti nuova esecuzione ri-claimando la chiave.
            cursor.execute(
                """
                UPDATE dbops.idempotency_keys
                SET
                    status = 'in_progress',
                    request_id = %s::uuid,
                    tx_id = NULL,
                    response_payload = NULL,
                    data_update = now(),
                    user_update = CURRENT_USER
                WHERE idempotency_key = %s
                  AND status = 'failed'
                RETURNING idempotency_key
                """,
                [request_id, idempotency_key],
            )
            row = cursor.fetchone()
            if row is not None:
                return IdempotencyDecision(should_execute=True)

        return IdempotencyDecision(should_execute=False, in_progress=True)

    # Scopo: Marca la richiesta idempotente come completata persistendo la response serializzata.
    @staticmethod
    def mark_completed(
        *,
        idempotency_key: str,
        response_payload: dict[str, Any],
        request_id: str | None,
    ) -> None:
        tx_id = IdempotencyStore._resolve_tx_id(request_id)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE dbops.idempotency_keys
                SET
                    status = 'completed',
                    request_id = %s::uuid,
                    tx_id = %s::uuid,
                    response_payload = %s::jsonb,
                    data_update = now(),
                    user_update = CURRENT_USER
                WHERE idempotency_key = %s
                """,
                [request_id, str(tx_id), json.dumps(response_payload), idempotency_key],
            )

    # Scopo: Marca la richiesta idempotente come fallita senza perdere tracciabilita dello stato.
    @staticmethod
    def mark_failed(*, idempotency_key: str, request_id: str | None) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE dbops.idempotency_keys
                SET
                    status = 'failed',
                    request_id = %s::uuid,
                    tx_id = NULL,
                    response_payload = NULL,
                    data_update = now(),
                    user_update = CURRENT_USER
                WHERE idempotency_key = %s
                """,
                [request_id, idempotency_key],
            )

    # Scopo: Risolve il tx_id da contesto richiesta o da fallback per persistenza idempotency.
    @staticmethod
    def _resolve_tx_id(request_id: str | None) -> UUID:
        # Prova ad agganciarsi al tx_id DB; fallback su UUID applicativo.
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT dbops.fn_get_or_create_session_tx_id()")
                row = cursor.fetchone()
                if row is not None and row[0] is not None:
                    value = row[0]
                    if isinstance(value, UUID):
                        return value
                    return UUID(str(value))
        except Exception:
            pass

        if request_id:
            try:
                return UUID(request_id)
            except ValueError:
                pass
        return uuid4()

    # Scopo: Normalizza payload response in JSON serializzabile prima della persistenza idempotency.
    @staticmethod
    def _normalize_response_payload(raw_payload: Any) -> dict[str, Any] | None:
        if isinstance(raw_payload, dict):
            return raw_payload
        if isinstance(raw_payload, str):
            try:
                parsed = json.loads(raw_payload)
                if isinstance(parsed, dict):
                    return parsed
            except ValueError:
                return None
        return None
