# Brief DB — Registrazione run dei job headless in `maintenance.job_run_log`

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🟢 normale — prerequisito per il lavoro BE (che attende colonne + funzioni).
> **Data**: 2026-06-17 · **Stato**: 🟡 da applicare.
>
> **Design autorevole**: [brief-design-job-run-registrazione.md](brief-design-job-run-registrazione.md)
> (modello, razionale, vincolo connessione/ruolo, piano BE). Qui **solo** ciò che serve a
> DB: DDL, funzioni, GRANT, pgTAP.
>
> **Vedi anche**: [Guida Tracciamento Processi e Job](/guide/analisi-tracciamento-processi-e-job),
> DDL vivo [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) e
> [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log),
> [brief-db-contesto-sistema-batch-fatturazione-rls.md](brief-db-contesto-sistema-batch-fatturazione-rls.md)
> (ruolo `zeroerp_batch_fatturazione`).

---

## 1. Contesto

`maintenance.job_run_log` è "un record per esecuzione di job", oggi alimentata solo dai
job **pgAgent** via `maintenance.fn_run_and_log(jobname, stepname, sql, lock_key)`. Si
**generalizza** la stessa tabella ai job **headless cron/command** (es. il management
command `run_fatturazione_batch`, systemd) — **niente seconda tabella gemella** (sarebbe
un duplicato). La fatturazione tiene il dettaglio di dominio nella propria
`vendite.event_log`/`fatturazione_lotti_task_runs`: `job_run_log` resta **generica**.

## 2. Modifiche schema — `maintenance.job_run_log`

Nuova migration `00_schema/maintenance/`:

```sql
ALTER TABLE maintenance.job_run_log
  ADD COLUMN origine varchar(16) NOT NULL DEFAULT 'PGAGENT',
  ADD COLUMN meta    jsonb       NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE maintenance.job_run_log
  ADD CONSTRAINT chk_job_run_log_origine
  CHECK (origine IN ('PGAGENT','CRON','COMMAND'));
```

- `origine` NOT NULL DEFAULT `'PGAGENT'` → **backfill implicito** dei record esistenti
  (tutti pgAgent) senza regressione; i job cron scrivono `'CRON'`, i lanci manuali
  `'COMMAND'`.
- `meta jsonb` NOT NULL DEFAULT `'{}'` → riepilogo **generico** del run (allineato al
  pattern `meta` pervasivo). **Mai** dettaglio di dominio fatturazione qui.

## 3. Funzioni start/end per job headless (Python non può passare `p_sql`)

`fn_run_and_log` avvolge un blocco **SQL** (`EXECUTE p_sql`): non adatta a un corpo job in
**Python**. Servono due funzioni che spezzano start/end attorno al corpo applicativo,
riusando l'advisory-lock di `fn_run_and_log`. **SECURITY DEFINER** (owner = owner DDL,
`search_path` fisso) così i ruoli batch hanno solo bisogno di `EXECUTE`, **non** di DML
diretto su `maintenance.job_run_log` (perimetro stretto). Nuova migration `20_code/maintenance/`.

```sql
CREATE OR REPLACE FUNCTION maintenance.fn_job_run_start(
    p_jobname    text,
    p_origine    text DEFAULT 'CRON',
    p_stepname   text DEFAULT NULL,
    p_lock_key   text DEFAULT NULL,   -- identità logica del job (es. 'run_fatturazione_batch:immediata')
    p_agent_host text DEFAULT NULL
) RETURNS TABLE(id bigint, run_uuid uuid, acquired boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = maintenance, pg_temp
AS $$
DECLARE
  v_lock     bigint;
  v_acquired boolean := true;
  v_id       bigint;
  v_uuid     uuid;
BEGIN
  -- Guard origine (difesa applicativa oltre al CHECK colonna).
  IF p_origine NOT IN ('PGAGENT','CRON','COMMAND') THEN
    RAISE EXCEPTION 'maintenance.fn_job_run_start: origine non valida %', p_origine;
  END IF;

  -- Advisory lock di SESSIONE per identità logica → anti-overlap fra run dello stesso job.
  IF p_lock_key IS NOT NULL THEN
    v_lock := hashtextextended(p_lock_key, 0);
    v_acquired := pg_try_advisory_lock(v_lock);
    IF NOT v_acquired THEN
      INSERT INTO maintenance.job_run_log(jobname, stepname, origine, ok, ended_at, message, agent_host)
      VALUES (p_jobname, p_stepname, p_origine, TRUE, clock_timestamp(),
              'skip: another run in progress',
              COALESCE(p_agent_host, inet_client_addr()::text))
      RETURNING job_run_log.id, job_run_log.run_uuid INTO v_id, v_uuid;
      RETURN QUERY SELECT v_id, v_uuid, FALSE;
      RETURN;
    END IF;
  END IF;

  INSERT INTO maintenance.job_run_log(jobname, stepname, origine, agent_host)
  VALUES (p_jobname, p_stepname, p_origine, COALESCE(p_agent_host, inet_client_addr()::text))
  RETURNING job_run_log.id, job_run_log.run_uuid INTO v_id, v_uuid;
  RETURN QUERY SELECT v_id, v_uuid, TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION maintenance.fn_job_run_end(
    p_id           bigint,
    p_ok           boolean,
    p_message      text   DEFAULT NULL,
    p_rows_affected bigint DEFAULT NULL,
    p_error_code   text   DEFAULT NULL,
    p_error_detail text   DEFAULT NULL,
    p_meta         jsonb  DEFAULT NULL,
    p_lock_key     text   DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = maintenance, pg_temp
AS $$
BEGIN
  UPDATE maintenance.job_run_log
     SET ended_at      = clock_timestamp(),
         ok            = p_ok,
         message       = COALESCE(p_message, message),
         rows_affected = COALESCE(p_rows_affected, rows_affected),
         error_code    = p_error_code,
         error_detail  = p_error_detail,
         meta          = COALESCE(p_meta, meta)
   WHERE id = p_id;

  IF p_lock_key IS NOT NULL THEN
    PERFORM pg_advisory_unlock(hashtextextended(p_lock_key, 0));
  END IF;
END;
$$;
```

