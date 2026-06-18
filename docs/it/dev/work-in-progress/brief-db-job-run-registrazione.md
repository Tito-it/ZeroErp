# Brief DB — Registrazione run dei job headless in `maintenance.job_run_log`

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🟢 normale — prerequisito per il lavoro BE (che attende colonne + funzioni).
> **Data**: 2026-06-17 · **Stato**: 🟢 **Lato DB COMPLETATO** (J1–J7): changeset applicati
> su dbdev, **pgTAP verdi**, doc tabella/funzioni + guida aggiornate. Resta il **BE**
> (`registered_job` + wiring `run_fatturazione_batch`).
>
> **Decisioni prese (2026-06-17)**:
>
> - **(a)** Le funzioni `fn_job_run_start/end` vivono in **`script`** (non `maintenance`):
>   i ruoli app/batch hanno già `USAGE` su `script` → niente `USAGE` su `maintenance`
>   (schema deliberatamente chiuso). La **tabella** resta in `maintenance`; la funzione
>   SECURITY DEFINER ci scrive fully-qualified.
> - **(b)** `fn_run_and_log` **lasciata invariata** (nessun refactor DRY): tipi `lock_key`
>   incompatibili (bigint vs text), funzione di manutenzione in produzione, **zero pgTAP**
>   a coprirla → rischio > beneficio.
>
> **Design autorevole**: [brief-design-job-run-registrazione.md](brief-design-job-run-registrazione.md).
> Qui **solo** ciò che serve a DB: DDL, funzioni, GRANT, pgTAP, piano.
>
> **Vedi anche**: [Guida Tracciamento Processi e Job](/guide/analisi-tracciamento-processi-e-job),
> DDL vivo [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log),
> [brief-db-contesto-sistema-batch-fatturazione-rls.md](brief-db-contesto-sistema-batch-fatturazione-rls.md)
> (ruolo `zeroerp_batch_fatturazione`).

---

## 1. Contesto

`maintenance.job_run_log` è "un record per esecuzione di job", oggi alimentata solo dai job
**pgAgent** via `maintenance.fn_run_and_log(jobname, stepname, sql, lock_key)`. Si
**generalizza** la stessa tabella ai job **headless cron/command** (es. il management
command `run_fatturazione_batch`) — **niente seconda tabella gemella**. Il dettaglio di
dominio della fatturazione resta in `vendite.event_log`/`fatturazione_lotti_task_runs`:
`job_run_log` resta **generica**.

Stato verificato (2026-06-17): `job_run_log` ha già `run_uuid uuid NOT NULL DEFAULT
uuidv7()`, `started_at DEFAULT clock_timestamp()`, `agent_host DEFAULT inet_client_addr()`,
`ok`, `rows_affected`, `message`, `error_code`, `error_detail`. **Nessun pgTAP** referenzia
oggi `job_run_log`/`fn_run_and_log`.

## 2. Schema — `maintenance.job_run_log` (J1)

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
  (tutti pgAgent), zero regressione; cron → `'CRON'`, lanci manuali → `'COMMAND'`.
- `ADD COLUMN` con default costante = metadata-only in PG (no table rewrite).
- `meta jsonb` NOT NULL DEFAULT `'{}'` → riepilogo **generico** del run. **Mai** dettaglio
  di dominio fatturazione.

## 3. Funzioni start/end (J2, J3) — in `script`, SECURITY DEFINER

`fn_run_and_log` avvolge un blocco **SQL** (`EXECUTE p_sql`): non adatta a un corpo job in
**Python**. Servono due funzioni che spezzano start/end attorno al corpo applicativo.
**SECURITY DEFINER** (owner = owner DDL) così i ruoli batch non hanno bisogno di DML
diretto su `maintenance.job_run_log`. **Schema `script`** (decisione a): i ruoli batch/app
hanno già `USAGE` su `script` e `GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA script` dal
provisioning → **nessun GRANT nuovo necessario**, nessuna apertura di `maintenance`.

Differenze rispetto alla bozza di design, da implementare:

- **Niente guard `origine` in-funzione**: la validità è già garantita dal `CHECK`
  colonna (`chk_job_run_log_origine`) all'INSERT → si evita un codice errore custom e si
  resta a norma (no `RAISE` con testo libero).
- **`search_path` hardened**: `SET search_path = pg_catalog, pg_temp` + tabella
  **fully-qualified** `maintenance.job_run_log` (no dipendenza dal path del chiamante).
- **`%TYPE` sui parametri/locali legati a colonne** (convenzione progetto, es.
  `p_id maintenance.job_run_log.id%TYPE`): la firma *risolta* non cambia (id→bigint,
  meta→jsonb, …) quindi `REVOKE`/`DROP`/pgTAP restano validi. Eccezione `p_origine`:
  resta **`text`** e non `origine%TYPE` — i parametri non portano il typmod
  (`varchar(16)` → diventerebbe `character varying` senza lunghezza, zero beneficio) e
  il valore è già vincolato dal `CHECK` colonna.
