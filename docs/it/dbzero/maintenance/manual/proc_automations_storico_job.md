## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_storico_job`

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [`dbops.fn_run_automations_storico`](/dbzero/dbops/funzioni/fn_run_automations_storico)
> * [`maintenance.fn_run_and_log`](/dbzero/maintenance/funzioni/fn_run_and_log)

---

### 🎯 Scopo Principale

(latest review 07-01-26)
* **Eseguire in modo schedulato** l’orchestrazione delle **automazioni STORICO** (trigger di storicizzazione su UPDATE/DELETE) incapsulando la chiamata a `dbops.fn_run_automations_storico(...)` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.

---

### 🧩 Firma

```sql
PROCEDURE maintenance.proc_automations_storico_job()
```

---

### 🧩 Descrizione

La procedura:

1. Invoca `maintenance.fn_run_and_log(...)` per tracciare **inizio/fine**, esito e **messaggi** dell’esecuzione.
2. Esegue la SQL:

   `SELECT dbops.fn_run_automations_storico('SCHEDULED', NULL, false);`

   come **step** identificato da `automations_storico / run_automations_storico`.
3. Usa un **advisory lock** (chiave derivata da `hashtext('automations_storico')`) per evitare **sovrapposizioni** se lo scheduler tenta più run contemporanei.

> In caso di errore, `fn_run_and_log` registra l’evento (con eventuale `tx_id` di sessione) e restituisce lo stato d’esito; la gestione delle eccezioni non interrompe lo scheduler, ma consente la diagnosi post‑mortem.

---

### 🔄 Flusso di esecuzione (alto livello)

1. **Acquire lock** tramite `p_lock_key`.
2. **Log start** (`p_jobname`, `p_stepname`).
3. **Esecuzione**: `SELECT dbops.fn_run_automations_storico('SCHEDULED', NULL, false);`.
4. **Log end** con esito **OK/KO** e dettagli.
5. **Release lock**.

---

### 🧪 Idempotenza & sicurezza

* La procedura è pensata per essere **idempotente** *a livello di orchestrazione*: può essere richiamata più volte senza creare duplicazioni, **se** `dbops.fn_run_automations_storico` applica la policy con controlli di pre‑esistenza (verifica trigger già presenti, strategie di existence, ecc.).
* Il **lock advisory** previene esecuzioni parallele indesiderate e riduce il rischio di:

  * DDL concorrente (creazione trigger)
  * log duplicati per run simultanei

---

### ⏰ Scheduling consigliato

Puoi schedulare con **pgAgent** (Windows/Linux) o con **cron** (Linux).

#### pgAgent (esempio giornaliero/notturno)

* **Job**: `automations_storico`
* **Step** (SQL): `CALL maintenance.proc_automations_storico_job();`
* **Schedule**: ogni notte 02:30 (bassa attività)

#### cron (Linux) con `psql`

```
30 2 * * * psql "$DATABASE_URL" -c "CALL maintenance.proc_automations_storico_job();"
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
  * confronta l’ultimo run riuscito vs fallito per capire se l’errore è **data‑dependent** o **DDL‑dependent**

---

### 🔗 Dipendenze

* `dbops.fn_run_automations_storico` — orchestratore che applica/regola la policy **STORICO** sulle tabelle nell'ambito.
* `maintenance.fn_run_and_log` — esecuzione protetta con logging e advisory lock.
* (Opzionale) funzioni di logging centralizzato (se integrate):

  * `script.fn_log_error_only`
  * `script.fn_log_and_raise_error`

---

### ✅ Checklist di produzione

* [ ] La procedura è **deployata** e testata in `dev`/`stage`.
* [ ] Esiste almeno **un job** (pgAgent/cron) attivo.
* [ ] `fn_run_and_log` scrive correttamente su log e gestisce l’advisory lock.
* [ ] Verificata la **policy di retry** dello scheduler (per errori transitori).
* [ ] Monitorati tempi medi di esecuzione e lock (evitare run troppo ravvicinati).

---

> 🧠 **In breve**: questa procedura è il wrapper schedulabile e sicuro per lanciare le automazioni **STORICO** tramite `dbops.fn_run_automations_storico`, con logging strutturato e prevenzione di esecuzioni concorrenti.

---

{% include-markdown "signature-core.md" %}
