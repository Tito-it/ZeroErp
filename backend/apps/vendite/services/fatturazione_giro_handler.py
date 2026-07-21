# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler del job `FATTURAZIONE_GIRO` (coda lavori generica, C-3): il
#        giro di fatturazione on-demand richiesto dall'operatore. È il primo
#        consumatore della coda `dbops.coda_lavori`. Registrato nel registry
#        handler (`handler_code = fatturazione_giro_default`, dal seed DB) al
#        boot di `VenditeConfig.ready()`.
#
#        Contesto d'esecuzione: il drainer lo invoca DENTRO
#        `operator_identity_context` (run_as=OPERATORE) → RLS ATTIVA con
#        l'identità dell'operatore che ha accodato. La discovery
#        (`fn_list_emittibili_lane`) e l'esecuzione della pipeline sono quindi
#        **scoped all'operatore via RLS** («esegue con i permessi
#        dell'operatore», guida Gestione code di lavoro). Nessun filtro
#        emittente esplicito qui: lo scope è la RLS, non un parametro.
#
#        Invariante I-1: chiama lo STESSO core del cron
#        (`esegui_giro_fatturazione`), niente seconda implementazione. Corsia
#        `differita` (on-demand): si ferma a EMESSA (D-1); la numerazione è un
#        atto separato (C-4). Best-effort per-terna (il core non solleva su
#        terna fallita): l'esito strutturato diventa il `result` del job.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.vendite.services._fatturazione_job_helpers import parse_competenza_mese

# handler_code seedato in dbops.coda_lavori_tipi per il tipo FATTURAZIONE_GIRO.
HANDLER_CODE = "fatturazione_giro_default"

# Corsia del giro on-demand: differita → fermata di corsia a EMESSA (D-1).
_MODALITA_ONDEMAND = "differita"

# Codice errore per payload di giro malformato: fallimento di dominio parlante
# (finisce in `coda.ultimo_errore`; non è una risposta HTTP → non va in
# error_policies). Parse condiviso in _fatturazione_job_helpers (regola del 2).
E_GIRO_PAYLOAD = "E_FATTURAZIONE_GIRO_PAYLOAD"


# Scopo: Esegue il giro di fatturazione on-demand. `payload`:
#        `{competenza_mese: ISO, fino_a_stato?: codice}`. `scope`: catturato
#        all'enqueue (`{auth_user_id, emittente_ids}`) — qui NON usato per
#        filtrare (lo fa la RLS del contesto operatore), presente per il
#        vincolo DB run_as↔scope e per l'audit. Ritorna l'esito compatto del
#        giro (senza la lista per-terna) come `result` del job.
def fatturazione_giro_handler(
    payload: dict[str, Any], *, scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    competenza = parse_competenza_mese(
        payload.get("competenza_mese"), error_code=E_GIRO_PAYLOAD,
    )
    fino_a_stato = payload.get("fino_a_stato")

    # Import locale: evita di caricare la catena driver al boot del modulo
    # (registrato in ready()); il core è l'unico punto di verità I-1.
    from apps.vendite.services.fatturazione_driver_service import (
        esegui_giro_fatturazione,
    )

    kwargs: dict[str, Any] = {
        "modalita": _MODALITA_ONDEMAND,
        "competenza": competenza,
    }
    if fino_a_stato:
        kwargs["fino_a_stato"] = fino_a_stato

    summary = esegui_giro_fatturazione(**kwargs)
    # Compatta per il `result` del job (la lista per-terna gonfierebbe il jsonb;
    # il dettaglio vive nei log/task_runs, correlati via job_run).
    return {k: v for k, v in summary.items() if k != "esiti"}


# Scopo: Registra l'handler nel registry della coda. Chiamata da
#        `VenditeConfig.ready()` (import del modulo). Dispatch controllato:
#        `dbops.coda_lavori_tipi.handler_code` → questa funzione.
def register() -> None:
    from apps.core.services.coda_lavori.handler_registry import register_handler
    register_handler(HANDLER_CODE, fatturazione_giro_handler)
