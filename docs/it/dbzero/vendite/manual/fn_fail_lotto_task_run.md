## 📘 Documentazione Concettuale – Funzione `vendite.fn_fail_lotto_task_run`

### 🎯 Scopo Principale

Chiude un task run in errore impostando `task_stato = ERRORE`, codice e messaggio.

---

### Regole principali

* `p_task_run_id` obbligatorio (`> 0`)
* `error_code`/`error_message` normalizzati con fallback (`E_GENERICO`, `Errore task`)
* merge di `p_meta` sui metadati esistenti
* in caso di record mancante genera errore applicativo `scope=LOTTO`

---

### Output

`void`

---

{% include-markdown "signature-core.md" %}
