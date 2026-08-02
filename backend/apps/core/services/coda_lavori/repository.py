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
from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    LIST_MAX_LIMIT,
    fetch_paged_with_total,
    iso_or_none,
    jsonb_out,
)

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

# Soglia (minuti) oltre cui un IN_CORSO è considerato STANTIO (worker morto):
# fonte unica condivisa da reaper (drainer) e requeue manuale — la stessa
# definizione di «bloccato» per entrambi, mai due soglie che divergono.
STALE_MINUTI_DEFAULT = 30

# Default dei tentativi extra concessi da un requeue manuale (fonte unica:
# service e view NON lo ripetono — passano None/omettono il kwarg).
DEFAULT_EXTRA_TENTATIVI = 3

# Whitelist ORDER BY della lista code: chiave = `campo_sorgente` inviato dal
# frontend, valore = espressione SQL (nuda solo dove e' un alias di output della
# SELECT, che e' l'unico caso in cui ORDER BY la risolve). `{dir}` compare solo
# dove serve NULLS LAST — la direzione va PRIMA della clausola; altrove si
# appende in coda.
#
# ⚠️ A livello MODULO, non attributo di classe, per due motivi che vanno
# insieme: (1) il gate del service ne DERIVA l'elenco invece di ricopiarlo, e
# una whitelist raggiungibile solo attraverso la classe diventa vuota appena un
# test mocka `CodaLavoriRepository` — il gate lascerebbe passare tutto o niente
# a seconda del mock, non del codice; (2) una whitelist e' un DATO, e i dati di
# questo repo (origini, stati, soglie) stanno tutti qui sopra.
#
# `stato` aggiunta il 2026-08-02: e' NUCLEO sempre ordinabile e mancava, mentre
# la colonna e' a video da sempre. `proprietario` e' l'alias di
# `scope->>'username'` proiettato dalla SELECT.
ELENCA_SORT_SQL: dict[str, str] = {
    "id": "id",
    "job_type": "job_type",
    "stato": "stato",
    "proprietario": "proprietario {dir} NULLS LAST",
    "started_at": "started_at {dir} NULLS LAST",
    "ended_at": "ended_at {dir} NULLS LAST",
}


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
                payload=jsonb_out(r[2]) or {},
                run_as=str(r[3]),
                scope=jsonb_out(r[4]),
                tentativi=int(r[5]),
                max_tentativi=int(r[6]),
                raw={"handler_code": r[7]},
            )
            for r in rows
        ]

    # Scopo: Marca l'item completato (→FATTO) col result; azzera l'errore.
    #        Guard di OWNERSHIP dell'esecuzione (review 2026-07-22): scrive solo
    #        se il job è ancora IN_CORSO e claimato da QUESTO run (`job_run_id`
    #        timbrato dal claim) — un worker sopravvissuto a reaper/requeue non
    #        può sovrascrivere l'esito dell'esecuzione che l'ha rimpiazzato.
    def mark_done(self, item_id: int, *, result: dict[str, Any]) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE dbops.coda_lavori
                   SET stato = 'FATTO', result = %s::jsonb,
                       ultimo_errore = NULL, ended_at = now()
                 WHERE id = %s
                   AND stato = 'IN_CORSO'
                   AND job_run_id IS NOT DISTINCT FROM %s
                """,
                [json.dumps(result, default=str), int(item_id), self._job_run_id],
            )

    # Scopo: Registra il fallimento. `retry_after_secondi=None` → ERRORE
    #        terminale; int → PENDING con `run_after = now()+intervallo`
    #        (backoff col clock DB) e `claimed_at` azzerato (ri-eleggibile).
    #        `tentativi` sempre incrementato (storia preservata). Stesso guard
    #        di ownership di `mark_done` (IN_CORSO + job_run_id del claim).
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
                       AND stato = 'IN_CORSO'
                       AND job_run_id IS NOT DISTINCT FROM %s
                    """,
                    [errore_json, int(item_id), self._job_run_id],
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
                       AND stato = 'IN_CORSO'
                       AND job_run_id IS NOT DISTINCT FROM %s
                    """,
                    [errore_json, int(retry_after_secondi), int(item_id),
                     self._job_run_id],
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
    #        ⚠️ IN_CORSO è riaccodabile SOLO se STANTIO (`claimed_at` oltre
    #        `stale_minuti`, stessa soglia del reaper): riaccodare un job che
    #        un worker sta DAVVERO eseguendo farebbe partire una seconda
    #        esecuzione concorrente dello stesso handler (review 2026-07-22).
    def requeue(
        self,
        item_id: int,
        *,
        extra_tentativi: int = DEFAULT_EXTRA_TENTATIVI,
        owner_scope_key: str | None = None,
        stale_minuti: int = STALE_MINUTI_DEFAULT,
    ) -> bool:
        conditions = [
            "id = %s",
            """(stato = 'ERRORE'
                OR (stato = 'IN_CORSO'
                    AND claimed_at < now() - make_interval(mins => %s)))""",
        ]
        params: list[Any] = [int(item_id), int(stale_minuti)]
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

    # Scopo: Riassunto per `job_type` dei lavori accodati — quanti lanciati,
    #        quanti riusciti, quando è stato l'ultimo e com'è andato. Gemello di
    #        `MaintenanceRepository.list_job_summary` per la coda: serve a
    #        raccontare l'attività ON-DEMAND (lanciata dall'app) accanto a quella
    #        del batch schedulato, che vive invece in `maintenance.job_run_log`.
    #        Le due strade di lancio devono comparire nello stesso pannello,
    #        altrimenti se ne guarda una sola e l'altra sembra non esistere
    #        (2026-07-23: la fatturazione girava da mesi via app mentre il
    #        cockpit leggeva solo il batch, e mostrava «fermo da un mese»).
    #
    #  - `competenza_mese`: filtra sul `payload->>'competenza_mese'` del job. Qui
    #    la competenza è DICHIARATA all'accodamento (l'endpoint la normalizza al
    #    1° del mese) — nessun ripiego euristico, a differenza dei run storici
    #    del batch.
    #  - `caller_scope_key`: NON filtra — i conteggi sono l'attività COMPLESSIVA
    #    (decisione Tid 2026-07-23: chi è autorizzato all'attività deve vedere il
    #    totale, un conteggio ristretto ai propri è un'informazione sbagliata).
    #    Serve a SPEZZARE il totale in `mio_count` (job con la stessa scope_key
    #    del chiamante) vs altri — stessa identità di `is_mio` in `elenca`, mai
    #    una seconda regola. None (uso di sistema) → `mio_count = 0`.
    #
    # `ok`/`fail` contano gli stati TERMINALI (FATTO/ERRORE); `total` include
    # anche i non terminali (PENDING/IN_CORSO) e gli ANNULLATO, così «10/13» si
    # legge onestamente come «13 lanciati, 10 riusciti» senza gonfiare i riusciti.
    def summary_per_job_type(
        self,
        *,
        job_types: list[str],
        competenza_mese: date | None = None,
        caller_scope_key: str | None = None,
    ) -> list[dict[str, Any]]:
        if not job_types:
            return []
        conditions: list[str] = ["job_type = ANY(%s)"]
        params: list[Any] = [list(job_types)]
        if competenza_mese is not None:
            conditions.append("payload->>'competenza_mese' = %s")
            params.append(competenza_mese.replace(day=1).isoformat())
        where = "WHERE " + " AND ".join(conditions)
        # `ended_at` è l'istante in cui il lavoro si è concluso; per i job non
        # ancora terminati si ripiega su started_at e infine sull'accodamento,
        # così «ultimo giro» non risulta mai vuoto per un job in corso.
        # `caller_scope_key` è il primo parametro perché compare per primo
        # nell'SQL (FILTER del mio_count); '' quando None: non matcha nessuna
        # scope_key reale → mio_count 0.
        sql = f"""
            SELECT job_type,
                   COUNT(*)::int AS total_runs,
                   COUNT(*) FILTER (WHERE stato = 'FATTO')::int AS ok_count,
                   COUNT(*) FILTER (WHERE stato = 'ERRORE')::int AS fail_count,
                   COUNT(*) FILTER (WHERE scope->>'scope_key' = %s)::int
                       AS mio_count,
                   MAX(COALESCE(ended_at, started_at, data_insert))::text
                       AS last_run_at,
                   (ARRAY_AGG(stato ORDER BY
                        COALESCE(ended_at, started_at, data_insert) DESC))[1]
                       = 'FATTO' AS last_ok
              FROM dbops.coda_lavori
              {where}
             GROUP BY job_type
             ORDER BY job_type
        """  # noqa: S608 — where da condizioni whitelisted (nessun input libero)
        with connection.cursor() as cursor:
            cursor.execute(sql, [caller_scope_key or "", *params])
            return [
                {
                    "jobname": str(r[0]),
                    "total_runs": int(r[1]),
                    "ok_count": int(r[2]),
                    "fail_count": int(r[3]),
                    "mio_count": int(r[4]),
                    "last_run_at": r[5],
                    "last_ok": r[6],
                }
                for r in cursor.fetchall()
            ]

    # Whitelist CHIUSA di ordinamento della lista job: chiave pubblica (query
    # param) -> espressione SQL. `started_at`/`ended_at` sono NULL per i job
    # non ancora avviati/conclusi: NULLS LAST esplicito, così ordinando per
    # «avviato» i job mai partiti stanno in fondo in ENTRAMBE le direzioni
    # (senza, in DESC PG li metterebbe in testa).
    # Scopo: Elenco paginato dei job per la UI di gestione code (tracciamento).
    #        Proietta stato/tentativi/errore/timeline/proprietario + `is_mio`
    #        (il job è del chiamante: la `scope_key` combacia) calcolato QUI, così
    #        il FE non confronta identità (P-5). `owner_scope_key` FILTRA le righe
    #        (operatore → solo le proprie; None = tutte, per l'admin `code_manage`);
    #        `caller_scope_key` serve SOLO a calcolare `is_mio` (resta la chiave del
    #        chiamante anche quando vede tutto). Filtri opzionali stato/job_type/
    #        intervallo `data_insert` (`data_a` bound ESCLUSIVO: il chiamante
    #        passa già il giorno+1). Ritorna `{items, total}` via BB
    #        `fetch_paged_with_total` (fallback pagina-stantia: le code si
    #        auto-svuotano sotto l'utente — mai «0 risultati» a offset alto).
    #
    #        Ordinamento (2026-07-23, richiesta Tid): `sort_by`/`sort_dir` da
    #        whitelist `ELENCA_SORT_SQL` — il service ha già validato, qui
    #        l'assert è defense-in-depth (mai input libero nell'SQL). Default
    #        `started_at DESC` (l'ultimo lavoro avviato in testa); tiebreaker
    #        `id DESC` sempre, per un ordine stabile tra righe pari. È una
    #        lista di MONITORAGGIO, non la corsia del worker (che resta
    #        `priorita, id` nel claim).
    def elenca(
        self,
        *,
        owner_scope_key: str | None = None,
        caller_scope_key: str | None = None,
        stati: list[str] | None = None,
        job_type: str | None = None,
        data_da: Any = None,
        data_a: Any = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "started_at",
        sort_dir: str = "DESC",
    ) -> dict[str, Any]:
        conditions: list[str] = []
        where_params: list[Any] = []
        if owner_scope_key is not None:
            conditions.append("scope->>'scope_key' = %s")
            where_params.append(str(owner_scope_key))
        if stati:
            conditions.append("stato = ANY(%s)")
            where_params.append(list(stati))
        if job_type is not None:
            conditions.append("job_type = %s")
            where_params.append(str(job_type))
        if data_da is not None:
            conditions.append("data_insert >= %s")
            where_params.append(data_da)
        if data_a is not None:
            conditions.append("data_insert < %s")
            where_params.append(data_a)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        safe_limit = max(1, min(int(limit), LIST_MAX_LIMIT))
        safe_offset = max(0, int(offset))
        sort_expr = ELENCA_SORT_SQL.get(sort_by)
        assert sort_expr is not None, f"sort_by non in whitelist: {sort_by!r}"
        assert sort_dir in ("ASC", "DESC"), f"sort_dir non valido: {sort_dir!r}"
        # `{dir}` presente solo nelle espressioni con NULLS LAST (la direzione
        # va PRIMA della clausola NULLS); per le altre si appende in coda.
        order_by = (
            sort_expr.format(dir=sort_dir)
            if "{dir}" in sort_expr
            else f"{sort_expr} {sort_dir}"
        )
        data_sql = f"""
            SELECT id, job_type, stato, priorita, tentativi, max_tentativi,
                   ultimo_errore, run_after, claimed_at, started_at, ended_at,
                   job_run_id, result,
                   scope->>'username' AS proprietario,
                   scope->>'scope_key' AS scope_key,
                   (scope->>'scope_key' = %s) AS is_mio,
                   COUNT(*) OVER() AS total_count
              FROM dbops.coda_lavori
              {where}
             ORDER BY {order_by}, id DESC
             LIMIT %s OFFSET %s
        """  # noqa: S608 — where/order da whitelist chiuse (nessun input libero)
        rows, total = fetch_paged_with_total(
            data_sql,
            [caller_scope_key, *where_params, safe_limit, safe_offset],
            fallback_count_sql=(
                f"SELECT COUNT(*) FROM dbops.coda_lavori {where}"  # noqa: S608
            ),
            fallback_params=list(where_params),
            offset=safe_offset,
        )
        items = [
            {
                "id": int(r["id"]),
                "job_type": str(r["job_type"]),
                "stato": str(r["stato"]),
                "priorita": int(r["priorita"]),
                "tentativi": int(r["tentativi"]),
                "max_tentativi": int(r["max_tentativi"]),
                "ultimo_errore": jsonb_out(r["ultimo_errore"]),
                "run_after": iso_or_none(r["run_after"]),
                "claimed_at": iso_or_none(r["claimed_at"]),
                "started_at": iso_or_none(r["started_at"]),
                "ended_at": iso_or_none(r["ended_at"]),
                "job_run_id": None if r["job_run_id"] is None else int(r["job_run_id"]),
                "result": jsonb_out(r["result"]),
                "proprietario": r["proprietario"],
                "scope_key": r["scope_key"],
                "is_mio": bool(r["is_mio"]),
            }
            for r in rows
        ]
        return {"items": items, "total": int(total)}

    # Scopo: Dettaglio COMPLETO di un job per il drawer della UI code (BE-8):
    #        oltre ai campi del polling, payload, origine, priorita, timeline
    #        (accodato/claimed/started/ended), run_after, proprietario
    #        (scope->>'username') e `is_mio` (scope_key del job == quella del
    #        chiamante, calcolato QUI — il FE non confronta identità, P-5).
    #        `owner_scope_key` filtra come in `get_stato` (None = nessun filtro,
    #        admin `code_manage`); `caller_scope_key` serve SOLO a `is_mio`.
    #        None se id inesistente o fuori scope (indistinguibile, no leak).
    def get_dettaglio(
        self,
        item_id: int,
        *,
        owner_scope_key: str | None = None,
        caller_scope_key: str | None = None,
    ) -> dict[str, Any] | None:
        conditions = ["id = %s"]
        params: list[Any] = [caller_scope_key, int(item_id)]
        if owner_scope_key is not None:
            conditions.append("scope->>'scope_key' = %s")
            params.append(str(owner_scope_key))
        where = " AND ".join(conditions)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, job_type, stato, priorita, origine, payload,
                       tentativi, max_tentativi, result, ultimo_errore,
                       run_after, data_insert, claimed_at, started_at,
                       ended_at, job_run_id,
                       scope->>'username' AS proprietario,
                       scope->>'scope_key' AS scope_key,
                       (scope->>'scope_key' = %s) AS is_mio
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
            "priorita": int(row[3]),
            "origine": str(row[4]),
            "payload": jsonb_out(row[5]),
            "tentativi": int(row[6]),
            "max_tentativi": int(row[7]),
            "result": jsonb_out(row[8]),
            "ultimo_errore": jsonb_out(row[9]),
            "run_after": iso_or_none(row[10]),
            "data_insert": iso_or_none(row[11]),
            "claimed_at": iso_or_none(row[12]),
            "started_at": iso_or_none(row[13]),
            "ended_at": iso_or_none(row[14]),
            "job_run_id": None if row[15] is None else int(row[15]),
            "proprietario": row[16],
            "scope_key": row[17],
            "is_mio": bool(row[18]),
        }

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
            "result": jsonb_out(row[5]),
            "ultimo_errore": jsonb_out(row[6]),
            "job_run_id": None if row[7] is None else int(row[7]),
        }
