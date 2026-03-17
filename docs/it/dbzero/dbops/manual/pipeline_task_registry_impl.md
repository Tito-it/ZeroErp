## 📘 Documentazione Concettuale – Tabella `dbops.pipeline_task_registry_impl`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.pipeline_task_registry](/dbzero/dbops/manual/pipeline_task_registry)  
> • [dbops.domini_task](/dbzero/dbops/manual/domini_task)  
>
🎯 Scopo Principale

(latest review 08-02-2026)
`dbops.pipeline_task_registry_impl` definisce le **implementazioni consentite**
per ciascun task. Serve a gestire in modo controllato le varianti
(`default`, `v2`, `gas_v1`, ecc.) senza dispatch dinamico libero.

---

### Campi chiave

* `task_registry_id`: riferimento al task.
* `implementation_key`: identificativo variante.
* `handler_code`: identificatore logico dell'handler applicativo.
* `is_default`: indica l'implementazione di default per il task.
* `attivo`: implementazione attiva/inattiva.

---

### Ruolo operativo

1. Per ogni task si registra almeno una implementazione `default`.
2. Il motore applicativo risolve la variante richiesta o usa la default.
3. Il dispatch reale avviene in Python tramite registry statico.

---

{% include-markdown "signature-core.md" %}
