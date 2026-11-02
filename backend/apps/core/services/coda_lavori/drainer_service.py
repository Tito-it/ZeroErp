# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Core del worker DRAINER della coda lavori generica (`dbops.coda_lavori`).
#        Cabla il motore condiviso `QueueDrainEngine` sul backend
#        `CodaLavoriRepository` con un `per_item` che dispatcha per
#        `handler_code` e imposta il CONTESTO DI ESECUZIONE secondo `run_as`:
#         - `SISTEMA`  → ruolo applicativo normale, `scope=None`: nessuna
#           identita' e nessun emittente, quindi solo tabelle senza perimetro;
#         - `OPERATORE`→ `operator_identity_context` (RLS attiva, 5 GUC =
#           identità completa dell'operatore che ha accodato, dallo scope
#           catturato: auth_user_id+username+identita_id). Nessuna interruzione
#           a metà (brief DB §3a): la revoca permessi vale per i job futuri,
#           non per l'IN_CORSO (ma un'identità revocata PRIMA del claim
#           fail-louda nel context: niente esecuzione con RLS a 0 righe).
#        È il CORE unico (I-1): il command `draina_coda_lavori` ne è un
#        chiamante sottile (argparse + registered_job + output).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.coda_lavori.backend import QueueItem
from apps.core.services.coda_lavori.context import operator_identity_context
from apps.core.services.coda_lavori.drain_engine import QueueDrainEngine
from apps.core.services.coda_lavori.handler_registry import get_handler
from apps.core.services.coda_lavori.repository import (
    RUN_AS_SISTEMA,
    STALE_MINUTI_DEFAULT,
    CodaLavoriRepository,
)
# Righe claimate per giro (batch unico misto per priorità). Tarabile su volumi.
_LIMIT_DEFAULT = 200
# Reaper: righe IN_CORSO stantie oltre N minuti (worker morto): tentativi+1 →
# PENDING, o ERRORE terminale oltre soglia (anti poison-job). Fonte unica in
# repository (STALE_MINUTI_DEFAULT): stessa definizione di «stantio» del
# requeue manuale della UI code.
_STALE_MINUTI_DEFAULT = STALE_MINUTI_DEFAULT


# Scopo: Esegue un work-item nel contesto giusto secondo `run_as`, risolvendo
#        l'handler dal registry (dispatch controllato). Ritorna il `result` del
#        job (persistito dal motore su FATTO). Solleva su handler mancante o
#        fallimento di dominio (il motore traduce in ERRORE/retry).
def _dispatch_item(item: QueueItem) -> dict[str, Any] | None:
    handler = get_handler(item.raw.get("handler_code"))
    if item.run_as == RUN_AS_SISTEMA:
        # ⭐ `SISTEMA` ha cambiato SIGNIFICATO (2026-09-05, §10.2 dell'analisi).
        #    Voleva dire «col bypass della RLS»; adesso vuole dire «senza
        #    emittente». Il job gira sul ruolo applicativo normale, quindi puo'
        #    toccare solo cio' che non ha un perimetro — ed e' esattamente cio'
        #    che un lavoro senza azienda deve poter fare.
        # ⛔ Niente canale di sistema: era l'ultimo punto del backend che lo
        #    apriva, e finche' esisteva bastava un tipo di coda dichiarato male
        #    per attraversare tutte le aziende.
        # ⚠️ Nessun tipo `SISTEMA` e' seedato oggi (i due esistenti sono
        #    `DOMINIO`/`OPERATORE`), e dal 2026-09-04 il guard di classe di
        #    `fn_accoda_lavoro` impedisce di accodare un lavoro di dominio come
        #    `SISTEMA`: il ramo vincola il futuro, non rompe il presente.
        return handler(item.payload, scope=None)
    # OPERATORE: RLS attiva con l'identità COMPLETA dell'operatore (5 GUC,
    # stessa risoluzione del web) dallo scope catturato all'enqueue.
    scope = item.scope or {}
    with operator_identity_context(
        scope.get("auth_user_id"),
        username=scope.get("username"),
        identita_id=scope.get("identita_id"),
        # Congelato all'enqueue (chiave assente sui job accodati prima del
        # cantiere impersonazione → None → comportamento storico).
        emittente_attivo_id=scope.get("emittente_attivo_id"),
    ):
        return handler(item.payload, scope=item.scope)


# Scopo: Drena la coda generica un giro. Wrapper sottile sul `QueueDrainEngine`
#        (che possiede reaper→claim→per-item→retry/backoff) col dispatch per
#        `run_as`. `backend`/`per_item` iniettabili per i test.
def draina_coda_lavori(
    *,
    limit: int = _LIMIT_DEFAULT,
    stale_minuti: int = _STALE_MINUTI_DEFAULT,
    job_run_id: int | None = None,
    on_item_esito=None,
    backend: CodaLavoriRepository | None = None,
    per_item=None,
) -> dict[str, Any]:
    # `job_run_id` (dal registered_job del command) timbrato sui job claimati
    # → tracciabilità job↔passata (guida Tracciamento). Backend iniettato nei
    # test (job_run_id ignorato lì).
    backend = backend or CodaLavoriRepository(job_run_id=job_run_id)
    engine = QueueDrainEngine(backend, per_item=per_item or _dispatch_item)
    return engine.drain(
        limit=limit, stale_minuti=stale_minuti, on_item_esito=on_item_esito,
    )
