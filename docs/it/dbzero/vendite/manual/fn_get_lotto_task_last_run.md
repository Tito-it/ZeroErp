## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_lotto_task_last_run`

### 🎯 Scopo Principale

Restituisce l'ultimo task run disponibile per lotto/step/task.

---

### Regole principali

* `p_lotto_id` obbligatorio (`> 0`)
* `p_task_code` obbligatorio
* filtro su `stato_doc_fiscale_id` con confronto `IS NOT DISTINCT FROM`
* ordinamento per tentativo/id decrescente

---

### Output

Ultima riga runtime con:
* stato task
* tentativo
* timestamp start/end
* eventuale errore
* metadati run

---

{% include-markdown "signature-core.md" %}
