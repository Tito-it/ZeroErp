## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_attivita_pipeline_task_policy`

### 🎯 Scopo Principale

Restituisce la policy runtime attiva di un task pipeline attività,
con fallback branch specifico -> `DEFAULT`.

---

### ✅ Regole principali

* `p_pipeline_id` obbligatorio (`> 0`)
* `p_task_code` obbligatorio
* `p_branch_code` opzionale (default `DEFAULT`)
* cerca solo policy `attivo = true`
* priorita` al branch richiesto, fallback su `DEFAULT`
* in assenza policy genera errore applicativo `scope=ATTIVITA_FATTURABILI`

---

### ✅ Output

Una riga con:
* `annullabile`
* `resume_mode`
* `block_scope`
* `depends_on`
* `attivo`
* `meta`

---

{% include-markdown "signature-core.md" %}
