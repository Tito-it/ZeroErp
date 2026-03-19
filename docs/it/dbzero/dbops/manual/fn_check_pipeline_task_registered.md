## 📘 Documentazione Concettuale – Funzione `dbops.fn_check_pipeline_task_registered`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.domini_task](/dbzero/dbops/manual/domini_task)  
> • [dbops.pipeline_task_registry](/dbzero/dbops/manual/pipeline_task_registry)  
>
**Approfondimento funzioni:**
>
• [dbops.fn_get_pipeline_task_implementation](/dbzero/dbops/manual/fn_get_pipeline_task_implementation)  
>
### 🎯 Scopo Principale
(latest review 08-02-2026)
Verifica che un task sia registrato e **attivo** per un dominio.
La funzione fallisce con errore applicativo se il task non e` ammesso.

---

### Regole principali

* `p_dominio_id` obbligatorio e > 0.
* `p_task_code` obbligatorio e non vuoto.
* Task e dominio devono essere `attivo = true`.
* In caso di assenza → errore.

---

### Esempio

```sql
SELECT dbops.fn_check_pipeline_task_registered(1, 'select_attivita');
```

---

{% include-markdown "signature-core.md" %}
