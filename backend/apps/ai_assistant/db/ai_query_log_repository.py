# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per la tabella dbops.ai_query_log.
#        Gestisce il salvataggio delle interazioni AI.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
from typing import Any

from django.db import connection

logger = logging.getLogger(__name__)


class AIQueryLogRepository:
    """Accesso alla tabella dbops.ai_query_log."""

    # Scopo: Salva un record di log per un'interazione AI completata.
    #        Append-only, nessun update previsto.
    def save_query_log(
        self,
        *,
        request_id: str,
        user_id: int,
        input_text: str,
        tools_called: list[dict[str, Any]] | None,
        response_text: str | None,
        provider: str,
        model: str,
        tokens_input: int | None,
        tokens_output: int | None,
        duration_ms: int | None,
        error_code: str | None,
        reliable: bool = False,
    ) -> None:
        sql = """
            INSERT INTO dbops.ai_query_log (
                request_id, user_id, input_text, tools_called,
                response_text, provider, model,
                tokens_input, tokens_output, duration_ms, error_code
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s
            )
        """
        tools_json = json.dumps(tools_called) if tools_called else None

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, [
                    request_id,
                    user_id,
                    input_text,
                    tools_json,
                    response_text,
                    provider,
                    model,
                    tokens_input,
                    tokens_output,
                    duration_ms,
                    error_code,
                ])
        except Exception:
            # Il logging non deve mai bloccare la risposta all'utente.
            # Ma per le operazioni delicate (scritture confermate, MCP/supporto)
            # l'audit e' anche il sistema di rilevamento anomalie: un fallimento
            # va emesso a livello ERROR (alert), non solo WARNING.
            if reliable:
                logger.exception(
                    "AUDIT FALLITO su ai_query_log per operazione affidabile "
                    "(request_id=%s): traccia mancante per operazione confermata/privilegiata.",
                    request_id,
                )
            else:
                logger.warning(
                    "Errore salvataggio ai_query_log per request_id=%s",
                    request_id,
                    exc_info=True,
                )
