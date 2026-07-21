# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi dei job handler della coda fatturazione
#        (FATTURAZIONE_GIRO C-3, FATTURAZIONE_NUMERA C-4). Estrazione regola
#        del 2 (ok Tid 2026-07-21): `_parse_competenza` era duplicata nei due
#        handler, identica salvo il codice errore — qui parametrizzato.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from apps.core.services.error_manager import ErrorManager, ServiceError


# Scopo: Normalizza `competenza_mese` (ISO YYYY-MM-DD) al 1° del mese. Errore
#        parlante col codice del job chiamante su valore mancante/invalido
#        (fallimento di dominio registrato in `ultimo_errore`, non eccezione
#        generica — guida Tracciamento).
def parse_competenza_mese(raw: Any, *, error_code: str) -> date:
    ErrorManager.require(
        bool(raw),
        code=error_code,
        message="Payload senza `competenza_mese`.",
    )
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date().replace(day=1)
    except ValueError as exc:
        raise ServiceError(
            code=error_code,
            message="`competenza_mese` non valida (atteso YYYY-MM-DD).",
            detail=str(raw),
        ) from exc