> **Nota lock di sessione**: `pg_try_advisory_lock` appartiene al **backend/sessione**, non
> al ruolo → resta valido sotto SECURITY DEFINER, è tenuto per tutta la durata del run
> (start→corpo→end sulla **stessa** connessione, vincolo §4 del design) e cade comunque
> alla chiusura connessione (no lock orfani su crash del processo). Confermare che il
> BE chiami start/end sulla **stessa** connessione (lo fa: il batch gira su un'unica
> connessione dentro `system_process_context`).

## 4. Refactor opzionale (DRY) — `fn_run_and_log`

Per evitare due logiche di INSERT/UPDATE/lock, `fn_run_and_log` **può** essere
rifattorizzata per delegare a `fn_job_run_start`/`fn_job_run_end` (origine `'PGAGENT'`),
mantenendo la stessa firma e comportamento per i job pgAgent esistenti. **Opzionale e a
discrezione del team DB**: tocca una funzione in produzione-manutenzione → se preferite
non rischiare ora, lasciare `fn_run_and_log` invariata (la sovrapposizione è piccola).

## 5. GRANT (perimetro ruoli batch)

I ruoli batch headless eseguono le funzioni (SECURITY DEFINER) → serve **solo** EXECUTE,
niente DML diretto. Da aggiungere a `scripts/sql/provision_db_role_batch_fatturazione.sql`
(e da prevedere nel **pattern** per ogni futuro `zeroerp_batch_<job>`):

```sql
GRANT EXECUTE ON FUNCTION
  maintenance.fn_job_run_start(text, text, text, text, text),
  maintenance.fn_job_run_end(bigint, boolean, text, bigint, text, text, jsonb, text)
TO zeroerp_batch_fatturazione;
```

> Aggiornare di conseguenza `check_db_role_batch_fatturazione.sql` / pgTAP postura del
> ruolo RLS: `EXECUTE` sulle 2 funzioni atteso, ma **nessun** DML diretto su
> `maintenance.job_run_log` (resta fuori perimetro tabellare del ruolo).

## 6. pgTAP

Nuovo `db/pgtap/maintenance/test-job-run-registrazione.sql`:

1. colonna `origine` esiste, NOT NULL, default `'PGAGENT'`; CHECK rifiuta `'XXX'`.
2. colonna `meta` esiste, NOT NULL, default `'{}'`.
3. `fn_job_run_start('j','CRON',NULL,NULL,NULL)` → inserisce riga `origine='CRON'`,
   `acquired=true`, `run_uuid` non null, `ended_at` null.
4. `fn_job_run_end(id, true, 'done', 5, NULL, NULL, '{"k":1}'::jsonb, NULL)` → `ok=true`,
   `ended_at` valorizzato, `meta` aggiornato, `rows_affected=5`.
5. anti-overlap: due `fn_job_run_start(..., p_lock_key:='L')` nella **stessa** sessione →
   il secondo `acquired=false` + riga "skip" (NB: nella stessa sessione il primo lock è
   già posseduto; per il test cross-sessione usare due connessioni o `pg_advisory_lock`
   pre-acquisito da altra sessione simulata).
6. origine invalida → `fn_job_run_start(..., p_origine:='XXX')` solleva.
7. funzioni SECURITY DEFINER (prosecdef = true) con `search_path` fisso.

## 7. Criteri di accettazione DB

- Colonne `origine`/`meta` presenti con default/CHECK; record esistenti restano `'PGAGENT'`.
- `fn_job_run_start`/`fn_job_run_end` create, SECURITY DEFINER, `search_path` fisso.
- Advisory-lock per `p_lock_key` distinto: due chiavi diverse non si bloccano.
- `zeroerp_batch_fatturazione` ha `EXECUTE` sulle 2 funzioni, **nessun** DML su `job_run_log`.
- (se scelto) `fn_run_and_log` refactor: job pgAgent invariati, pgTAP esistenti verdi.

## 8. Coordinamento

- Generalità: vale per **ogni** job headless presente e futuro; il **meccanismo** (colonna
  `origine` + funzioni + GRANT EXECUTE) è generico, l'uso fatturazione è il primo consumer.
- Doc: aggiornare la [guida processi e job](/guide/analisi-tracciamento-processi-e-job)
  (`job_run_log`: "esecuzioni pgAgent" → "esecuzioni job schedulati: pgAgent + cron/command";
  colonna `origine`; nuove funzioni start/end).
- Nessuna modifica a changelog Liquibase già mergiati; numerazione globale per data;
  funzioni con `runOnChange` su nuovo file (mai editare changeset mergiati).
