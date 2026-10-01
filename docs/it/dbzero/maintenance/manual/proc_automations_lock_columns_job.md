## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_lock_columns_job`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
>
[`dbops.fn_run_automations_lock_columns`](/dbzero/dbops/funzioni/fn_run_automations_lock_columns)
> [`maintenance.fn_run_and_log`](/dbzero/maintenance/funzioni/fn_run_and_log)

---
### 🎯 Scopo Principale
(latest review 11-01-26)
* **Eseguire in modo schedulato** l’orchestrazione delle **automazioni LOCK_COLUMNS** (trigger di blocco colonne) incapsulando la chiamata a `dbops.fn_run_automations_lock_columns(...)` e il cleanup dei trigger obsoleti in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.

---

### Firma

```sql
PROCEDURE maintenance.proc_automations_lock_columns_job()
```

---

### Descrizione

La procedura:

1. Invoca `maintenance.fn_run_and_log(...)` per tracciare **inizio/fine**, esito e **messaggi** dell’esecuzione.
2. Esegue la SQL:

   `SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', NULL, false);`

   `SELECT dbops.fn_run_automations_date_validita('SCHEDULED', NULL, false);`

   come **step** identificato da `automations_lock_columns / run_automations_lock_columns`.
3. Usa un **advisory lock** (chiave derivata da `hashtext('automations_lock_columns')`) per evitare **sovrapposizioni** se lo scheduler tenta più run contemporanei.

> In caso di errore, `fn_run_and_log` registra l’evento (con eventuale `tx_id` di sessione) e restituisce lo stato d’esito; la gestione delle eccezioni non interrompe lo scheduler, ma consente la diagnosi post‑mortem.

---

### Flusso di esecuzione (alto livello)

1. **Acquire lock** tramite `p_lock_key`.
2. **Log start** (`p_jobname`, `p_stepname`).
3. **Esecuzione**:
   `SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', NULL, false);`,
   poi `SELECT dbops.fn_run_automations_date_validita('SCHEDULED', NULL, false);`.

> ⛔ **Fino al 2026-09-26 qui girava anche `dbops.fn_run_automations_drop_lock_trg`**,
> ora ritirata. Cancellava per funzione i lock di colonna delle tabelle che il
> registro non nominava, **anche quelli scritti a mano**: su dbdev sono spariti
> così i lock di `config.iva_stati` e di `vendite.fatture.natura_doc_id`, mentre
> in CI il job non esiste (`85_pgagent` è `MARK_RAN`) e non se ne accorgeva
> nessuno. Togliere un lock che non serve più è ora l'azione `TOGLIE` di
> `dbops.fn_run_automations_lock_columns`, che prima controlla che il registro
> conosca le colonne.

#### Esempio manuale (che cosa farebbe la convergenza)

```sql
SELECT * FROM dbops.fn_lock_columns_divergenze('SCHEDULED', NULL);
```
4. **Log end** con esito **OK/KO** e dettagli.
5. **Release lock**.

---

### Idempotenza & sicurezza

* La procedura è **idempotente**: `dbops.fn_run_automations_lock_columns` converge verso il registro, e su una tabella già allineata non fa niente.
* ⚠️ Se una colonna è bloccata da un trigger che il registro non nomina, il runner **si ferma** con `E_LOCK_COLUMNS` e il run finisce KO nel log del job: è voluto. Il rimedio è una riga nel registro, non rilanciare.
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

### Osservabilità & diagnostica

* Controlla la tabella/log usata da `fn_run_and_log` (es. `maintenance.job_log` o equivalente) per:

  * **start_time / end_time**
  * **status** (success/fail)
  * **message** / **error_detail**
  * **tx_id** (correlazione cross‑component)

* In caso di KO:

  * verifica eventuali log applicativi collegati alle automazioni (es. `dbops.error_log` / `maintenance.error_log` se presenti)
  * confronta l’ultimo run riuscito vs fallito per capire se l’errore e' **data‑dependent** o **DDL‑dependent**

---

### Dipendenze

* `dbops.fn_run_automations_lock_columns` — converge i trigger **LOCK_COLUMNS** verso il registro: crea, rigenera, toglie.
* `dbops.fn_run_automations_date_validita` — il guard delle date di validità (automazione DATE_VALIDITA).
* `maintenance.fn_run_and_log` — esecuzione protetta con logging e advisory lock.

---

> **In breve**: questa procedura e' il wrapper schedulabile e sicuro per lanciare la convergenza dei lock **LOCK_COLUMNS** e il guard delle date di validità, con logging strutturato e prevenzione di esecuzioni concorrenti.

---

{% include-markdown "signature-core.md" %}
