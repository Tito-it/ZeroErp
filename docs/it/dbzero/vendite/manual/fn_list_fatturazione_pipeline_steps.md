## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_fatturazione_pipeline_steps`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_resolve_fatturazione_pipeline_step](/dbzero/vendite/funzioni/fn_resolve_fatturazione_pipeline_step)  
>
### 🎯 Scopo Principale
(latest review 08-02-2026)  
La funzione restituisce la lista step pipeline risolti per `tipo_lotto`,
`utility_id` e `tipo_doc_fiscale_id`, delegando la precedenza a
`fn_resolve_fatturazione_pipeline_step`.

---

### Regole principali

* Filtra solo stati lotto (`config.stati_doc_fiscale.applica_lotto = true`).
* Per ogni stato restituisce al massimo una configurazione risolta.
* Ordina per `config.stati_doc_fiscale.ordine`.

---

### Esempio

```sql
SELECT *
FROM vendite.fn_list_fatturazione_pipeline_steps(
  p_tipo_lotto => 'GIORNALIERO',
  p_utility_id => 1,
  p_tipo_doc_fiscale_id => 2
);
```

---

{% include-markdown "signature-core.md" %}
