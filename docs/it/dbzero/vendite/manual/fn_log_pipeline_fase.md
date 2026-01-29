## 📘 Documentazione Concettuale – Funzione `vendite.fn_log_pipeline_fase`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)  
>
---

### 🎯 Scopo Principale

(latest review 28-01-2026)  
La funzione **`vendite.fn_log_pipeline_fase()`** inserisce un record nel log
del lotto per registrare l’avanzamento (fase) della pipeline.

---

### ✅ Regole principali

* `lotto_id` obbligatorio.
* `status` ammessi: `I` (info), `W` (warning), `C` (critical).
* `fase` e` testo descrittivo utilizzato dalla dashboard.

---

### ✅ Output

Nessun output (RETURN void).

---

### 🧪 Esempio

```sql
SELECT vendite.fn_log_pipeline_fase(
  p_lotto_id => 123,
  p_stato_doc_fiscale_id => 1,
  p_fase => 'Caricamento lista attivita',
  p_status => 'I'
);
```

---

{% include-markdown "signature-core.md" %}
