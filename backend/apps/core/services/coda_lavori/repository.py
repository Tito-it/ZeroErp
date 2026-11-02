# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `CodaLavoriRepository` — accesso DB alla coda generica
#        `dbops.coda_lavori`. Implementa il protocollo `QueueBackend` (SQL
#        tipizzato di claim/reaper/marca per QUESTA tabella) + enqueue (delega
#        a `dbops.fn_accoda_lavoro`, atomico e idempotente sui job vivi) +
#        operazioni amministrative (cancel/requeue/archiviazione) e di
#        monitoraggio (count/get_stato). Le transizioni di stato seguono il
#        design brief DB §3a. La tabella ha i trigger audit
#        (`data_update`/`user_update` automatici) → gli UPDATE NON li settano a
#        mano; dal 2026-09-04 ha anche `_a10_archiviazione_upd`, che governa
#        `archiviato` e ne DERIVA i due timbri — stessa regola, con una ragione
#        in più: scriverli da qui vorrebbe dire poter dire una cosa che la
#        bandiera smentisce.
# ------------------------------------------------------------

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    predicato_giorno_operativo,
    limiti_pagina,
    conta_con_perimetro,
    corsa_conclusa,
    fetch_paged_with_total,
    iso_or_none,
    jsonb_out,
    sql_order_clause,
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

# Gli stati in cui un lavoro e' VIVO — «ancora da fare o in mano al worker».
# E' la definizione dell'unique parziale `uq_coda_lavori_vivo_idem` (la dedup di
# `fn_accoda_lavoro`), del badge in topbar e del trigger di archiviazione:
# una sola, e sta qui con gli altri vocabolari di questa tabella.
STATI_VIVI = ("PENDING", "IN_CORSO")

# Soglia (minuti) oltre cui un IN_CORSO è considerato STANTIO (worker morto):
# fonte unica condivisa da reaper (drainer) e requeue manuale — la stessa
# definizione di «bloccato» per entrambi, mai due soglie che divergono.
STALE_MINUTI_DEFAULT = 30

# Default dei tentativi extra concessi da un requeue manuale (fonte unica:
# service e view NON lo ripetono — passano None/omettono il kwarg).
DEFAULT_EXTRA_TENTATIVI = 3

# Whitelist ORDER BY della lista code: chiave = `campo_sorgente` inviato dal
# frontend, valore = espressione SQL (nuda solo dove e' un alias di output della
# SELECT, che e' l'unico caso in cui ORDER BY la risolve). Direzione, NULLS e
# tiebreak li mette il BB `sql_order_clause` (2026-09-26: prima il segnaposto
# `{dir}` portava un `NULLS LAST` fisso in entrambi i versi e il tiebreak era
# `id DESC` fisso — una seconda regola accanto a quella di Tid del
# 2026-07-19/08-03, e la stessa copia viveva nella coda stampa).
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
#
# `archiviato_il` aggiunta il 2026-09-04 (brief-db-archiviazione-righe-code):
# la colonna e' a catalogo `ordinabile = t` su entrambe le code, e il seed e la
# whitelist sono confrontati da `test_liste_configurabili_seed` — accenderla la'
# senza metterla qui sarebbe una colonna che il frontend offre e il backend
# rifiuta con un 400. Nullable: la data e' NULL su tutte le righe NON
# archiviate, che in DESC il BB manda in coda.
ELENCA_SORT_SQL: dict[str, str] = {
    "id": "id",
    "job_type": "job_type",
    "stato": "stato",
    "proprietario": "proprietario",
    # ⭐ QUANDO IL LAVORO E' ENTRATO IN CODA, ed e' il default dal 2026-09-07.
    #    ⛔ Niente NULLS LAST, e non e' una dimenticanza: `data_insert` e' NOT
    #    NULL con default `now()`. E' l'unica colonna temporale della tabella
    #    che un lavoro ha SEMPRE — le altre tre le scrive il worker.
    "data_insert": "data_insert",
    # ⚠️ Ordinare qui una colonna che il lavoro non ha ancora significa mandare
    #    in fondo proprio lo stato che interessa: `started_at` lo scrive il
    #    worker quando prende il lavoro, quindi un PENDING non ce l'ha e con
    #    `NULLS LAST` finisce dopo OGNI lavoro mai avviato. Era il default fino
    #    al 2026-09-07, e il difetto era muto — la lista non nascondeva niente,
    #    seppelliva. Misurato quel giorno: le righe senza `started_at` in
    #    posizione 112 e 113 su 113, cioe' in quinta pagina da 25.
    "started_at": "started_at",
    "ended_at": "ended_at",
    "archiviato_il": "archiviato_il",
}

