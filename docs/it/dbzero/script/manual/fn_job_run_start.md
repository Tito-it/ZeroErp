## Documentazione Concettuale – Funzione `script.fn_job_run_start`

> **Vedi anche**
>
**Tabelle correlate:**
>
[maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log)
>
**Funzioni correlate:**
>
[script.fn_job_run_end](/dbzero/script/funzioni/fn_job_run_end),
[maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log)

---
### 🎯 Scopo Principale
(latest review 18-06-2026 — registrazione run job headless)

La funzione **`script.fn_job_run_start`** apre un **run** nel registro generico
[`maintenance.job_run_log`](/dbzero/maintenance/tabelle/job_run_log) per i **job
headless** (management command cron/command in Python). È la controparte di apertura;
la chiusura è [`script.fn_job_run_end`](/dbzero/script/funzioni/fn_job_run_end).

Esiste perché [`fn_run_and_log`](/dbzero/maintenance/funzioni/fn_run_and_log) avvolge un
blocco **SQL** (`EXECUTE p_sql`) e non è adatta a un corpo job in **Python**: qui start ed
end sono spezzati attorno al corpo applicativo.

---

### Parametri di input

| Parametro      | Tipo                                       | Default    | Descrizione                                                            |
| -------------- | ------------------------------------------ | ---------- | ---------------------------------------------------------------------- |
| `p_jobname`    | `maintenance.job_run_log.jobname%TYPE`     | —          | Nome del job.                                                          |
| `p_origine`    | `text`                                     | `'CRON'`   | `PGAGENT` / `CRON` / `COMMAND` (validato dal CHECK colonna all'INSERT). |
| `p_stepname`   | `maintenance.job_run_log.stepname%TYPE`    | `NULL`     | Step opzionale.                                                        |
| `p_lock_key`   | `text`                                     | `NULL`     | Identità **logica** del job (es. `run_fatturazione_batch:immediata`) per l'anti-overlap. Non è una colonna. |
| `p_agent_host` | `maintenance.job_run_log.agent_host%TYPE`  | `NULL`     | Host sorgente; default `inet_client_addr()`.                          |
| `p_processo_codice` | `maintenance.job_run_log.processo_codice%TYPE` | `NULL` | ⭐ *(dal 2026-09-04)* quale processo di [dbops.processi](/dbzero/dbops/manual/processi) sta girando. **Hard FK**: un codice inventato viene respinto. |
| `p_auth_user_id` | `integer`                              | `NULL`     | ⭐ *(dal 2026-09-04)* l'utente tecnico con cui il processo gira, quando ne ha uno. |

⚠️ **I due parametri nuovi stanno in CODA e hanno un default**: le chiamate
esistenti continuano a funzionare senza modifiche. ⛔ Aggiungere un parametro a
una funzione ne crea però un **overload**: la firma a cinque argomenti è stata
`DROP`ata esplicitamente, o sarebbero rimaste due funzioni e il backend avrebbe
chiamato a caso.

🔴 **E il `DROP` porta via i privilegi.** La `CREATE` successiva riparte dal
default di PostgreSQL, che per le funzioni è `EXECUTE` a `PUBLIC`: su una
`SECURITY DEFINER` è un buco. Il `REVOKE ... FROM PUBLIC` è stato rimesso con
una correttiva. ⇒ Chi rifà `DROP` + `CREATE` **ricostruisce l'ACL nello stesso
changeSet**.

---

### Output

`RETURNS TABLE(id, run_uuid, acquired)`:

* **`id`** — PK della riga `job_run_log` aperta (da passare a `fn_job_run_end`).
* **`run_uuid`** — UUID del run, per correlare i record di dominio (`meta`/tabelle di dominio).
* **`acquired`** — `true` se il run può procedere; `false` se un altro run dello stesso
  `lock_key` è già in corso (in tal caso la riga "skip" è già loggata e chiusa).

---

### Anti-overlap (advisory lock di sessione)

* Se `p_lock_key` è valorizzato, prova `pg_try_advisory_lock(classid, hashtext(p_lock_key))`
  con `classid` fisso per i job headless (namespace separato dai lock di `fn_run_and_log`).
* Lock occupato → **non aspetta**: inserisce una riga **saltata** (`saltata=true`,
  `ok` NULL, `ended_at` valorizzato, `message='skip: another run in progress'`) e ritorna
  `acquired=false`. Il chiamante salta il lavoro e **non** chiude la corsa:
  `fn_job_run_end` la rifiuta.
  ⚠️ Fino al 2026-10-10 la riga nasceva con `ok=true`, e ogni lettore la contava come
  una corsa riuscita (vedi [job_run_log](/dbzero/maintenance/manual/job_run_log),
  «una corsa saltata non è una corsa riuscita»).
* Il lock è di **sessione**: tenuto per tutta la durata del run (start→corpo→end sulla
  **stessa** connessione) e rilasciato da `fn_job_run_end` o alla chiusura connessione
  (nessun lock orfano su crash). L'anti-overlap protegge fra **connessioni diverse** (due
  run cron); nella stessa sessione il lock è re-entrant.

---

### Regole principali

* **`SECURITY DEFINER`** con `search_path` fisso (`pg_catalog, pg_temp`) e tabella
  fully-qualified: i ruoli batch headless (`zeroerp_batch_<job>`) hanno solo bisogno di
  `EXECUTE`, **nessun DML diretto** su `maintenance.job_run_log`.
* `EXECUTE` **revocato da PUBLIC** (concesso ai soli ruoli che hanno `USAGE` su `script`).
* `origine` non è validata in-funzione: lo fa il CHECK `chk_job_run_log_origine`.

---

### Esempio d'uso

```sql
-- apertura (con anti-overlap)
SELECT * FROM script.fn_job_run_start(
  p_jobname  => 'run_fatturazione_batch:immediata',
  p_origine  => 'CRON',
  p_lock_key => 'run_fatturazione_batch:immediata'
);
-- -> (id, run_uuid, acquired). Se acquired=false: altro run in corso, NON eseguire il corpo.
```

---

{% include-markdown "signature-core.md" %}
