## 📘 Documentazione Concettuale – Tabella `vendite.attivita_fatturabili_lotti_task_runs`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.attivita_fatturabili_lotti](/dbzero/vendite/tabelle/attivita_fatturabili_lotti)  
> • [vendite.attivita_fatturabili_pipeline](/dbzero/vendite/tabelle/attivita_fatturabili_pipeline)  
>
---

### 🎯 Scopo Principale

`vendite.attivita_fatturabili_lotti_task_runs` traccia il runtime dei task
pipeline per ogni lotto attività, includendo branch, tentativi, esito e dettagli errore.

---

### 🧱 Campi chiave (semantica)

* **Contesto**: `lotto_attivita_id`, `pipeline_id`, `sorgente_tipo_id`, `branch_code`.
* **Task**: `task_code`, `fase`, `tentativo`, `task_stato`.
* **Governance blocchi**: `block_scope`, `depends_on`.
* **Timing**: `started_at`, `ended_at`.
* **Errore**: `error_code`, `error_message`.
* **Audit**: `meta`, `attivo`, audit standard.

---

### ✅ Regole principali

* Unicita` tecnica: `(lotto_attivita_id, pipeline_id, branch_code, task_code, tentativo)`.
* Stati task ammessi:
  * `IN_ESECUZIONE`
  * `COMPLETATO`
  * `ERRORE`
  * `ANNULLATO`
* Scope blocco ammessi:
  * `BRANCH`
  * `GLOBAL`
* Coerenza temporale: `ended_at >= started_at` quando valorizzata.

---

### 🧩 Utilizzo previsto

* osservabilita` puntuale dei task per branch,
* supporto operativo a resume/rerun senza blocco globale non necessario,
* base dati per API stato/task-runs della pipeline attività.

---

{% include-markdown "signature-core.md" %}
