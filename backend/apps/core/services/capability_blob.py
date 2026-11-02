# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il ripiego del blob capability in una funzione sola: legge il blob
#        di una `script.fn_available_actions_*` e, se il capability layer e'
#        rotto (DatabaseError: funzione assente, SQL invalido), logga e
#        ritorna `{}`. Il dettaglio esce comunque, con `capabilities` VUOTO —
#        la chiave c'e' sempre, la forma non dipende dall'esito (api.md §«Il
#        blob sta SOTTO `capabilities`») — e il frontend cade in sola
#        consultazione (fail-closed: nessuna azione, nessun campo editabile).
# Note: ⭐ Regola del 2 (2026-09-23, brief-be-fe-capability-annidata): offerte
#        e lotto avevano lo stesso `try/except DatabaseError` scritto due volte.
#        ⚠️ Il savepoint: un DatabaseError dentro un `transaction.atomic()`
#        lascia la transazione ABORTITA, e ogni query successiva del chiamante
#        fallirebbe con «current transaction is aborted» — il ripiego
#        salverebbe il dettaglio e romperebbe il resto. Dentro un blocco
#        atomico la lettura va quindi in un savepoint suo; fuori (autocommit)
#        il savepoint non serve e non si apre.
#        ⛔ Solo per il blob: un errore che non e' del capability layer (la
#        testata, le righe) deve continuare a salire.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from django.db import DatabaseError, transaction


# Scopo: `leggi()` → il blob; `{}` se il capability layer solleva.
#        `funzione` e `entita_id` servono solo al log; `logger` e' quello del
#        dominio chiamante, perche' il warning resti attribuito a lui.
def capabilities_o_vuoto(
    leggi: Callable[[], dict[str, Any]],
    *,
    funzione: str,
    entita_id: int,
    logger: logging.Logger,
) -> dict[str, Any]:
    try:
        if transaction.get_connection().in_atomic_block:
            with transaction.atomic():
                return leggi()
        return leggi()
    except DatabaseError as exc:
        logger.warning(
            "%s fallita per id=%s: %s. Dettaglio ritornato con `capabilities` "
            "vuoto (drawer in sola consultazione).",
            funzione, entita_id, exc,
        )
        return {}
