## 📘 Documentazione Concettuale – Procedura `maintenance.proc_apply_fk_index_policy_job`

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [`dbops.apply_fk_index_policy`](/dbzero/dbops/funzioni/apply_fk_index_policy)
> * [`maintenance.fn_run_and_log`](/dbzero/maintenance/funzioni/fn_run_and_log)

---

### 🎯 Scopo Principale

(latest review 16-01-26)
* **Eseguire in modo schedulato** l’applicazione della **policy indici FK** incapsulando la chiamata a `dbops.apply_fk_index_policy()` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.

---

### 🧩 Firma

```sql
PROCEDURE maintenance.proc_apply_fk_index_policy_job()
```

---

### 🧩 Descrizione

La procedura:

1. Invoca `maintenance.fn_run_and_log(...)` per registrare **inizio/fine**, esito e dettagli.
2. Esegue la SQL:

   `CALL dbops.apply_fk_index_policy();`

   come **step** identificato da `apply_fk_index_policy / run_apply_fk_index_policy`.
3. Usa un **advisory lock** (`hashtext('apply_fk_index_policy')`) per evitare **esecuzioni concorrenti**.

---

### 🔄 Flusso di esecuzione (alto livello)

1. **Acquire lock** tramite `p_lock_key`.
2. **Log start** (`p_jobname`, `p_stepname`).
3. **Esecuzione**: `CALL dbops.apply_fk_index_policy();`.
4. **Log end** con esito **OK/KO** e dettagli.
5. **Release lock**.

---

### 🧪 Idempotenza & sicurezza

* La procedura e' **idempotente** a livello di orchestrazione: l’effetto dipende dallo stato di `dbops.fk_index_policy`.
* Il **lock advisory** previene run simultanei che potrebbero generare DDL concorrente.

---

### ⏰ Scheduling consigliato

#### pgAgent

* **Job**: `apply_fk_index_policy`
* **Step** (SQL): `CALL maintenance.proc_apply_fk_index_policy_job();`
* **Schedule**: notturno o finestra di bassa attivita'

#### cron (Linux) con `psql`

```
0 3 * * * psql "$DATABASE_URL" -c "CALL maintenance.proc_apply_fk_index_policy_job();"
```

---

### 🔗 Dipendenze

* `dbops.apply_fk_index_policy` — applica la policy di indicizzazione FK definita in `dbops.fk_index_policy`.
* `maintenance.fn_run_and_log` — logging + lock per run schedulati.

---

{% include-markdown "signature-core.md" %}
