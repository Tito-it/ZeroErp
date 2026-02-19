## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_lotti_task_runs`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline)  
>
---

### 🎯 Scopo Principale

`vendite.fatturazione_lotti_task_runs` traccia il runtime dei task di pipeline
per ogni lotto, con tentativi, esito, tempi e contesto errore.

---

### 🧱 Campi chiave (semantica)

* **Contesto**: `lotto_id`, `pipeline_id`, `stato_doc_fiscale_id`.
* **Task**: `task_code`, `fase`, `tentativo`, `task_stato`.
* **Timing**: `started_at`, `ended_at`.
* **Errore**: `error_code`, `error_message`.
* **Governance**: `meta`, `attivo`, audit standard.

---

### ✅ Regole principali

* Unicita` tecnica: `(lotto_id, stato_doc_fiscale_id, task_code, tentativo)`.
* Stati task ammessi:
  * `IN_ESECUZIONE`
  * `COMPLETATO`
  * `ERRORE`
  * `ANNULLATO`
* Coerenza temporale: `ended_at >= started_at` quando valorizzata.

---

### 🧩 Utilizzo previsto

* osservabilita` puntuale dello step (non solo log testuale),
* supporto a resume/reset deterministico,
* base per dashboard “stato task” e diagnostica runtime.

---

{% include-markdown "signature-core.md" %}
