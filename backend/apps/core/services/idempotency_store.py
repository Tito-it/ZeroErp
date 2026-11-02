# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Persistenza idempotency-key su dbops.idempotency_keys.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from django.db import connection, transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IdempotencyDecision:
    should_execute: bool
    replay_payload: dict[str, Any] | None = None
    in_progress: bool = False


class IdempotencyStore:
    """Store idempotenza forte: claim key, replay risposta, finalize esito."""

    # Scopo: Prenota la key e dice che cosa fare: eseguire, rimandare la
    #        risposta salvata, oppure 409 perche' un'altra richiesta la sta
    #        eseguendo.
    # ⭐ La decisione e' di `dbops.fn_idempotency_prenota` (BE-1 di
    #    brief-be-verifica-documentazione-api, 2026-10-24): fino a quel giorno
    #    stava qui, in un INSERT ... ON CONFLICT piu' un UPDATE sulle `failed`,
    #    e non conosceva ne' il legame a utente ed endpoint (D7) ne' la ripresa
    #    di una key orfana (D6). Le regole si leggono sulla funzione.
    # ⛔ `ripresa_ammessa` si passa SEMPRE: la funzione non ha un default che
    #    decida, e NULL e' `E_SCRIPT_CHIAMATA_NON_VALIDA` (§I.7.5). La decide
    #    l'unita' di lavoro dell'endpoint (`handle_post_json`), mai il chiamante
    #    di questo metodo a mano.
    # ⚠️ Gira in autocommit, FUORI dalla transazione dell'operazione: la
    #    prenotazione deve essere visibile subito alle altre richieste. Un
    #    rifiuto della funzione (`E_IDEMPOTENCY_KEY_RIUSATA`, 400) risale come
    #    ogni errore di dominio del database.
    @staticmethod
    def claim_or_replay(
        *,
        idempotency_key: str,
        request_id: str | None,
        auth_user_id: int | None,
        endpoint: str,
        ripresa_ammessa: bool,
    ) -> IdempotencyDecision:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT esito, response_payload
                FROM dbops.fn_idempotency_prenota(%s, %s, %s, %s::uuid, %s)
                """,
                [idempotency_key, auth_user_id, endpoint, request_id, ripresa_ammessa],
            )
            row = cursor.fetchone()
        esito, response_payload = row if row is not None else (None, None)
        if esito == "ESEGUI":
            return IdempotencyDecision(should_execute=True)
        if esito == "REPLAY":
            payload = IdempotencyStore._normalize_response_payload(response_payload)
            # ⛔ Un REPLAY senza una risposta leggibile non si esegue di nuovo:
            #    l'operazione E' stata fatta. Rieseguirla sarebbe il doppione che
            #    la key esiste per impedire.
            if payload is None:
                raise RuntimeError(
                    f"idempotency: REPLAY senza risposta leggibile per la key {idempotency_key}"
                )
            return IdempotencyDecision(should_execute=False, replay_payload=payload)
        if esito == "IN_CORSO":
            return IdempotencyDecision(should_execute=False, in_progress=True)
        # Un esito fuori dai tre e' un contratto rotto con la funzione: si dice.
        raise RuntimeError(f"idempotency: esito di fn_idempotency_prenota non previsto: {esito!r}")

    # Scopo: La soglia di ripresa in secondi, letta e validata dal database.
    # ⭐ Sede unica della regola: `dbops.fn_idempotency_soglia_secondi` (§I.11 di
    #    brief-be-verifica-documentazione-api, 2026-10-24), la stessa che usa
    #    `fn_idempotency_prenota`. Fino a quel giorno il backend ricopiava la
    #    regex del parametro, e una copia aveva gia' divergito (lo `strip`).
    #    Una soglia rotta e' `E_CONFIG_MANCANTE` sollevato dalla funzione.
    @staticmethod
    def soglia_ripresa_secondi() -> int:
        with connection.cursor() as cursor:
            cursor.execute("SELECT dbops.fn_idempotency_soglia_secondi()")
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

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
        # ⚠️ Savepoint: dentro la transazione di un'operazione ATOMICA
        #    (`handle_post_json`) una SELECT fallita senza savepoint
        #    abortirebbe la transazione, e l'`except` qui sotto non la
        #    riaprirebbe: l'UPDATE a `completed` subito dopo fallirebbe.
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("SELECT dbops.fn_get_or_create_session_tx_id()")
                row = cursor.fetchone()
                if row is not None and row[0] is not None:
                    value = row[0]
                    if isinstance(value, UUID):
                        return value
                    return UUID(str(value))
        except Exception:
            # Il ripiego resta, ma non muto: un tx_id applicativo scollega la
            # chiave dalla transazione DB, e senza questa riga non lo saprebbe
            # nessuno.
            logger.warning("idempotency.tx_id_db_non_disponibile", exc_info=True)

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