- **Advisory lock a DUE chiavi** `pg_try_advisory_lock(classid, objid)` con `classid` fisso
  per i job headless (`hashtext('zeroerp:job_run_log')`) e `objid = hashtext(p_lock_key)`
  → namespace praticamente separato dai lock bigint di `fn_run_and_log`.
- **`REVOKE EXECUTE … FROM PUBLIC`** subito dopo ogni `CREATE` (defense-in-depth; il gate
  reale resta `USAGE` su `script`, concesso solo ai ruoli app/batch).
- **`fn_job_run_end` robusta su end-dopo-skip**: sblocca solo se la riga non era già chiusa
  (lo skip chiude la riga in `start` e NON acquisisce lock per quel flusso) → niente
  warning `pg_advisory_unlock` su lock non posseduto.

```sql
CREATE OR REPLACE FUNCTION script.fn_job_run_start(
    p_jobname    text,
    p_origine    text DEFAULT 'CRON',
    p_stepname   text DEFAULT NULL,
    p_lock_key   text DEFAULT NULL,   -- identità logica del job (es. 'run_fatturazione_batch:immediata')
    p_agent_host text DEFAULT NULL
) RETURNS TABLE(id bigint, run_uuid uuid, acquired boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
  c_lock_class constant int := hashtext('zeroerp:job_run_log');  -- namespace lock headless
  v_acquired boolean := true;
  v_id   bigint;
  v_uuid uuid;
BEGIN
  -- origine validata dal CHECK colonna all'INSERT (no guard ridondante qui).
  IF p_lock_key IS NOT NULL THEN
    v_acquired := pg_try_advisory_lock(c_lock_class, hashtext(p_lock_key));
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

REVOKE EXECUTE ON FUNCTION script.fn_job_run_start(text,text,text,text,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION script.fn_job_run_end(
    p_id            bigint,
    p_ok            boolean,
    p_message       text   DEFAULT NULL,
    p_rows_affected bigint DEFAULT NULL,
    p_error_code    text   DEFAULT NULL,
    p_error_detail  text   DEFAULT NULL,
    p_meta          jsonb  DEFAULT NULL,
    p_lock_key      text   DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
  c_lock_class constant int := hashtext('zeroerp:job_run_log');
  v_already_ended boolean;
BEGIN
  SELECT (ended_at IS NOT NULL) INTO v_already_ended
  FROM maintenance.job_run_log WHERE id = p_id;

  UPDATE maintenance.job_run_log
     SET ended_at      = clock_timestamp(),
         ok            = p_ok,
         message       = COALESCE(p_message, message),
         rows_affected = COALESCE(p_rows_affected, rows_affected),
         error_code    = p_error_code,
         error_detail  = p_error_detail,
         meta          = COALESCE(p_meta, meta)
   WHERE id = p_id;

  -- Sblocca SOLO se un lock è realmente posseduto da questo flusso:
  -- end-dopo-skip (riga già chiusa) non possiede il lock → niente unlock/warning.
  IF p_lock_key IS NOT NULL AND NOT COALESCE(v_already_ended, TRUE) THEN
    PERFORM pg_advisory_unlock(c_lock_class, hashtext(p_lock_key));
  END IF;
END;
$$;

REVOKE EXECUTE ON FUNCTION script.fn_job_run_end(bigint,boolean,text,bigint,text,text,jsonb,text) FROM PUBLIC;
```

> **Nota lock di sessione**: `pg_try_advisory_lock` appartiene al **backend/sessione**, non
> al ruolo → resta valido sotto SECURITY DEFINER, tenuto per tutta la durata del run
> (start→corpo→end sulla **stessa** connessione, vincolo §4 del design) e cade comunque
> alla chiusura connessione (no lock orfani su crash). **Re-entranza**: nella *stessa*
> sessione lo stesso lock è ri-acquisibile → l'anti-overlap protegge fra **connessioni
> diverse** (due run cron), non fra chiamate nella stessa sessione (vedi limite test §6).

## 4. `fn_run_and_log` — INVARIATA (decisione b)

Nessun refactor DRY. Motivi: `p_lock_key` è **bigint** in `fn_run_and_log` vs **text** qui
(convenzioni di lock diverse), è una funzione di manutenzione in produzione con molti
chiamanti pgAgent (`proc-*-job`), e **nessun pgTAP** la copre (regressione silenziosa). La
piccola sovrapposizione non giustifica il rischio.

## 5. GRANT / perimetro ruoli (J4)

Conseguenza della **decisione (a)** (funzioni in `script`):

- Il ruolo `zeroerp_batch_fatturazione` **ha già** `EXECUTE` su queste funzioni tramite il
  `GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA script` + `ALTER DEFAULT PRIVILEGES` del suo
  provisioning → **nessun GRANT nuovo da aggiungere** allo script provisioning.
- **`REVOKE EXECUTE … FROM PUBLIC`** è nelle migration funzioni (J2/J3). Il gate effettivo
  resta `USAGE` su `script`, concesso solo ai ruoli app/batch.
- **Nessun** `USAGE` su `maintenance` da concedere (resta chiuso).

