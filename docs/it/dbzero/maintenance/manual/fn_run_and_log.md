## 📘 Documentazione Concettuale – Funzione: `maintenance.fn_run_and_log`

> 👀 **Vedi anche:**
>
Approfondimento tabelle:
>
[maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log)
>
Approfondimento funzioni:
>
[maintenance.proc_apply_storicizza_defaults_job](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults_job)

---

### 🎯 Scopo Principale

(latest review 07-01-26)
`maintenance.fn_run_and_log` esegue in modo sicuro uno *statement* SQL arbitrario e ne registra l’esecuzione su `maintenance.job_run_log`, gestendo in modo opzionale un **lock consulente** (advisory lock) per prevenire esecuzioni sovrapposte dello stesso job/step.

---

### Firma

```sql
FUNCTION maintenance.fn_run_and_log(
  p_jobname  text,         -- nome logico del job
  p_stepname text,         -- nome dello step/sottofase
  p_sql      text,         -- SQL da eseguire
  p_lock_key bigint = NULL -- chiave per advisory lock (opzionale)
) RETURNS void
```

---

### Comportamento

1. **Lock opzionale**

   * Se `p_lock_key` è valorizzato, prova `pg_try_advisory_lock(p_lock_key)`.
   * In caso di lock già detenuto da un’altra esecuzione, **non esegue** `p_sql` e scrive un log con `message = 'skip: another run in progress'`.

2. **Apertura log**

   * Inserisce una riga su `maintenance.job_run_log` con `jobname`, `stepname`, `started_at` (auto), `run_uuid` (auto).

3. **Esecuzione SQL**

   * Esegue `p_sql` con `EXECUTE` e cattura `ROW_COUNT` in `rows_affected`.

4. **Chiusura positiva**

   * Aggiorna il record del log con `ended_at`, `ok = TRUE`, `rows_affected`, `message = 'done'`.
   * Rilascia l’eventuale advisory lock.

5. **Gestione errori**

   * In caso di eccezione, cattura dettagli tramite `GET STACKED DIAGNOSTICS`:

     * `MESSAGE_TEXT`, `PG_EXCEPTION_DETAIL`, `PG_EXCEPTION_HINT`, `PG_EXCEPTION_CONTEXT`, `RETURNED_SQLSTATE`.
   * Scrive tali informazioni nei campi `message`, `error_code`, `error_detail` del log.
   * Rilascia l’eventuale advisory lock.
   * **Propaga l’errore** (`RAISE`) in modo che il chiamante possa gestirlo (comportamento modificabile togliendo il `RAISE`).

---

### Concorrenza & Idempotenza

* L’uso di `p_lock_key` consente di evitare sovrapposizioni del medesimo job/step.
* Chiavi di lock consigliate:

  * Hash del nome job/step (es. `hashtext('job_name::step_name')`).
  * Chiavi costanti per job singoli, condivise tra tutti gli step che non devono sovrapporsi.

---

### Linee Guida d’Uso

* **SQL idempotente**: quando possibile, rendere `p_sql` idempotente per facilitare retry e recovery.
* **Transazioni**: la funzione non apre/chiude transazioni esplicite; si appoggia al contesto del chiamante.
* **Messaggi leggibili**: prevedere che gli operatori consultino `message` per una diagnosi rapida, e `error_detail` per analisi tecniche.

---

### Esempi

**Esecuzione protetta da lock**

```sql
SELECT maintenance.fn_run_and_log(
  p_jobname  => 'apply_storicizza_weekly',
  p_stepname => 'run_proc_apply_storicizza',
  p_sql      => 'CALL dbops.proc_apply_storicizza_defaults();',
  p_lock_key => hashtext('proc_apply_storicizza_defaults')
);
```

**Esecuzione senza lock**

```sql
SELECT maintenance.fn_run_and_log(
  p_jobname  => 'rebuild_materialized',
  p_stepname => 'refresh_view_x',
  p_sql      => 'REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.view_x;'
);
```

---

> **Nota**: se si desidera “ingoiare” l’errore nel log senza propagazione, rimuovere il `RAISE` nella sezione `EXCEPTION`. Valutare attentamente l’impatto sugli orchestratori esterni.

---

{% include-markdown "signature-core.md" %}