# Le colonne DATA della whitelist: senza direzione indicata partono DESC (regola
# Tid 2026-09-02, `colonne_desc` di `sql_order_clause`). Coincidono con le date
# ordinabili del seed — lo verifica `test_liste_configurabili_seed`.
ELENCA_SORT_COLONNE_DATA: frozenset[str] = frozenset(
    {"data_insert", "started_at", "ended_at", "archiviato_il"}
)


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
    #        ⚠️ L'`ORDER BY priorita, id` della CTE decide QUALI item entrano nel
    #        batch, NON in che ordine si eseguono: le righe tornano da un
    #        `UPDATE ... RETURNING`, e PostgreSQL non ne specifica l'ordine (qui
    #        c'e' pure un join al registry, che il planner puo' materializzare
    #        come vuole). Il chiamante cicla la lista cosi' com'e', quindi senza
    #        il riordino finale l'intenzione FIFO sarebbe dichiarata e persa una
    #        riga dopo. Misurato in app il 2026-08-17: due giri di fatturazione
    #        lanciati a pochi secondi l'uno dall'altro sono stati eseguiti al
    #        contrario, e il lotto del secondo ha preso il codice piu' basso.
    #        Non e' una questione estetica: con due giri che si contendono le
    #        stesse righe e' l'ordine di esecuzione a decidere CHI VINCE, e il
    #        giro lanciato per primo tornava con «gia' fatturato altrove».
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
                      c.tentativi, c.max_tentativi, t.handler_code, c.priorita
        """
        with connection.cursor() as cursor:
            # Param order: LIMIT (nella CTE) poi job_run_id (nella SET).
            cursor.execute(sql, [safe_limit, self._job_run_id])
            rows = cursor.fetchall()
        # Riordino esplicito con la STESSA chiave della CTE (priorita, id): e'
        # l'unico punto in cui l'ordine di esecuzione diventa deterministico.
        rows = sorted(rows, key=lambda r: (int(r[8]), int(r[0])))
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
    #
    # ⭐ Le corse hanno la STESSA forma di `MaintenanceRepository.job_liveness`
    #    (2026-09-14): `last_run_at` = il lavoro toccato piu' di recente,
    #    `in_corso` = quel lavoro e' ancora vivo (PENDING/IN_CORSO), e
    #    `ultima_conclusa` = l'ultimo lavoro arrivato a un ESITO (FATTO/ERRORE)
    #    con la sua data e il suo `ok` insieme, via `corsa_conclusa`.
    # ⛔ Fino a quel giorno `last_ok` era `stato = 'FATTO'` sulla riga piu'
    #    recente: un lavoro IN_CORSO usciva «Errore» nel pannello degli esiti,
    #    e un ANNULLATO pure. Qui la riga e' una sola per costruzione (`DISTINCT
    #    ON`), ma il difetto era della stessa famiglia della cucitura sul
    #    giornale dei run — un esito letto da una riga che un esito non ce l'ha.
    # ⚠️ ANNULLATO non e' ne' in corso ne' concluso: e' un lavoro che non ha
    #    girato, e per «com'e' andata l'ultima volta» non conta. Resta nel
    #    `total`, ed e' giusto cosi': e' stato lanciato.
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
        # scope_key reale → mio_count 0. Le condizioni compaiono TRE volte
        # (summary, recente, conclusa): i loro valori, nello stesso ordine.
        sql = f"""
            WITH summary AS (
                SELECT job_type,
                       COUNT(*)::int AS total_runs,
                       COUNT(*) FILTER (WHERE stato = 'FATTO')::int AS ok_count,
                       COUNT(*) FILTER (WHERE stato = 'ERRORE')::int AS fail_count,
                       COUNT(*) FILTER (WHERE scope->>'scope_key' = %s)::int
                           AS mio_count
                  FROM dbops.coda_lavori
                  {where}
                 GROUP BY job_type
            ),
            recente AS (
                SELECT DISTINCT ON (job_type) job_type,
                       COALESCE(ended_at, started_at, data_insert) AS toccato_il,
                       stato IN ('PENDING', 'IN_CORSO') AS in_corso
                  FROM dbops.coda_lavori
                  {where}
                 ORDER BY job_type,
                          COALESCE(ended_at, started_at, data_insert) DESC, id DESC
            ),
            conclusa AS (
                SELECT DISTINCT ON (job_type) job_type,
                       started_at, ended_at, stato = 'FATTO' AS ok
                  FROM dbops.coda_lavori
                  {where} AND stato IN ('FATTO', 'ERRORE')
                 ORDER BY job_type,
                          COALESCE(ended_at, started_at, data_insert) DESC, id DESC
            )
            SELECT s.job_type, s.total_runs, s.ok_count, s.fail_count, s.mio_count,
                   r.toccato_il::text AS last_run_at,
                   r.in_corso,
                   c.started_at, c.ended_at, c.ok
              FROM summary s
              JOIN recente r USING (job_type)
              LEFT JOIN conclusa c USING (job_type)
             ORDER BY s.job_type
        """  # noqa: S608 — where da condizioni whitelisted (nessun input libero)
        with connection.cursor() as cursor:
            cursor.execute(sql, [caller_scope_key or "", *params, *params, *params])
            return [
                {
                    "jobname": str(r[0]),
                    "total_runs": int(r[1]),
                    "ok_count": int(r[2]),
                    "fail_count": int(r[3]),
                    "mio_count": int(r[4]),
                    "last_run_at": r[5],
                    "in_corso": bool(r[6]),
                    "ultima_conclusa": corsa_conclusa(r[7], r[8], r[9]),
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
    #        intervallo `data_insert` (giorni dell'AZIENDA, `data_a` incluso:
    #        BB `predicato_giorno_operativo`). Ritorna `{items, total, archiviate}` via BB
    #        `fetch_paged_with_total` (fallback pagina-stantia: le code si
    #        auto-svuotano sotto l'utente — mai «0 risultati» a offset alto).
    #
    #        Ordinamento (2026-07-23, richiesta Tid): `sort_by`/`sort_dir` da
    #        whitelist `ELENCA_SORT_SQL` — il service ha già validato, qui
    #        l'assert è defense-in-depth (mai input libero nell'SQL). Default
    #        `started_at DESC` (l'ultimo lavoro avviato in testa); tiebreaker
    #        `id` allineato alla direzione (regola 2026-08-03), per un ordine
    #        stabile tra righe pari. È una
    #        lista di MONITORAGGIO, non la corsia del worker (che resta
    #        `priorita, id` nel claim).
    #
    #        ⭐ ARCHIVIAZIONE (2026-09-04, brief-db-archiviazione-righe-code).
    #        Le righe archiviate sono NASCOSTE di default e
    #        `includi_archiviate=True` le chiede. ⛔ La bandiera la legge SOLO
    #        questa lista: claim, reaper, `mark_*` e `count_per_stato` non la
    #        nominano, altrimenti archiviare diventerebbe un annullamento
    #        silenzioso — cioè peggio della cancellazione che la bandiera esiste
    #        per evitare (brief §3, il contratto del cantiere).
    #        ⚠️ `archiviate` dice QUANTE ne restano fuori: senza quel numero
    #        «coda pulita» e «tre righe messe via» si leggono uguali — stessa
    #        lezione di `ritirate_count` sul giornale della fattura. È un
    #        conteggio SUO, con lo stesso perimetro della lista meno la
    #        bandiera: non si deriva mai dalle righe consegnate.
    def elenca(
        self,
        *,
        owner_scope_key: str | None = None,
        caller_scope_key: str | None = None,
        stati: list[str] | None = None,
        job_type: str | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        includi_archiviate: bool = False,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        sort_by: str = "started_at",
        sort_dir: str = "DESC",
    ) -> dict[str, Any]:
        # `base_*` = il perimetro della lista SENZA la bandiera: è il frammento
        # condiviso fra le righe e il conteggio delle archiviate, che devono
        # avere lo stesso perimetro (scritto due volte, divergerebbe).
        base_conditions: list[str] = []
        base_params: list[Any] = []
        if owner_scope_key is not None:
            base_conditions.append("scope->>'scope_key' = %s")
            base_params.append(str(owner_scope_key))
        if stati:
            base_conditions.append("stato = ANY(%s)")
            base_params.append(list(stati))
        if job_type is not None:
            base_conditions.append("job_type = %s")
            base_params.append(str(job_type))
        giorno_sql, giorno_params = predicato_giorno_operativo("data_insert", data_da, data_a)
        base_conditions.append(giorno_sql)
        base_params.extend(giorno_params)
        conditions = list(base_conditions)
        where_params = list(base_params)
        if not includi_archiviate:
            conditions.append("NOT archiviato")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        # Whitelist prima dell'SQL: l'ordinamento finisce interpolato nel testo.
        # BB `sql_order_clause` RIGIDO — sort_by o sort_dir fuori lista sono
        # `ValueError`, mai il default.
        order_by = sql_order_clause(
            sort_by, sort_dir,
            colonne=ELENCA_SORT_SQL, default="data_insert", default_desc=True,
            colonne_desc=ELENCA_SORT_COLONNE_DATA,
            tiebreak="id",
        )
        data_sql = f"""
            SELECT id, job_type, stato, priorita, tentativi, max_tentativi,
                   ultimo_errore, run_after, claimed_at, started_at, ended_at,
                   job_run_id, result, data_insert,
                   archiviato, archiviato_il, archiviato_da,
                   scope->>'username' AS proprietario,
                   scope->>'scope_key' AS scope_key,
                   (scope->>'scope_key' = %s) AS is_mio,
                   COUNT(*) OVER() AS total_count
              FROM dbops.coda_lavori
              {where}
             ORDER BY {order_by}
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
        # Le nascoste, con lo STESSO perimetro della lista meno la bandiera.
        # Zero quando sono incluse: lì non c'è niente di nascosto da dichiarare
        # (stessa semantica di `ritirate_count` sul giornale della fattura).
        archiviate = 0 if includi_archiviate else conta_con_perimetro(
            "FROM dbops.coda_lavori", [*base_conditions, "archiviato"], base_params,
        )
        items = [
            {
                "id": int(r["id"]),
                "job_type": str(r["job_type"]),
                "stato": str(r["stato"]),
                "priorita": int(r["priorita"]),
                "tentativi": int(r["tentativi"]),
                "max_tentativi": int(r["max_tentativi"]),
                "ultimo_errore": r["ultimo_errore"],
                "run_after": iso_or_none(r["run_after"]),
                # ⭐ QUANDO E' STATO IMMESSO A SISTEMA, ed e' un fatto diverso da
                #    `started_at`: il primo lo scrive chi accoda, il secondo il
                #    worker che prende. Su un lavoro in attesa c'e' solo questo.
                #    ⚠️ NOT NULL a tabella, quindi `iso_or_none` non torna mai
                #    None — si usa lo stesso helper delle altre per non avere due
                #    formati di data nello stesso payload.
                "data_insert": iso_or_none(r["data_insert"]),
                "claimed_at": iso_or_none(r["claimed_at"]),
                "started_at": iso_or_none(r["started_at"]),
                "ended_at": iso_or_none(r["ended_at"]),
                "job_run_id": None if r["job_run_id"] is None else int(r["job_run_id"]),
                "result": r["result"],
                "archiviato": bool(r["archiviato"]),
                "archiviato_il": iso_or_none(r["archiviato_il"]),
                "archiviato_da": r["archiviato_da"],
                "proprietario": r["proprietario"],
                "scope_key": r["scope_key"],
                "is_mio": bool(r["is_mio"]),
            }
            for r in rows
        ]
        return {"items": items, "total": int(total), "archiviate": archiviate}

    # Scopo: alza o abbassa la bandiera `archiviato` di una riga di coda —
    #        l'ARCHIVIAZIONE, che toglie la riga dall'ELENCO senza toccarne lo
    #        stato (brief-db-archiviazione-righe-code). Ritorna True se la riga
    #        esiste (0 righe = inesistente → 404 no-leak nel service).
    #
    #        ⛔ Qui NON si ricontrolla che la riga sia terminale, e non è una
    #        dimenticanza: il criterio vive in UNA sede sola, il trigger
    #        `trg_coda_lavori_a10_archiviazione_upd`, che su una riga viva
    #        solleva `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` (409). Una copia in
    #        Python sarebbe un secondo elenco di stati destinato a sfilarsi dal
    #        primo — e il `CHECK` chk_coda_lavori_archiviato_non_vivo resta
    #        comunque sotto.
    #        ⛔ `archiviato_il` e `archiviato_da` NON si scrivono: le deriva il
    #        trigger dalla GUC `app.jwt_user`. Scriverle da qui vorrebbe dire
    #        poter dire una cosa che la bandiera smentisce.
    #        ⚠️ L'UPDATE non è condizionato al valore corrente: il verbo dichiara
    #        uno STATO desiderato, quindi archiviare ciò che è già archiviato è
    #        un successo che non fa niente — non un 409 da spiegare.
    def imposta_archiviato(self, item_id: int, *, archiviato: bool) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE dbops.coda_lavori
                   SET archiviato = %s
                 WHERE id = %s
                """,
                [bool(archiviato), int(item_id)],
            )
            return cursor.rowcount > 0

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
    # Scopo: i lavori VIVI di un tipo, per chiave di idempotenza:
    #        `{chiave: {"id", "stato"}}` per le sole chiavi che ne hanno uno.
    #        Una `SELECT` per tutte le chiavi chieste (`= ANY`), non una per
    #        chiave.
    # ⭐ Serve alla capability «Esegui ora» (2026-09-15): il dettaglio di un
    #    processo spegne il pulsante sulla sveglia che ha gia' un lavoro in
    #    coda, e l'endpoint rifiuta con `E_PROCESSO_AVVIO_GIA_IN_CODA` prima di
    #    accodare. La dedup di `fn_accoda_lavoro` resta la rete sotto (la corsa
    #    fra due click): qui si LEGGE la stessa definizione di «vivo», non se ne
    #    scrive una seconda.
    # ⚠️ Per costruzione al piu' UN lavoro vivo per chiave (l'unique parziale):
    #    l'`ORDER BY id` serve solo a rendere deterministico chi vince se un
    #    giorno quell'unique cadesse — il piu' vecchio, come fa la funzione.
    def lavori_vivi_per_chiave(
        self, *, job_type: str, chiavi: Sequence[str],
    ) -> dict[str, dict[str, Any]]:
        if not chiavi:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT idempotency_key, id, stato
                  FROM dbops.coda_lavori
                 WHERE job_type = %s
                   AND idempotency_key = ANY(%s)
                   AND stato = ANY(%s)
                 ORDER BY id
                """,
                [job_type, list(chiavi), list(STATI_VIVI)],
            )
            rows = cursor.fetchall()
        vivi: dict[str, dict[str, Any]] = {}
        for chiave, item_id, stato in rows:
            vivi.setdefault(str(chiave), {"id": int(item_id), "stato": str(stato)})
        return vivi

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
