## 📘 Documentazione Concettuale – Procedura `maintenance.proc_apply_storicizza_defaults_job`

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [`maintenance.proc_apply_storicizza_defaults`](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults)
> * [`maintenance.fn_run_and_log`](/dbzero/maintenance/funzioni/fn_run_and_log)
>
> Approfondimento guide:
>
> * [Storicizzazione Tabelle](/guide/storicizzazione-tabelle)
> * [Transaction ID](/guide/tx_id_implementation_guide)

---

### 🎯 Scopo Principale

(latest review 07-01-26)
* **Eseguire in modo schedulato** l’applicazione delle **impostazioni di storicizzazione di default** sull’intero database, incapsulando la chiamata a `maintenance.proc_apply_storicizza_defaults()` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.

---

### 🧩 Descrizione

La procedura:

1. Invoca `maintenance.fn_run_and_log(...)` per tracciare **inizio/fine**, esito e **messaggi** dell’esecuzione.
2. Esegue la SQL `CALL maintenance.proc_apply_storicizza_defaults();` come **step** identificato da `apply_storicizza_weekly / run_proc_apply_storicizza`.
3. Usa un **advisory lock** (chiave derivata da `hashtext('proc_apply_storicizza_defaults')`) per evitare **sovrapposizioni** se lo scheduler tenta più run contemporanei.

> In caso di errore, `fn_run_and_log` registra l’evento (con eventuale `tx_id` di sessione) e restituisce lo stato d’esito; la gestione delle eccezioni non interrompe lo scheduler, ma consente la diagnosi post‑mortem.

---

### 🔄 Flusso di esecuzione (alto livello)

1. **Acquire lock** tramite `p_lock_key`.
2. **Log start** (`p_jobname`, `p_stepname`).
3. **Esecuzione**: `CALL maintenance.proc_apply_storicizza_defaults();`.
4. **Log end** con esito **OK/KO** e dettagli.
5. **Release lock**.

---

### 🧪 Idempotenza & sicurezza

* La logica è **idempotente**: più invocazioni non dovrebbero creare effetti duplicati se la procedura applicata rispetta le policy (per es. `CREATE ... IF NOT EXISTS`, controlli di pre‑esistenza ecc.).
* Il **lock** previene esecuzioni parallele indesiderate.

---

### 📝 Esempio DDL (versione corretta)

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_apply_storicizza_defaults_job()
LANGUAGE plpgsql
AS $procedure$
BEGIN
  PERFORM maintenance.fn_run_and_log(
    p_jobname  := 'apply_storicizza_weekly',
    p_stepname := 'run_proc_apply_storicizza',
    p_sql      := 'call maintenance.proc_apply_storicizza_defaults();',
    p_lock_key := hashtext('proc_apply_storicizza_defaults')  -- evita overlap
  );
END;
$procedure$;
```

---

### ⏰ Scheduling consigliato

Puoi schedulare con **pgAgent** (Windows/Linux) o con **cron** (Linux):

### pgAgent (esempio settimanale)

* **Job**: `apply_storicizza_weekly`
* **Step** (SQL): `CALL maintenance.proc_apply_storicizza_defaults_job();`
* **Schedule**: ogni domenica 02:30 (bassa attività)

### cron (Linux) con `psql`

```
30 2 * * 0 psql "$DATABASE_URL" -c "CALL maintenance.proc_apply_storicizza_defaults_job();"
```

> Suggerimento: mantieni i job **fuori dalla finestra di backup** per evitare lock prolungati.

---

### 🧰 Osservabilità & diagnostica

* Controlla la tabella/log usata da `fn_run_and_log` (es. `maintenance.job_log` o equivalente) per:

  * **start\_time / end\_time**
  * **status** (success/fail)
  * **message** / **error\_detail**
  * **tx\_id** (correlazione cross‑component)
* In caso di KO, cerca voci correlate in `maintenance.error_log` (se integrato con `script.fn_log_error_only`/`fn_log_and_raise_error`).

---

### 🔗 Dipendenze

* `maintenance.proc_apply_storicizza_defaults` — applica le policy/trigger di storicizzazione di default.
* `maintenance.fn_run_and_log` — esecuzione protetta con logging e advisory lock.
* (Opzionale) `script.fn_log_error_only` / `script.fn_log_and_raise_error` — logging centralizzato.

---

### ✅ Checklist di produzione

* [ ] La procedura è **deployata** e testata in `dev`/`stage`.
* [ ] Esiste almeno **un job** (pgAgent/cron) attivo.
* [ ] `fn_run_and_log` scrive correttamente su log e gestisce l’advisory lock.
* [ ] Verificate le **policy di retry** dello scheduler (per errori transitori).

---

> 🧠 **In breve**: questa procedura offre un punto di ingresso unico, schedulabile e sicuro per applicare le impostazioni di storicizzazione, con tracciamento e prevenzione di run concorrenti. Mantiene pulita l’orchestrazione e delega il lavoro vero alla logica di `maintenance.proc_apply_storicizza_defaults()`.
