## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_pipeline_task_implementation`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.domini_task](/dbzero/dbops/manual/domini_task)  
> • [dbops.pipeline_task_registry](/dbzero/dbops/manual/pipeline_task_registry)  
> • [dbops.pipeline_task_registry_impl](/dbzero/dbops/manual/pipeline_task_registry_impl)  
>
**Approfondimento funzioni:**
>
• [dbops.fn_check_pipeline_task_registered](/dbzero/dbops/manual/fn_check_pipeline_task_registered)  
>
### 🎯 Scopo Principale
(latest review 08-02-2026)
Risoluzione controllata dell'implementazione di un task:
usa la variante richiesta se valida, altrimenti il **default**.

---

### Regole principali

* `p_dominio_id` obbligatorio e > 0.
* `p_task_code` obbligatorio e non vuoto.
* Se `p_implementation_key` e` NULL/vuoto → usa default.
* Se `p_implementation_key` non valida → fallback su default.
* Se nessun default attivo → errore.

---

### Output

Ritorna:

* `handler_code`
* `implementation_key`
* `task_registry_id`

---

### Esempio

```sql
SELECT *
FROM dbops.fn_get_pipeline_task_implementation(
  p_dominio_id => 1,
  p_task_code => 'select_attivita',
  p_implementation_key => NULL
);
```

---

{% include-markdown "signature-core.md" %}
