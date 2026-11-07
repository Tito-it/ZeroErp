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
#
#        ⭐ DAL 2026-11-07 (BE10, brief-db-revisione-dbops §5 e §18) IL
#        DRENATORE LAVORA UN'AZIENDA ALLA VOLTA, come quello della stampa: il
#        giro completo (`draina_coda_lavori_per_roster`) passa per il BB
#        `giro_per_azienda` e chiama il core una volta per utente tecnico di
#        `draina_coda_lavori`. Reaper, claim e `mark_*` girano con quella
#        identità: con la coda sotto RLS (blocco 5b) il badge vede i lavori
#        OPERATORE della sua azienda e i lavori SISTEMA, che `SKIP LOCKED` dà
#        a uno solo. L'ESECUZIONE di un lavoro resta con l'identità del suo
#        scope, dentro la parentesi del contesto, che all'uscita rimette quella
#        del badge.
#        ⛔ Un'azienda senza utente tecnico non viene drenata, e il giro lo
#        dice (`emittenti_non_serviti`). Nessun ramo che veda tutte le aziende
#        (decisione 1 di Tid, §18.1): è la porta che R-2 ha chiuso.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.coda_lavori.backend import QueueItem
from apps.core.services.coda_lavori.context import (
    operator_identity_context,
    senza_identita_context,
)
from apps.core.services.coda_lavori.drain_engine import QueueDrainEngine
from apps.core.services.coda_lavori.handler_registry import get_handler
from apps.core.services.coda_lavori.repository import (
    RUN_AS_SISTEMA,
    STALE_MINUTI_DEFAULT,
    CodaLavoriRepository,
)
from apps.core.services.giro_per_azienda import giro_per_azienda
from apps.core.services.processi import PROCESSO_DRAINA_CODA_LAVORI

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
        # ⛔ SENZA identità, anche se il giro gira con quella di un utente
        #    tecnico (BE10): un lavoro SISTEMA non ha azienda, e col badge
        #    addosso lavorerebbe col perimetro di quella. All'uscita il
        #    contesto rimette il badge, per la `mark_*` che segue.
        with senza_identita_context():
            return handler(item.payload, scope=None)
    # OPERATORE: RLS attiva con l'identità COMPLETA dell'operatore (5 GUC,
    # stessa risoluzione del web) dallo scope catturato all'enqueue. Il
    # contesto, uscendo, rimette l'identità del badge (non la azzera): senza,
    # la `mark_done` sotto RLS aggiornerebbe zero righe senza dirlo.
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


# I contatori che il giro completo somma azienda per azienda. Sede unica:
# aggiungerne uno qui lo fa comparire nell'esito senza toccare il ciclo.
_CHIAVI_AGGREGATE = ("recuperate", "claimate", "fatto", "errore", "riprovabili")


# Scopo: IL GIRO COMPLETO — drena la coda per OGNI azienda servita dal
#        processo `draina_coda_lavori`, una alla volta, con l'identità del suo
#        utente tecnico (BB `giro_per_azienda`). Aggrega gli esiti.
#        Un solo repository per tutto il giro: lo stesso `job_run_id` timbra i
#        lavori presi da ogni badge, e la `mark_*` lo pretende uguale.
# ⚠️ ROSTER VUOTO = NIENTE DRENATO, nemmeno i lavori SISTEMA: li vede solo un
#    utente tecnico del drenatore. L'esito lo dice (`roster_vuoto`), e il
#    command lo scrive per primo.
def draina_coda_lavori_per_roster(
    *,
    limit: int = _LIMIT_DEFAULT,
    stale_minuti: int = _STALE_MINUTI_DEFAULT,
    job_run_id: int | None = None,
    on_item_esito=None,
    on_emittente_esito: Callable[[Mapping[str, Any], dict[str, Any] | None, Exception | None], None] | None = None,
    processi_repo: ProcessiRepository | None = None,
    backend: CodaLavoriRepository | None = None,
    per_item=None,
) -> dict[str, Any]:
    backend = backend or CodaLavoriRepository(job_run_id=job_run_id)

    # Scopo: il lavoro di UN badge, gia' dentro la sua identita'.
    def _drena(badge: Mapping[str, Any]) -> dict[str, Any]:
        esito = draina_coda_lavori(
            limit=limit, stale_minuti=stale_minuti,
            on_item_esito=on_item_esito, backend=backend, per_item=per_item,
        )
        esito["emittente_codice"] = badge["emittente_codice"]
        return esito

    giro = giro_per_azienda(
        PROCESSO_DRAINA_CODA_LAVORI,
        _drena,
        evento="coda_lavori",
        on_badge=on_emittente_esito,
        processi_repo=processi_repo,
    )
    per_emittente = [esito for _badge, esito in giro.serviti]
    totali = {
        chiave: sum(esito.get(chiave, 0) for esito in per_emittente)
        for chiave in _CHIAVI_AGGREGATE
    }
    return {
        **totali,
        "emittenti_serviti": len(per_emittente),
        "emittenti_falliti": giro.falliti,
        "emittenti_non_serviti": giro.non_serviti,
        "roster_vuoto": giro.roster_vuoto,
        "limit": limit,
        "per_emittente": per_emittente,
    }
