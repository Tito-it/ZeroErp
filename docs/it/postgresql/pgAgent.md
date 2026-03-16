# Estensione PostgreSQL: pgAgent

> **Vedi anche**
>
> * Schema e utilita': **[`maintenance`](/dbzero/maintenance)**
> * Estensioni utili: [`pgcrypto`](/postgresql/pgcrypto), [`dblink`](/postgresql/dblink)

L'**agent di schedulazione** per PostgreSQL. In Zero ERP lo adotteremo come **best practice** per **tutte le attivita' periodiche** legate al database (manutenzione, allineamenti, pulizie, compattazioni, verifiche, rebuild/refresh, storicizzazioni, ecc.).

---

## Obiettivi

* Eseguire **job programmati** interamente lato DB (affidabilita', atomicita', tracciabilita').
* Tenere **tutta la logica di manutenzione** in un unico posto: schema `maintenance` + job pgAgent.
* Rendere riproducibile in **CI/CD** l'installazione/configurazione dei job.

---

## Concetti chiave

* **Job**: entita' principale (nome, descrizione, abilitato). Tabella: `pgagent.pga_job`.
* **Schedule**: quando eseguire (minuti, ore, weekday, monthday, mesi). Tabella: `pgagent.pga_schedule`.
* **Step**: cosa eseguire (SQL o shell). Tabella: `pgagent.pga_jobstep`.

  * `jstkind = 's'` → SQL,  `jstkind = 'b'` → batch/shell.
* **Log**: `pgagent.pga_joblog` e `pgagent.pga_jobsteplog`.
* **Classi**: categorie (es. *Routine Maintenance*). Tabella: `pgagent.pga_jobclass`.

> **Dove sono salvati i job?** Nelle tabelle dello **schema `pgagent`** del **database scelto** (es.: `zeroerp` in CI o `Zero` in locale). Non ci sono file esterni.

---

## Struttura di progetto (linee guida)

* Tutte le procedure/funzioni usate dai job vivono nello **schema `maintenance`**.

  * Esempi: `maintenance.run_and_log(...)`, `maintenance.apply_storicizza_defaults_job()`.
* Le procedure "di business" possono restare in `dbops` e venire **wrappate** in `maintenance` per logging/lock.
* I job pgAgent **richiamano sempre** wrapper di `maintenance` (log + advisory lock).

---

## Prerequisiti

* PostgreSQL >= 17.5.
* Estensioni utili gia' create dove servono: `CREATE EXTENSION IF NOT EXISTS pgcrypto;` (UUID), `dblink` (se si logga fuori transazione).
* Schema `pgagent` installato nel **database target** (quello che usera' pgAgent).

  * In molte installazioni e' disponibile **come estensione**: `CREATE EXTENSION IF NOT EXISTS pgagent;`
    In alternativa caricare lo script SQL fornito dal pacchetto pgAgent.
* **pgAdmin**: il nodo *pgAgent Jobs* mostra i job del **Maintenance DB** configurato nel server. Assicurarsi che punti al DB giusto (es. `zeroerp`).

---

## Permessi consigliati

* Utente/servizio del pgAgent con ruolo dedicato (es. `maintenance_executor`):

  * `USAGE` su schema `maintenance`
  * `EXECUTE` su funzioni/procedure in `maintenance`
  * privilegi minimi necessari su oggetti target (tabelle, viste, ecc.)

```sql
-- Ruolo e grant di base
CREATE ROLE IF NOT EXISTS maintenance_executor;
GRANT USAGE ON SCHEMA maintenance TO maintenance_executor;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA maintenance TO maintenance_executor;
ALTER DEFAULT PRIVILEGES IN SCHEMA maintenance GRANT EXECUTE ON FUNCTIONS TO maintenance_executor;
-- Assegna il ruolo all'utente con cui gira pgAgent (es. postgres o zeroerp)
GRANT maintenance_executor TO postgres;
```

---

## Schema `maintenance` (setup minimo)

```sql
-- 0) Schema
CREATE SCHEMA IF NOT EXISTS maintenance;

-- 1) Log esecuzioni
CREATE TABLE IF NOT EXISTS maintenance.job_run_log (
  id            bigserial PRIMARY KEY,
  jobname       text NOT NULL,
  stepname      text,
  started_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
  ended_at      timestamptz,
  ok            boolean,
  rows_affected bigint,
  message       text,
  error_code    text,
  error_detail  text,
  agent_host    text DEFAULT inet_client_addr()::text,
  run_uuid      uuid NOT NULL DEFAULT gen_random_uuid()
);

-- 2) Wrapper generico: log + advisory lock
CREATE OR REPLACE FUNCTION maintenance.run_and_log(
  p_jobname  text,
  p_stepname text,
  p_sql      text,
  p_lock_key bigint DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
  v_id         bigint;
  v_rows       bigint := 0;
  v_locked     boolean := false;
  v_errmsg     text; v_errdetail text; v_errhint text; v_errcontext text; v_sqlstate text;
BEGIN
  IF p_lock_key IS NOT NULL THEN
    v_locked := pg_try_advisory_lock(p_lock_key);
    IF NOT v_locked THEN
      INSERT INTO maintenance.job_run_log(jobname, stepname, ok, message)
      VALUES (p_jobname, p_stepname, TRUE, 'skip: another run in progress');
      RETURN;
    END IF;
  END IF;

  INSERT INTO maintenance.job_run_log(jobname, stepname)
  VALUES (p_jobname, p_stepname)
  RETURNING id INTO v_id;

  BEGIN
    EXECUTE p_sql;
    GET DIAGNOSTICS v_rows = ROW_COUNT;

    UPDATE maintenance.job_run_log
       SET ended_at = clock_timestamp(), ok = TRUE, rows_affected = v_rows, message = 'done'
     WHERE id = v_id;

    IF v_locked THEN PERFORM pg_advisory_unlock(p_lock_key); END IF;

  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS
      v_errmsg     = MESSAGE_TEXT,
      v_errdetail  = PG_EXCEPTION_DETAIL,
      v_errhint    = PG_EXCEPTION_HINT,
      v_errcontext = PG_EXCEPTION_CONTEXT,
      v_sqlstate   = RETURNED_SQLSTATE;

    UPDATE maintenance.job_run_log
       SET ended_at = clock_timestamp(), ok = FALSE, message = v_errmsg,
           error_code = v_sqlstate,
           error_detail = coalesce(v_errdetail,'') ||
                          CASE WHEN v_errhint IS NOT NULL THEN E'\nHINT: '||v_errhint ELSE '' END ||
                          CASE WHEN v_errcontext IS NOT NULL THEN E'\nCONTEXT: '||v_errcontext ELSE '' END
     WHERE id = v_id;

    IF v_locked THEN PERFORM pg_advisory_unlock(p_lock_key); END IF;
    RAISE;
  END;
END
$$;

-- 3) Esempio wrapper di job (chiama una PROCEDURE con CALL)
CREATE OR REPLACE PROCEDURE maintenance.apply_storicizza_defaults_job()
LANGUAGE plpgsql AS $$
BEGIN
  PERFORM maintenance.run_and_log(
    p_jobname  := 'apply_storicizza_weekly',
    p_stepname := 'run_apply_storicizza',
    p_sql      := 'CALL dbops.apply_storicizza_defaults();',
    p_lock_key := hashtextextended('apply_storicizza_defaults', 0)
  );
END
$$;
```

---

## Creare un job (esempio: sabato ore 07:00)

```sql
DO $$
DECLARE
  v_jobid   integer;
  v_classid integer;
BEGIN
  -- Classe: Routine Maintenance
  SELECT jclid INTO v_classid
    FROM pgagent.pga_jobclass
   WHERE jclname = 'Routine Maintenance'
   LIMIT 1;

  IF v_classid IS NULL THEN
    RAISE EXCEPTION 'Job class "Routine Maintenance" non trovata';
  END IF;

  -- Idempotenza
  DELETE FROM pgagent.pga_job WHERE jobname = 'apply_storicizza_weekly';

  -- Job
  INSERT INTO pgagent.pga_job(jobjclid, jobname, jobdesc, jobenabled)
  VALUES (v_classid, 'apply_storicizza_weekly', 'Storicizza ogni sabato 07:00', TRUE)
  RETURNING jobid INTO v_jobid;

  -- Schedule: sabato (weekday=6) alle 07:00 precise
  INSERT INTO pgagent.pga_schedule(
    jscjobid, jscname, jscenabled,
    jscminutes, jschours, jscweekdays,
    jscmonthdays, jscmonths, jscstart
  ) VALUES (
    v_jobid, 'sat_07', TRUE,
    (SELECT array_agg((i = 0)::boolean) FROM generate_series(0,59) AS g(i)),
    (SELECT array_agg((i = 7)::boolean) FROM generate_series(0,23) AS g(i)),
    ARRAY[FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE]::boolean[],
    array_fill(TRUE, ARRAY[32])::boolean[],
    array_fill(TRUE, ARRAY[12])::boolean[],
    now()
  );

  -- Step: chiama il wrapper (che fa CALL della tua procedura)
  INSERT INTO pgagent.pga_jobstep(
    jstjobid, jstname, jstkind, jstcode, jstdbname
  ) VALUES (
    v_jobid,
    'run_apply_storicizza',
    's',
    $step$
      SELECT maintenance.apply_storicizza_defaults_job();
    $step$,
    current_database()
  );
END
$$;
```

### Operazioni veloci

```sql
-- Disabilita/abilita job
UPDATE pgagent.pga_job SET jobenabled = FALSE WHERE jobname = 'apply_storicizza_weekly';
UPDATE pgagent.pga_job SET jobenabled = TRUE  WHERE jobname = 'apply_storicizza_weekly';

-- Forza un run immediato
UPDATE pgagent.pga_job
   SET jobnextrun = now() - INTERVAL '1 minute'
 WHERE jobname = 'apply_storicizza_weekly';

-- Ispeziona codice step
SELECT s.jstname, s.jstkind, s.jstdbname, s.jstcode
  FROM pgagent.pga_jobstep s
  JOIN pgagent.pga_job j ON j.jobid = s.jstjobid
 WHERE j.jobname = 'apply_storicizza_weekly';
```

---

## Installazione su Windows (servizio)

```powershell
# Apri PowerShell/cmd come Amministratore
# Installa il servizio sotto LocalSystem
"C:\Program Files\PostgreSQL\17\bin\pgagent.exe" INSTALL pgagent-pg17 -u "NT AUTHORITY\LocalSystem" -p "" "host=localhost port=5432 dbname=Zero user=postgres password=<PWD>"

# Avvio e verifica
sc start pgagent-pg17
sc query pgagent-pg17

# Se serve rimuovere/reinstallare
"C:\Program Files\PostgreSQL\17\bin\pgagent.exe" REMOVE pgagent-pg17
```

> In pgAdmin il nodo **pgAgent Jobs** e' a **livello server** e legge dal **Maintenance DB** configurato nelle *Properties* del server (impostalo al DB che contiene `pgagent.*`).

---

## Integrazione CI (Ubuntu/GitHub Actions)

Aggiungi un **servizio pgAgent** accanto a PostgreSQL e verifica che il job giri.

```yaml
services:
  postgres:
    image: postgis/postgis:17-3.5
    env:
      POSTGRES_DB: zeroerp
      POSTGRES_USER: zeroerp
      POSTGRES_PASSWORD: secret
    ports: ["5432:5432"]
    options: >-
      --health-cmd "pg_isready -U zeroerp -d zeroerp"
      --health-interval 10s --health-timeout 5s --health-retries 5

  pgagent:
    image: chiavegatto/postgres-pgagent:latest   # immagine che include pgAgent
    env:
      PGAGENT_HOST: postgres
      PGAGENT_PORT: 5432
      PGAGENT_DATABASE: zeroerp
      PGAGENT_USER: zeroerp
      PGAGENT_PASSWORD: secret
```

```yaml
# Dopo le migrazioni Liquibase
- name: Wait for pgAgent
  run: sleep 15

- name: Verify pgAgent log
  env: { PGPASSWORD: secret }
  run: |
    psql -h localhost -p 5432 -U zeroerp -d zeroerp -c \
      "SELECT * FROM maintenance.job_run_log ORDER BY id DESC LIMIT 1;"
```

> Gestisci le password via `secrets` del provider CI. Evita di committare credenziali.

---

## Troubleshooting

* **Job non visibile in pgAdmin** → imposta *Maintenance database* del server al DB che contiene `pgagent.*` e fai *Refresh*.
* **Errore "database non esiste"** → la connect string del servizio punta al DB sbagliato; correggi `dbname=...`.
* **Step SQL non parte** → verifica `jstkind = 's'`, `jstdbname` coincide col DB vero, e permessi su oggetti target.
* **Overlap esecuzioni** → usa `maintenance.run_and_log(..., p_lock_key := ...)`.
* **Liquibase blocca su funzioni** → usa `splitStatements: false` e niente apici tipografici.

---

## Backup e migrazione dei job

```bash
pg_dump -h <host> -U <user> -d <db> \
  --data-only --column-inserts \
  -t pgagent.pga_job -t pgagent.pga_schedule -t pgagent.pga_jobstep \
  > pgagent_jobs.sql
```

> Consigliato comunque *versionare* creazione/modifica job via Liquibase (idempotente).

---

## Checklist rapida

* [ ] `CREATE EXTENSION pgagent;` (o install script) nel DB target
* [ ] pgAdmin → *Maintenance DB* = DB con `pgagent.*`
* [ ] Schema `maintenance` con `run_and_log` + tabelle log
* [ ] Job/step creano solo wrapper `maintenance.*`
* [ ] CI: servizio `pgagent` e verifica post-migrazione
* [ ] Permessi minimi e password in `secrets`

---

> **Nota sul recupero dei job non eseguiti:**
> pgAgent non recupera automaticamente le esecuzioni perse se il database/server era spento all'orario pianificato.
> In ambiente Linux e' possibile affiancare o sostituire pgAgent con un systemd timer configurato con OnCalendar= e Persistent=true, che riesegue il job alla prima occasione utile dopo un'interruzione.
> In ambiente Windows l'Utilita' di pianificazione (Task Scheduler) offre l'opzione "Esegui il piu' presto possibile dopo un avvio pianificato mancato", che permette di avviare un'attivita' pianificata al riavvio se l'orario previsto e' stato perso.

---

> **Regola d'oro**: tutto cio' che e' manutenzione periodica del DB vive in `maintenance` ed e' schedulato da pgAgent. Log, lock ed error handling sono standardizzati nel wrapper `run_and_log`.

---
{% include-markdown "signature-core.md" %}
