# Analisi: Tracciamento Processi e Job


## il documento sarà sostituito quando l'attività sarà completata. 
---

## Contesto

Attualmente nel progetto Zero ERP sono presenti due sistemi di logging separati:

* **`dbops.audit_log`** → registra eventi e sessioni di auditing (BEGIN/END/INFO/WARN/ERROR).
* **`dbops.error_log`** → registra errori centralizzati.

Questi strumenti sono ottimi per tracciare eventi puntuali o sessioni logiche, ma **non sono sufficienti per gestire processi complessi o job di lunga durata** (es. calcolo fatture, migrazioni massicce, sincronizzazioni).

---

## Obiettivo

Progettare un sistema dedicato al **tracciamento dei job** che:

* Mantenga lo stato corrente di ogni processo.
* Consenta di mostrare in tempo reale il progresso (percentuale, step corrente).
* Sia integrato con `audit_log` ed `error_log` per avere tracciabilità completa.

---

## Proposta di Modellazione

### 1. Tabella `dbops.jobs`

* Definizione dei job configurabili.
* Campi: `id`, `codice`, `descrizione`, `config jsonb`, `attivo`.

### 2. Tabella `dbops.job_runs`

* Una esecuzione concreta di un job.
* Campi principali:

  * `id` (uuid), `job_id` (FK), `status` (`queued|running|success|error|canceled`),
  * `progress_pct`, `current_step`, `started_at`, `ended_at`, `duration_ms`,
  * `params jsonb`, `result jsonb`, `tx_id`, `audit_begin_id`, `audit_end_id` ,`created_by`, `node_name (per cluster)`, `pid/backend_xid (debug)`.

### 3. Tabella `dbops.job_steps`

* Tracciamento dettagliato degli step di un job.
* Campi: `id`, `job_run_id` (FK), `seq_no`, `name`, `status`, `progress_pct`, `started_at`, `ended_at`, `metrics jsonb`, `audit_id`.

### 4. Tabella opzionale `dbops.job_events`

* Eventi granulari (INFO/WARN/ERROR) per visualizzazioni in tempo reale.
* Alternativa: usare direttamente `audit_log` con viste dedicate.

---

## Integrazione con `audit_log` ed `error_log`

* `fn_audit_begin`/`fn_audit_end` collegati ai campi `audit_begin_id` e `audit_end_id` di `job_runs`.
* Eventi singoli loggati con `fn_audit_log_once`.
* Errori gravi registrati in `error_log` e associati al `job_run_id`.

---

## Flusso tipico

1. Creazione record in `job_runs` (status = queued).
2. Avvio del job → `status = running`, `audit_begin_id` registrato.
3. Aggiornamento `progress_pct` e `current_step` tramite `job_steps`.
4. Eventi intermedi loggati in `audit_log` o `job_events`.
5. Fine job → `status = success|error`, `ended_at`, `audit_end_id` registrato.

---

## Vantaggi

* **Chiarezza operativa**: stato immediato del job da `job_runs`.
* **Storico dettagliato**: `job_steps` e `audit_log` offrono granularità.
* **UI e monitoraggio**: una dashboard può mostrare job, step ed eventi.
* **Flessibilità**: possibile aggiungere metriche specifiche per singoli job.

---

## Best Practice

* Usare `tx_id` come chiave di correlazione tra tabelle.
* Applicare advisory lock per evitare esecuzioni parallele non volute.
* Prevedere retention differenziata (eventi a breve, job\_run a medio/lungo termine).
* Integrare `LISTEN/NOTIFY` per aggiornamenti in tempo reale.

---

## Conclusione

Il sistema proposto affianca `audit_log` ed `error_log`, offrendo un **livello dedicato al monitoraggio dei job**. Sarà così possibile tracciare processi lunghi come il calcolo fatture, mostrando in modo trasparente **stato, step, progressi e anomalie**.

---
{% include-markdown "signature-core.md" %}