> **Trade-off onesto (registrato)**: stando in `script`, le funzioni ereditano il broad
> `EXECUTE` che anche `zeroerp_app` (web) ha sullo schema `script`. Essendo SECURITY
> DEFINER, ciò significa che un ruolo app potrebbe scrivere righe in `job_run_log`. Severità
> **bassa** (tabella di log, nessun dato di business, nessun bypass RLS). Se in futuro si
> volesse restringere a **soli** ruoli batch, spostare le 2 funzioni in `maintenance` e
> concedere esplicitamente `USAGE maintenance` + `EXECUTE` ai soli `zeroerp_batch_<job>`.

Aggiornare comunque `check_db_role_batch_fatturazione.sql` / pgTAP postura ruolo (J6):
`EXECUTE` sulle 2 funzioni atteso, **nessun** DML diretto su `maintenance.job_run_log`.

## 6. pgTAP (J5, J6)

Nuovo `db/pgtap/maintenance/test-job-run-registrazione.sql`:

1. colonna `origine` esiste, NOT NULL, default `'PGAGENT'`; `CHECK` rifiuta `'XXX'`.
2. colonna `meta` esiste, NOT NULL, default `'{}'`.
3. `script.fn_job_run_start('j','CRON')` → riga `origine='CRON'`, `acquired=true`,
   `run_uuid` non null, `ended_at` null.
4. `script.fn_job_run_end(id, true, 'done', 5, NULL, NULL, '{"k":1}'::jsonb)` → `ok=true`,
   `ended_at` valorizzato, `meta` aggiornato, `rows_affected=5`.
5. funzioni SECURITY DEFINER (`prosecdef=true`) con `search_path` fisso, in schema `script`.
6. `REVOKE`d da PUBLIC (no `EXECUTE` per PUBLIC).

> **Limite onesto (anti-overlap)**: l'advisory lock di sessione è **re-entrant**, quindi due
> `fn_job_run_start` con la stessa `lock_key` nella **stessa** sessione tornano *entrambe*
> `acquired=true`. L'overlap reale è **cross-connessione** (due run cron) e **non è
> testabile** in un singolo `BEGIN` pgTAP (una sola sessione). Coprirlo con: test
> d'integrazione **BE** a due connessioni, oppure `dblink` da pgTAP. Il pgTAP qui copre
> struttura + happy-path start/end, **non** l'overlap.

J6: estendere `db/pgtap/rls/test-role-batch-fatturazione-postura.sql` per asserire
`has_function_privilege` EXECUTE sulle 2 funzioni e l'assenza di DML su `job_run_log`.

## 7. Piano di sviluppo (deliverable DB)

| # | Deliverable | Path | Stato |
| --- | --- | --- | --- |
| J1 | `ALTER` colonne `origine`/`meta` + CHECK | `00_schema/maintenance/20260618-01-alter-job-run-log-add-origine-meta-mctit.yaml` | ✅ applicato |
| J2 | `script.fn_job_run_start` (`%TYPE`, SECURITY DEFINER) + REVOKE PUBLIC | `20_code/script/20260618-02-create-fn-job-run-start-mctit.yaml` | ✅ applicato |
| J3 | `script.fn_job_run_end` (`%TYPE`, SECURITY DEFINER) + REVOKE PUBLIC | `20_code/script/20260618-03-create-fn-job-run-end-mctit.yaml` | ✅ applicato |
| J5 | pgTAP funzioni/colonne (`plan(21)`) | `db/pgtap/maintenance/test-job-run-registrazione.sql` | ✅ verde (overlap NON coperto, §6) |
| J6 | pgTAP postura ruolo: EXECUTE sulle 2 fn (`plan(14)`) | `db/pgtap/rls/test-role-batch-fatturazione-postura.sql` | ✅ verde |
| J7 | Doc: guida processi/job + manual `job_run_log` + manual `fn_job_run_start`/`fn_job_run_end` | `docs/it/guide/…`, `docs/it/dbzero/…/manual/…` | ✅ (pagine autogen `funzioni/*` da rigenerare con `gen_db_docs.py`) |
| — | **NON fare**: refactor `fn_run_and_log` (decisione b) | — | invariata |

> J4 (grant) **non genera deliverable**: in `script` il ruolo batch ha già EXECUTE; resta
> solo l'aggiornamento di check/pgTAP postura (J6).

Ordine: J1 → J2 → J3 → J5/J6 → J7. Poi handoff BE (`registered_job` + wiring command).
Numerazione NN globale per data; **un changeSet per file**; `logicalFilePath`; mai editare
changeset già mergiati.

## 8. Criteri di accettazione DB

- Colonne `origine`/`meta` presenti con default/CHECK; record esistenti restano `'PGAGENT'`.
- `script.fn_job_run_start`/`fn_job_run_end` create, SECURITY DEFINER, `search_path` fisso,
  `REVOKE`d da PUBLIC.
- `fn_job_run_start(...,p_lock_key)` con due chiavi diverse: run indipendenti.
- `zeroerp_batch_fatturazione` ha `EXECUTE` (via broad script grant), **nessun** DML su
  `job_run_log`.
- `fn_run_and_log` e i job pgAgent: invariati.
