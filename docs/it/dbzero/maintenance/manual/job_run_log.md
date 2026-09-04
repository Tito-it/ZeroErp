## 📚 Documentazione Tabella: `maintenance.job_run_log`

> 👀 **Vedi anche:**
>
Approfondimento tabelle:
>
`maintenance.job_definitions` *(riferimento ipotetico: la tabella non esiste)*
>
Approfondimento funzioni/procedure:
>
[maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log)
> [script.fn_job_run_start](/dbzero/script/funzioni/fn_job_run_start)
> [script.fn_job_run_end](/dbzero/script/funzioni/fn_job_run_end)
> [maintenance.proc_apply_storicizza_defaults_job](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults_job)

---
### 🎯 Scopo Principale
(latest review 18-06-2026)
La tabella `maintenance.job_run_log` memorizza i log di esecuzione dei job schedulati o lanciati manualmente all’interno del sistema Zero ERP.
Ogni riga rappresenta una singola esecuzione di un job, includendo informazioni di stato, tempi di inizio/fine, eventuali errori e dettagli di esecuzione.

È la tabella **generica** "un record per esecuzione di job" per **qualsiasi** processo
schedulato: job **pgAgent** (lato DB) *e* **job headless cron/command** (management
command Django via systemd, es. `run_fatturazione_batch`). La colonna **`origine`**
distingue la sorgente del lancio; la colonna **`meta`** porta un riepilogo *generico* del
run. Il dettaglio di dominio NON vive qui (es. la fatturazione lo tiene in `vendite.*`,
correlato via `run_uuid`).

---

### Vincoli e Relazioni

* **`job_run_log_pkey`**: Chiave primaria su `id`.
* **Relazioni logiche** (non vincolate da FK nel DDL):

  * Possibile collegamento con tabella di definizione job (`maintenance.job_definitions`).
  * Utilizzata da funzioni di logging automatico (`maintenance.fn_run_and_log`).

---

### Colonne discriminanti `origine` e `meta`

* **`origine`** (`varchar(16)` NOT NULL, default `'PGAGENT'`, CHECK
  `chk_job_run_log_origine`): come è stato lanciato il run.
  * `PGAGENT` — job DB pgAgent (default; backfill dei record storici, semantica identica a prima).
  * `CRON` — management command schedulato (systemd/cron), es. `run_fatturazione_batch`.
  * `COMMAND` — lancio manuale di un command.
* **`meta`** (`jsonb` NOT NULL, default `'{}'`): riepilogo **generico** del run (es. conteggi
  per esito). **Mai** dettaglio di dominio (resta nei domini, correlato via `run_uuid`).

### ⭐ Rev 2026-09-04 — chi è che sta girando

Il giornale registrava da sempre **che** qualcosa era girato. Non registrava
**chi**: un run era una riga senza autore, e in un sistema multi-azienda questa
è una domanda che prima o poi qualcuno fa.

| colonna | Che cosa dice |
| --- | --- |
| `processo_codice` | quale processo di [dbops.processi](/dbzero/dbops/manual/processi) sta girando (**hard FK**: un codice inventato viene respinto) |
| `auth_user_id` | l'utente tecnico con cui gira, quando ne ha uno |

⚠️ **`auth_user_id` non è l'operatore per-item della coda.** Quello sta già in
`coda_lavori.scope`, ed è un'altra cosa: qui c'è l'identità del **processo**,
là c'è la persona che ha chiesto un singolo lavoro.

⭐ **I dodici job notturni si sono dichiarati senza toccare lo scheduler.** Il
codice del processo non viene passato come parametro: si **deriva dal nome del
job**, perché per convenzione le due stringhe coincidono. Chi vuole essere
esplicito passa comunque il parametro, che vince.

⇒ Il presidio [dbops.vw_run_senza_attore](/dbzero/dbops/manual/vw_run_senza_attore)
conta chi non si è ancora dichiarato — guardando l'**ultima** corsa, non lo
storico: le righe vecchie hanno l'autore vuoto per sempre e non sono sanabili.

---

### Percorsi di scrittura

* **pgAgent** → [`maintenance.fn_run_and_log`](/dbzero/maintenance/funzioni/fn_run_and_log)
  (avvolge un blocco SQL). Invariata.
* **Job headless (cron/command)** → [`script.fn_job_run_start`](/dbzero/script/funzioni/fn_job_run_start)
  + [`script.fn_job_run_end`](/dbzero/script/funzioni/fn_job_run_end): spezzano start/end
  attorno a un corpo job **Python**. `SECURITY DEFINER` (i ruoli batch headless non hanno
  DML diretto sulla tabella, solo `EXECUTE`). Advisory lock di sessione opzionale per
  anti-overlap fra run dello stesso job (per `lock_key`).

### Considerazioni di Progettazione

* Permette la **tracciabilità completa** delle esecuzioni, con dettagli utili per debug e audit.
* Il campo `run_uuid` consente di correlare log multipli appartenenti alla stessa sessione o esecuzione — e di **agganciare i record di dominio** del run (es. `vendite.*` per la fatturazione).
* La colonna `agent_host` è utile per identificare l’host sorgente in scenari multi-server o distribuiti.

---

### 🚨 Gestione Errori e Audit

* Gli errori vengono registrati nei campi `error_code` ed `error_detail`, mantenendo in `message` un testo più leggibile per l’operatore.
* Integrazione con funzioni di logging standard (`fn_run_and_log`) per assicurare uniformità nella raccolta dei dati.

---

> **“Questa tabella rappresenta il cuore del sistema di tracciamento dei job, fornendo una base solida per l’analisi delle esecuzioni e la diagnosi dei problemi.”**

---

{% include-markdown "signature-core.md" %}
