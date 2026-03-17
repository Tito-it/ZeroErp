## 📘 Documentazione Concettuale – Funzione `vendite.fn_complete_lotto_task_run`

### 🎯 Scopo Principale

Chiude un task run impostando `task_stato = COMPLETATO` e `ended_at`.

---

### Regole principali

* `p_task_run_id` obbligatorio (`> 0`)
* merge di `p_meta` sui metadati esistenti
* in caso di record mancante genera errore applicativo `scope=LOTTO`

---

### Output

`void`

---

{% include-markdown "signature-core.md" %}
