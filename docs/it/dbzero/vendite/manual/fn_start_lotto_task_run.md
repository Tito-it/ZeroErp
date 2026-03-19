## 📘 Documentazione Concettuale – Funzione `vendite.fn_start_lotto_task_run`
### 🎯 Scopo Principale
Apre un nuovo record runtime task su lotto in stato `IN_ESECUZIONE`.

---

### Regole principali

* `p_lotto_id` obbligatorio (`> 0`)
* `p_task_code` obbligatorio
* calcola `tentativo` incrementale per coppia `(lotto_id, stato_doc_fiscale_id, task_code)`
* salva snapshot di contesto (`pipeline_id`, `fase`, `meta`)

---

### Output

Una riga con:
* `task_run_id`
* `tentativo`

---

{% include-markdown "signature-core.md" %}
