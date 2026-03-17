## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_fatturazione_pipeline_step`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline)  
> • [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_list_fatturazione_pipeline_steps](/dbzero/vendite/funzioni/fn_list_fatturazione_pipeline_steps)  
>
🎯 Scopo Principale

(latest review 08-02-2026)  
La funzione risolve la configurazione pipeline per un singolo step
(`stato_doc_fiscale_id`) applicando fallback su `utility_id` e
`tipo_doc_fiscale_id`.

---

### Precedenza fallback

1. `utility_id` + `tipo_doc_fiscale_id`
2. `utility_id` + `tipo_doc_fiscale_id = NULL`
3. `utility_id = NULL` + `tipo_doc_fiscale_id`
4. fallback globale: entrambi `NULL`

---

### Output

Ritorna la riga pipeline risolta con:
* `processi` (o `rollback` se `p_rollback = true`)
* `livello_match` (`UTILITY_TIPO_DOC`, `UTILITY`, `TIPO_DOC`, `FALLBACK`)
* metadati di supporto (`pipeline_id`, `ordine`, ecc.)

---

### Esempio

```sql
SELECT *
FROM vendite.fn_resolve_fatturazione_pipeline_step(
  p_tipo_lotto => 'MASSIVO',
  p_stato_doc_fiscale_id => 2,
  p_utility_id => 1,
  p_tipo_doc_fiscale_id => 3,
  p_rollback => false
);
```

---

{% include-markdown "signature-core.md" %}
