# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `CodaLavoriRepository` — accesso DB alla coda generica
#        `dbops.coda_lavori`. Implementa il protocollo `QueueBackend` (SQL
#        tipizzato di claim/reaper/marca per QUESTA tabella) + enqueue (delega
#        a `dbops.fn_accoda_lavoro`, atomico e idempotente sui job vivi) +
#        operazioni amministrative (cancel/requeue) e di monitoraggio
#        (count/get_stato). Le transizioni di stato seguono il design brief DB
#        §3a. La tabella ha i trigger audit (`data_update`/`user_update`
#        automatici) → gli UPDATE NON li settano a mano.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from .backend import QueueItem

# Origini di accodamento (CHECK chk_coda_lavori_origine). Chi ha ACCODATO
# (distinto da chi esegue il run, in job_run_log).
ORIGINE_API = "API"
ORIGINE_CRON = "CRON"
ORIGINE_COMMAND = "COMMAND"
ORIGINE_TRIGGER = "TRIGGER"

# Modalità di esecuzione (CHECK chk_coda_lavori_run_as + chk_..._run_as_scope).
RUN_AS_SISTEMA = "SISTEMA"
RUN_AS_OPERATORE = "OPERATORE"


class CodaLavoriRepository:
    """Backend `dbops.coda_lavori` per il `QueueDrainEngine` + enqueue/admin.

    `job_run_id` (opzionale): id del run `maintenance.job_run_log` del worker
    corrente. Se valorizzato, il `claim` lo timbra sui job presi in carico →
    «ogni lavoro conserva il collegamento alla passata che lo ha eseguito»
    (guida Tracciamento processi e job). None fuori da un run (es. test/enqueue).
    """

    # Scopo: Inizializza il backend, opzionalmente legato al run del worker.
    def __init__(self, *, job_run_id: int | None = None) -> None:
        self._job_run_id = job_run_id

    # ══════════════════════════════════════════════════════════
    #  ENQUEUE — delega alla funzione DB atomica/idempotente
    # ══════════════════════════════════════════════════════════

    # Scopo: Accoda un lavoro (transazionale). Delega a `dbops.fn_accoda_lavoro`:
    #        guard job_type attivo, default run_as/max_tentativi dal tipo,
    #        idempotenza sui job VIVI per `(job_type, idempotency_key)` (2ª
    #        chiamata viva → stesso id, nessun doppione). ⚠️ `idempotency_key` è
    #        la chiave di BUSINESS del job (es. competenza+scope), NON l'header
    #        HTTP `Idempotency-Key` (idempotenza a due layer, brief DB Q-E).
    #        ⚠️ CHECK run_as↔scope: OPERATORE richiede scope non-null; SISTEMA
    #        richiede scope null (guard applicativo qui per errore parlante).
    def accoda(
        self,
        *,
        job_type: str,
        payload: dict[str, Any] | None = None,
        run_as: str | None = None,
        scope: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        priorita: int = 100,
        run_after: Any = None,
        max_tentativi: int | None = None,
        origine: str = ORIGINE_API,
    ) -> int:
        sql = """
            SELECT dbops.fn_accoda_lavoro(
                %s, %s::jsonb, %s, %s::jsonb, %s, %s::smallint, %s, %s, %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                job_type,
                json.dumps(payload or {}),
                run_as,
                json.dumps(scope) if scope is not None else None,
                idempotency_key,
                priorita,
                run_after,
                max_tentativi,
                origine,
            ])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # ══════════════════════════════════════════════════════════
    #  QueueBackend — claim / reaper / marca (SQL tipizzato)
    # ══════════════════════════════════════════════════════════

    # Scopo: Reaper delle righe IN_CORSO stantie (worker morto oltre
    #        `stale_minuti`). `claimed_at` è il timestamp autoritativo.
    #        Ogni recupero INCREMENTA `tentativi` (l'esecuzione interrotta È
    #        un tentativo consumato): un poison-job che uccide il worker — e
    #        che quindi non passa mai da `mark_error` — non può ciclare
    #        all'infinito: oltre `max_tentativi` → ERRORE terminale (con
    #        `ultimo_errore` parlante), altrimenti → PENDING ri-eleggibile.
    #        Servito dall'indice `ix_coda_lavori_da_lavorare` (include IN_CORSO).
    def reap_stale(self, *, stale_minuti: int) -> int:
        errore_json = json.dumps({
            "code": "E_CODA_JOB_STANTIO",
            "message": (
                "Esecuzione interrotta (worker morto o kill): "
                "recuperata dal reaper."
            ),
        })
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE dbops.coda_lavori
                   SET tentativi = tentativi + 1,
                       ultimo_errore = %s::jsonb,
                       claimed_at = NULL,
                       stato = CASE
                                 WHEN tentativi + 1 >= max_tentativi
                                 THEN 'ERRORE' ELSE 'PENDING'
                               END,
                       ended_at = CASE
                                    WHEN tentativi + 1 >= max_tentativi
                                    THEN now() ELSE ended_at
                                  END
                 WHERE stato = 'IN_CORSO'
                   AND claimed_at < now() - make_interval(mins => %s)
                """,
                [errore_json, int(stale_minuti)],
            )
            return cursor.rowcount

    # Scopo: Claim atomico di ≤ `limit` work-item ELEGGIBILI (PENDING e
    #        `run_after` scaduto), batch MISTO per priorità (`ORDER BY priorita,
    #        id`) così un tipo lungo non affama gli altri. `FOR UPDATE SKIP
    #        LOCKED` → più worker paralleli non si pestano; flip a IN_CORSO +
    #        `claimed_at`/`started_at` nella stessa istruzione. JOIN al registry
    #        per l'`handler_code` (autoritativo dal DB config). Il lavoro
    #        avviene FUORI da qui (nessun lock tenuto durante l'esecuzione).
    def claim(self, *, limit: int) -> list[QueueItem]:
        safe_limit = max(1, int(limit))
        sql = """
            WITH claimed AS (
                SELECT id
                  FROM dbops.coda_lavori
                 WHERE stato = 'PENDING'
                   AND (run_after IS NULL OR run_after <= now())
                 ORDER BY priorita, id
                 FOR UPDATE SKIP LOCKED
                 LIMIT %s
            )
            UPDATE dbops.coda_lavori c
               SET stato = 'IN_CORSO', claimed_at = now(), started_at = now(),
                   job_run_id = %s
              FROM claimed, dbops.coda_lavori_tipi t
             WHERE c.id = claimed.id
               AND t.codice = c.job_type
            RETURNING c.id, c.job_type, c.payload, c.run_as, c.scope,
                      c.tentativi, c.max_tentativi, t.handler_code
        """
        with connection.cursor() as cursor:
            # Param order: LIMIT (nella CTE) poi job_run_id (nella SET).
            cursor.execute(sql, [safe_limit, self._job_run_id])
            rows = cursor.fetchall()
        return [
            QueueItem(
                id=int(r[0]),
                job_type=str(r[1]),
                payload=r[2] or {},
                run_as=str(r[3]),
                scope=r[4],
                tentativi=int(r[5]),
                max_tentativi=int(r[6]),
                raw={"handler_code": r[7]},
            )
            for r in rows
        ]

    # Scopo: Marca l'item completato (→FATTO) col result; azzera l'errore.
    def mark_done(self, item_id: int, *, result: dict[str, Any]) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE dbops.coda_lavori
                   SET stato = 'FATTO', result = %s::jsonb,
                       ultimo_errore = NULL, ended_at = now()
                 WHERE id = %s
                """,
                [json.dumps(result, default=str), int(item_id)],
            )

    # Scopo: Registra il fallimento. `retry_after_secondi=None` → ERRORE
    #        terminale; int → PENDING con `run_after = now()+intervallo`
    #        (backoff col clock DB) e `claimed_at` azzerato (ri-eleggibile).
    #        `tentativi` sempre incrementato (storia preservata).
    def mark_error(
        self,
        item_id: int,
        *,
        errore: dict[str, Any],
        retry_after_secondi: int | None,
    ) -> None:
        errore_json = json.dumps(errore, default=str)
        with connection.cursor() as cursor:
            if retry_after_secondi is None:
                cursor.execute(
                    """
                    UPDATE dbops.coda_lavori
                       SET stato = 'ERRORE', tentativi = tentativi + 1,
                           ultimo_errore = %s::jsonb, ended_at = now()
                     WHERE id = %s
                    """,
                    [errore_json, int(item_id)],
                )
            else:
                cursor.execute(
                    """
                    UPDATE dbops.coda_lavori
                       SET stato = 'PENDING', tentativi = tentativi + 1,
                           ultimo_errore = %s::jsonb,
                           run_after = now() + make_interval(secs => %s),
                           claimed_at = NULL
                     WHERE id = %s
                    """,
                    [errore_json, int(retry_after_secondi), int(item_id)],
                )

    # ══════════════════════════════════════════════════════════
    #  ADMIN / MONITORAGGIO
    # ══════════════════════════════════════════════════════════

    # Scopo: Annulla un job SOLO se ancora PENDING → ANNULLATO (0 righe se già
    #        claimato: nessuna race col worker). Ritorna True se annullato.
    #        `owner_scope_key`: enforcement ownership (agisce solo sui job della
    #        propria `scope_key`; None = qualunque job, per l'admin `code_manage`).
    #        Job fuori scope → 0 righe, indistinguibile da inesistente (no leak).
    def annulla(self, item_id: int, *, owner_scope_key: str | None = None) -> bool:
        conditions = ["id = %s", "stato = 'PENDING'"]
        params: list[Any] = [int(item_id)]
        if owner_scope_key is not None:
            conditions.append("scope->>'scope_key' = %s")
            params.append(str(owner_scope_key))
        where = " AND ".join(conditions)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE dbops.coda_lavori
                   SET stato = 'ANNULLATO'
                 WHERE {where}
                """,  # noqa: S608 — where da condizioni whitelisted
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Sblocco manuale (requeue admin) di un job bloccato IN_CORSO o
    #        ERRORE terminale → PENDING. `tentativi` si MANTIENE (storia dei
    #        fallimenti preservata) e si alza `max_tentativi += extra_tentativi`
    #        per consentire i nuovi tentativi (brief DB §3a). Ritorna True se
    #        rimesso in coda. `owner_scope_key`: enforcement ownership (None =
    #        qualunque job, per l'admin `code_manage`); fuori scope → 0 righe.
    def requeue(
        self,
        item_id: int,
        *,
        extra_tentativi: int = 3,
        owner_scope_key: str | None = None,
    ) -> bool:
        conditions = ["id = %s", "stato IN ('IN_CORSO', 'ERRORE')"]
        params: list[Any] = [int(item_id)]
        if owner_scope_key is not None:
            conditions.append("scope->>'scope_key' = %s")
            params.append(str(owner_scope_key))
        where = " AND ".join(conditions)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE dbops.coda_lavori
                   SET stato = 'PENDING',
                       max_tentativi = max_tentativi + %s,
                       claimed_at = NULL, run_after = NULL
                 WHERE {where}
                """,  # noqa: S608 — where da condizioni whitelisted
                [int(extra_tentativi), *params],
            )
            return cursor.rowcount > 0

    # Scopo: Conteggi per stato (monitoraggio), opzionalmente per job_type e/o
    #        scope operatore. `owner_scope_key` None = tutta la coda (admin/
    #        sistema); valorizzato = solo i job della propria `scope_key` (badge
    #        top bar per-operatore).
    def count_per_stato(
        self, *, job_type: str | None = None, owner_scope_key: str | None = None,
    ) -> dict[str, int]:
        conditions: list[str] = []
        params: list[Any] = []
        if job_type is not None:
            conditions.append("job_type = %s")
            params.append(job_type)
        if owner_scope_key is not None:
            conditions.append("scope->>'scope_key' = %s")
            params.append(str(owner_scope_key))
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT stato, COUNT(*)::int
              FROM dbops.coda_lavori
              {where}
             GROUP BY stato
        """  # noqa: S608 — where da condizioni whitelisted (nessun input libero)
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return {str(r[0]): int(r[1]) for r in cursor.fetchall()}

    # Scopo: Elenco paginato dei job per la UI di gestione code (tracciamento).
    #        Proietta stato/tentativi/errore/timeline/proprietario + `is_mio`
    #        (il job è del chiamante: la `scope_key` combacia) calcolato QUI, così
    #        il FE non confronta identità (P-5). `owner_scope_key` FILTRA le righe
    #        (operatore → solo le proprie; None = tutte, per l'admin `code_manage`);
    #        `caller_scope_key` serve SOLO a calcolare `is_mio` (resta la chiave del
    #        chiamante anche quando vede tutto). Filtri opzionali stato/job_type/
    #        intervallo `data_insert`/solo-vivi. Ritorna `{items, total}` (total =
    #        righe che matchano PRIMA della paginazione, via `COUNT(*) OVER()`).
    def elenca(
        self,
        *,
        owner_scope_key: str | None = None,
        caller_scope_key: str | None = None,
        stati: list[str] | None = None,
        job_type: str | None = None,
        data_da: Any = None,
        data_a: Any = None,
        solo_vivi: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        conditions: list[str] = []
        where_params: list[Any] = []
        if owner_scope_key is not None:
            conditions.append("scope->>'scope_key' = %s")
            where_params.append(str(owner_scope_key))
        if solo_vivi:
            conditions.append("stato IN ('PENDING', 'IN_CORSO')")
        elif stati:
            conditions.append("stato = ANY(%s)")
            where_params.append(list(stati))
        if job_type is not None:
            conditions.append("job_type = %s")
            where_params.append(str(job_type))
        if data_da is not None:
            conditions.append("data_insert >= %s")
            where_params.append(data_da)
        if data_a is not None:
            conditions.append("data_insert <= %s")
            where_params.append(data_a)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        sql = f"""
            SELECT id, job_type, stato, priorita, tentativi, max_tentativi,
                   ultimo_errore, run_after, claimed_at, started_at, ended_at,
                   job_run_id, result,
                   scope->>'username' AS proprietario,
                   scope->>'scope_key' AS scope_key,
                   (scope->>'scope_key' = %s) AS is_mio,
                   COUNT(*) OVER()::int AS total
              FROM dbops.coda_lavori
              {where}
             ORDER BY priorita, id
             LIMIT %s OFFSET %s
        """  # noqa: S608 — where da condizioni whitelisted (nessun input libero)
        params = [caller_scope_key, *where_params, safe_limit, safe_offset]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        def _iso(value: Any) -> str | None:
            return value.isoformat() if value is not None else None

        total = int(rows[0][16]) if rows else 0
        items = [
            {
                "id": int(r[0]),
                "job_type": str(r[1]),
                "stato": str(r[2]),
                "priorita": int(r[3]),
                "tentativi": int(r[4]),
                "max_tentativi": int(r[5]),
                "ultimo_errore": r[6],
                "run_after": _iso(r[7]),
                "claimed_at": _iso(r[8]),
                "started_at": _iso(r[9]),
                "ended_at": _iso(r[10]),
                "job_run_id": None if r[11] is None else int(r[11]),
                "result": r[12],
                "proprietario": r[13],
                "scope_key": r[14],
                "is_mio": bool(r[15]),
            }
            for r in rows
        ]
        return {"items": items, "total": total}

    # Scopo: Stato di un job per il polling FE (I-3 non bloccante): stato +
    #        result (a FATTO) + ultimo_errore (a ERRORE). None se id inesistente
    #        (o fuori dallo scope, se `owner_scope_key` passato). Ownership
    #        SCOPE-based: il job è di proprietà della sua `scope->>'scope_key'`
    #        (chi condivide lo scope lo vede — coerente con la dedup, che aggancia
    #        allo stesso job solo chi ha la stessa scope_key). Un job di altro
    #        scope è indistinguibile da inesistente (no leak). `owner_scope_key`
    #        None = nessun filtro (admin globale / sistema: vede ogni job).
    def get_stato(
        self, item_id: int, *, owner_scope_key: str | None = None,
    ) -> dict[str, Any] | None:
        conditions = ["id = %s"]
        params: list[Any] = [int(item_id)]
        if owner_scope_key is not None:
            conditions.append("scope->>'scope_key' = %s")
            params.append(str(owner_scope_key))
        where = " AND ".join(conditions)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, job_type, stato, tentativi, max_tentativi,
                       result, ultimo_errore, job_run_id
                  FROM dbops.coda_lavori
                 WHERE {where}
                """,  # noqa: S608 — where da condizioni whitelisted
                params,
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": int(row[0]),
            "job_type": str(row[1]),
            "stato": str(row[2]),
            "tentativi": int(row[3]),
            "max_tentativi": int(row[4]),
            "result": row[5],
            "ultimo_errore": row[6],
            "job_run_id": None if row[7] is None else int(row[7]),
        }
