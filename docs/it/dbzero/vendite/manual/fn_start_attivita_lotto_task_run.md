## 📘 Documentazione Concettuale – Funzione `vendite.fn_start_attivita_lotto_task_run`

### 🎯 Scopo Principale

Apre un nuovo record runtime task su lotto attività in stato `IN_ESECUZIONE`.

---

### ✅ Regole principali

* `p_lotto_attivita_id` obbligatorio (`> 0`)
* `p_task_code` obbligatorio
* `p_block_scope` ammesso: `BRANCH|GLOBAL`
* calcola `tentativo` incrementale per chiave `(lotto_attivita_id, pipeline_id, branch_code, task_code)`
* salva snapshot di contesto (`sorgente_tipo_id`, `fase`, `depends_on`, `meta`)

---

### ✅ Output

Una riga con:
* `task_run_id`
* `tentativo`

---

{% include-markdown "signature-core.md" %}
