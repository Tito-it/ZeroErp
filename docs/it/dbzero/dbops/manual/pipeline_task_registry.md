## 📘 Documentazione Concettuale – Tabella `dbops.pipeline_task_registry`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [dbops.domini_task](/dbzero/dbops/manual/domini_task)  
> • [dbops.pipeline_task_registry_impl](/dbzero/dbops/manual/pipeline_task_registry_impl)  
>
---

### 🎯 Scopo Principale

(latest review 08-02-2026)
`dbops.pipeline_task_registry` e` il catalogo dei **task ammessi** per ciascun
dominio pipeline. Impedisce l'esecuzione di task non registrati e centralizza
la governance delle azioni eseguibili dal motore applicativo.

---

### 🔑 Campi chiave

* `dominio_id`: riferimento a `dbops.domini_task`.
* `task_code`: codice task (es. `select_attivita`, `generate_fatture_righe`).
* `attivo`: abilita/disabilita il task.
* `meta`: estensioni o note operative.

---

### ✅ Ruolo operativo

1. Si registra ogni task ammesso per dominio.
2. Il motore applicativo verifica che il task sia attivo prima di eseguirlo.
3. Le implementazioni concrete sono definite in `dbops.pipeline_task_registry_impl`.

---

{% include-markdown "signature-core.md" %}
