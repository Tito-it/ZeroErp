## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_lock_columns_job`

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [`dbops.fn_run_automations_lock_columns`](/dbzero/dbops/funzioni/fn_run_automations_lock_columns)
> * [`maintenance.fn_run_and_log`](/dbzero/maintenance/funzioni/fn_run_and_log)

---

### 🎯 Scopo Principale

(latest review 11-01-26)
* **Eseguire in modo schedulato** l’orchestrazione delle **automazioni LOCK_COLUMNS** (trigger di blocco colonne) incapsulando la chiamata a `dbops.fn_run_automations_lock_columns(...)` e il cleanup dei trigger obsoleti in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.

---

### 🧩 Firma

```sql
PROCEDURE maintenance.proc_automations_lock_columns_job()
```

---

### 🧩 Descrizione

La procedura:

1. Invoca `maintenance.fn_run_and_log(...)` per tracciare **inizio/fine**, esito e **messaggi** dell’esecuzione.
2. Esegue la SQL:

   `SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', NULL, false);`

   `SELECT dbops.fn_run_automations_drop_lock_trg('SCHEDULED', NULL, false);`

   come **step** identificato da `automations_lock_columns / run_automations_lock_columns`.
3. Usa un **advisory lock** (chiave derivata da `hashtext('automations_lock_columns')`) per evitare **sovrapposizioni** se lo scheduler tenta più run contemporanei.

> In caso di errore, `fn_run_and_log` registra l’evento (con eventuale `tx_id` di sessione) e restituisce lo stato d’esito; la gestione delle eccezioni non interrompe lo scheduler, ma consente la diagnosi post‑mortem.

---

### 🔄 Flusso di esecuzione (alto livello)

1. **Acquire lock** tramite `p_lock_key`.
2. **Log start** (`p_jobname`, `p_stepname`).
3. **Esecuzione**:
   `SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', NULL, false);`.

   `SELECT dbops.fn_run_automations_drop_lock_trg('SCHEDULED', NULL, false);`.
4. **Log end** con esito **OK/KO** e dettagli.
5. **Release lock**.

---

### 🧪 Idempotenza & sicurezza

* La procedura è pensata per essere **idempotente** *a livello di orchestrazione*: può essere richiamata più volte senza creare duplicazioni, **se** `dbops.fn_run_automations_lock_columns` applica la policy con controlli di pre‑esistenza (verifica trigger già presenti, strategie di existence, ecc.).
* Il **lock advisory** previene esecuzioni parallele indesiderate e riduce il rischio di:

  * DDL concorrente (creazione trigger)
  * log duplicati per run simultanei

---

### ⏰ Scheduling consigliato

Puoi schedulare con **pgAgent** (Windows/Linux) o con **cron** (Linux).

#### pgAgent (esempio giornaliero/notturno)

* **Job**: `automations_lock_columns`
* **Step** (SQL): `CALL maintenance.proc_automations_lock_columns_job();`
* **Schedule**: ogni notte 02:40 (bassa attivita')

#### cron (Linux) con `psql`

```
40 2 * * * psql "$DATABASE_URL" -c "CALL maintenance.proc_automations_lock_columns_job();"
```

> Suggerimento: mantieni i job **fuori dalla finestra di backup** e lontano da altre migrazioni/DDL massivi per evitare lock prolungati.

---

### 🧰 Osservabilità & diagnostica

* Controlla la tabella/log usata da `fn_run_and_log` (es. `maintenance.job_log` o equivalente) per:

  * **start_time / end_time**
  * **status** (success/fail)
  * **message** / **error_detail**
  * **tx_id** (correlazione cross‑component)

* In caso di KO:

  * verifica eventuali log applicativi collegati alle automazioni (es. `dbops.error_log` / `maintenance.error_log` se presenti)
  * confronta l’ultimo run riuscito vs fallito per capire se l’errore e' **data‑dependent** o **DDL‑dependent**

---

### 🔗 Dipendenze

* `dbops.fn_run_automations_lock_columns` — orchestratore che applica/regola la policy **LOCK_COLUMNS** sulle tabelle in scope.
* `dbops.fn_run_automations_drop_lock_trg` — cleanup dei trigger **LOCK_COLUMNS** non piu' necessari.
* `maintenance.fn_run_and_log` — esecuzione protetta con logging e advisory lock.

---

> 🧠 **In breve**: questa procedura e' il wrapper schedulabile e sicuro per lanciare le automazioni **LOCK_COLUMNS** e il cleanup dei trigger obsoleti, con logging strutturato e prevenzione di esecuzioni concorrenti.

---

{% include-markdown "signature-core.md" %}
