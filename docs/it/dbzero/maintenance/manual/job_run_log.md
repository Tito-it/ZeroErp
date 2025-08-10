## 📚 Documentazione Tabella: `maintenance.job_run_log`

> 👀 **Vedi anche:**
>
> Approfondimento tabelle:
>
> * [maintenance.job\_definitions](/dbzero/maintenance/job_definitions) *(ipotetico riferimento a definizione job)*
>
> Approfondimento funzioni/procedure:
>
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log)
> * [maintenance.proc_apply_storicizza_defaults_job](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults_job)

---

### 🎯 Scopo Principale

La tabella `maintenance.job_run_log` memorizza i log di esecuzione dei job schedulati o lanciati manualmente all’interno del sistema Zero ERP.
Ogni riga rappresenta una singola esecuzione di un job, includendo informazioni di stato, tempi di inizio/fine, eventuali errori e dettagli di esecuzione.

---

### ⚙️ Vincoli e Relazioni

* **`job_run_log_pkey`**: Chiave primaria su `id`.
* **Relazioni logiche** (non vincolate da FK nel DDL):

  * Possibile collegamento con tabella di definizione job (`maintenance.job_definitions`).
  * Utilizzata da funzioni di logging automatico (`maintenance.fn_run_and_log`).

---

### 🔍 Considerazioni di Progettazione

* Permette la **tracciabilità completa** delle esecuzioni, con dettagli utili per debug e audit.
* Il campo `run_uuid` consente di correlare log multipli appartenenti alla stessa sessione o esecuzione.
* La colonna `agent_host` è utile per identificare l’host sorgente in scenari multi-server o distribuiti.

---

### 🚨 Gestione Errori e Audit

* Gli errori vengono registrati nei campi `error_code` ed `error_detail`, mantenendo in `message` un testo più leggibile per l’operatore.
* Integrazione con funzioni di logging standard (`fn_run_and_log`) per assicurare uniformità nella raccolta dei dati.

---

> 🧠 **“Questa tabella rappresenta il cuore del sistema di tracciamento dei job, fornendo una base solida per l’analisi delle esecuzioni e la diagnosi dei problemi.”**

---

{% include-markdown "signature-core.md" %}
