# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Contratto `QueueBackend` + `QueueItem` per il motore di drenaggio
#        condiviso (`QueueDrainEngine`). L'astrazione anti-duplicazione vive al
#        layer Python (design §4a): il LOOP di drenaggio è uno solo
#        (`QueueDrainEngine`), ogni coda fornisce un backend con il PROPRIO SQL
#        tipizzato (claim/reaper/marca), zero SQL dinamico e zero perdita di FK.
#        `dbops.coda_lavori` (coda generica) e — a convergenza — `fatture_stampa_coda`
#        (outbox stampa) implementano entrambe questo protocollo.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


# Scopo: Work-item claimato dalla coda, forma minima di cui il motore ha
#        bisogno per la policy retry/backoff + il dispatch. `payload`/`scope`
#        sono opachi al motore (li interpreta l'handler). `run_as`/`scope`
#        governano il contesto di esecuzione (SISTEMA senza emittente vs OPERATORE
#        con scope catturato). Il backend può portare campi extra nel dict
#        `raw` (colonne specifiche della sua tabella) senza gonfiare il contratto.
@dataclass(frozen=True)
class QueueItem:
    id: int
    job_type: str
    payload: dict[str, Any]
    run_as: str
    scope: dict[str, Any] | None
    tentativi: int
    max_tentativi: int
    raw: dict[str, Any] = field(default_factory=dict)


class QueueBackend(Protocol):
    """Contratto SQL-tipizzato di una coda drenabile dal `QueueDrainEngine`.

    Il motore possiede la POLICY (loop, retry/backoff, priorità); il backend
    possiede l'SQL per la PROPRIA tabella. Le transizioni di stato (design
    brief DB §3a) sono: claim `PENDING→IN_CORSO` (SKIP LOCKED), `mark_done`
    `→FATTO`, `mark_error` `→ERRORE` (terminale) o `→PENDING` con `run_after`
    (retry con backoff), `reap_stale` `IN_CORSO stantio→PENDING` (o `→ERRORE`
    oltre soglia tentativi — il recupero consuma un tentativo, anti poison-job).
    """

    # Scopo: righe IN_CORSO più vecchie di `stale_minuti` (worker morto):
    #        tentativi+1, poi → PENDING o → ERRORE terminale oltre soglia.
    def reap_stale(self, *, stale_minuti: int) -> int: ...

    # Scopo: claim atomico di ≤ limit work-item eleggibili (FOR UPDATE SKIP
    #        LOCKED + flip a IN_CORSO). Batch misto per priorità.
    def claim(self, *, limit: int) -> list[QueueItem]: ...

    # Scopo: marca l'item completato col result (→FATTO).
    def mark_done(self, item_id: int, *, result: dict[str, Any]) -> None: ...

    # Scopo: registra il fallimento. `retry_after_secondi=None` → ERRORE
    #        terminale; valore int → PENDING con `run_after = now()+intervallo`
    #        (backoff deciso dal motore, applicato col clock DB).
    def mark_error(
        self,
        item_id: int,
        *,
        errore: dict[str, Any],
        retry_after_secondi: int | None,
    ) -> None: ...
