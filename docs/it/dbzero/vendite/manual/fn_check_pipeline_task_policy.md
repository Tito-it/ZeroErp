## 📘 Documentazione Concettuale – Funzione `vendite.fn_check_pipeline_task_policy`

### 🎯 Scopo Principale

Verifica la presenza di una policy task attiva per pipeline.

---

### ✅ Regole principali

* `p_pipeline_id` obbligatorio (`> 0`)
* `p_task_code` obbligatorio
* ritorna `true` se la policy esiste e `attivo=true`
* in assenza policy genera errore applicativo `scope=LOTTO`

---

### ✅ Output

`boolean`

---

{% include-markdown "signature-core.md" %}
