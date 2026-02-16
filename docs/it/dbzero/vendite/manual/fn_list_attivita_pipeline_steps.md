## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_attivita_pipeline_steps`

> 👀 **Vedi anche**
>
> • [vendite.attivita_fatturabili_pipeline](/dbzero/vendite/tabelle/attivita_fatturabili_pipeline)  
> • [vendite.fn_resolve_attivita_pipeline_step](/dbzero/vendite/funzioni/fn_resolve_attivita_pipeline_step)  

---

### 🎯 Scopo Principale

(latest review 16-02-2026)  
Elencare gli step pipeline del dominio `attivita_fatturabili` con fallback
automatico per `utility_id` e `sorgente_tipo_id`.

---

### ✅ Regole principali

* Input opzionali:
  * `p_utility_id`
  * `p_sorgente_tipo_id`
* Se valorizzati devono essere `> 0`.
* Per ogni `codice_step` viene scelta la configurazione migliore via
  `vendite.fn_resolve_attivita_pipeline_step`.
* Output ordinato per `ordine`, poi `codice_step`.

---

### 🧪 Esempio

```sql
SELECT *
FROM vendite.fn_list_attivita_pipeline_steps(
  p_utility_id => 1,
  p_sorgente_tipo_id => 1
);
```

---

{% include-markdown "signature-core.md" %}
