## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_attivita_pipeline_step`

> 👀 **Vedi anche**
>
> • [vendite.attivita_fatturabili_pipeline](/dbzero/vendite/tabelle/attivita_fatturabili_pipeline)  
> • [vendite.fn_list_attivita_pipeline_steps](/dbzero/vendite/funzioni/fn_list_attivita_pipeline_steps)  

---

### 🎯 Scopo Principale

(latest review 16-02-2026)  
La funzione risolve una singola configurazione step della pipeline
`attivita_fatturabili`, applicando fallback su:

* `utility_id`
* `sorgente_tipo_id`

---

### ✅ Regole principali

* `p_codice_step` obbligatorio.
* `p_utility_id` e `p_sorgente_tipo_id`, se valorizzati, devono essere `> 0`.
* Precedenza deterministica:
  1. match `utility + sorgente`
  2. match `utility`
  3. match `sorgente`
  4. fallback globale
* `p_rollback=true` restituisce il payload `rollback`, altrimenti `processi`.

---

### 🧪 Esempio

```sql
SELECT *
FROM vendite.fn_resolve_attivita_pipeline_step(
  p_codice_step => 'RACCOLTA_INPUT',
  p_utility_id => 1,
  p_sorgente_tipo_id => 1,
  p_rollback => false
);
```

---

{% include-markdown "signature-core.md" %}
