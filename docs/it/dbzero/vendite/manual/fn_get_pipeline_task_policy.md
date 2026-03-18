## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_pipeline_task_policy`
### 🎯 Scopo Principale
Restituisce la policy runtime attiva di un task pipeline (`annullabile`, `resume_mode`, `meta`).

---

### Regole principali

* `p_pipeline_id` obbligatorio (`> 0`)
* `p_task_code` obbligatorio
* cerca solo policy `attivo = true`
* in assenza policy genera errore applicativo `scope=LOTTO`

---

### Output

Una riga con:
* `annullabile`
* `resume_mode`
* `attivo`
* `meta`

---

{% include-markdown "signature-core.md" %}
