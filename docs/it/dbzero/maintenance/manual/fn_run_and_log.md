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
   * In caso di lock già detenuto da un’altra esecuzione, **non esegue** `p_sql` e scrive una riga **saltata**: `saltata = true`, `ok` NULL, `ended_at` valorizzato, `message = 'skip: another run in progress'`.
   * ⚠️ Fino al 2026-10-10 quella riga nasceva con `ok = true` e **aperta** (`ended_at` NULL): «riuscita e mai chiusa», contata come corsa vera da ogni lettore. Vedi [job_run_log](/dbzero/maintenance/manual/job_run_log), «una corsa saltata non è una corsa riuscita».

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

### ⭐ Rev 2026-09-04 — due parametri in coda, e la derivazione dal jobname

La firma cresce di due parametri **facoltativi**, `p_processo_codice` e
`p_auth_user_id`, che finiscono nelle colonne omonime di
[job_run_log](/dbzero/maintenance/manual/job_run_log).

⭐ **Ma i dodici job pgAgent non li passano, e si dichiarano lo stesso.** Se il
codice del processo non è indicato, la funzione lo **cerca per nome**: il
`jobname` e il codice del processo in
[dbops.processi](/dbzero/dbops/manual/processi) sono per convenzione la stessa
stringa.

⇒ Nessuna modifica alla configurazione dello scheduler — che è una fase che in
CI **non gira mai**, e dove un errore si scoprirebbe solo di notte.

⚠️ Un `jobname` che non corrisponde a nessun processo resta **senza attore**, e
compare in [vw_run_senza_attore](/dbzero/dbops/manual/vw_run_senza_attore). Non
si inventa un attore: si dice che manca.

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

### ⭐ Rev 2026-10-16 — il codice di dominio e lo SQLSTATE

Quando il lavoro fallisce, lo SQLSTATE va in `job_run_log.sqlstate` e `error_code`
riceve il **codice di dominio** (`E_…`) se l'errore rispetta il contratto di
`script.fn_log_and_raise_error` («`P0001` + canale `CONSTRAINT` valorizzato»),
altrimenti lo SQLSTATE come prima. Prima un errore di dominio lasciava solo `P0001`.
Tutti e due vanno anche al verbale fuori transazione. Firma invariata.
*Brief: `brief-db-presidio-job-run-a-chi-tocca.md`.*

---

{% include-markdown "signature-core.md" %}
