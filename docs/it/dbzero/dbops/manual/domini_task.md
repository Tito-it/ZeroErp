## 📘 Documentazione Concettuale – Tabella `dbops.domini_task`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [dbops.pipeline_task_registry](/dbzero/dbops/manual/pipeline_task_registry)  
> • [dbops.pipeline_task_registry_impl](/dbzero/dbops/manual/pipeline_task_registry_impl)  
>
---

### 🎯 Scopo Principale

(latest review 08-02-2026)
`dbops.domini_task` definisce i **domini logici** per i task pipeline
(es. `FATTURAZIONE`, `ATTIVITA_FATTURABILI`, `PRATICHE`).
Serve a stabilire un **perimetro chiaro** per il registry multi‑dominio
e garantire univocita` dei task per dominio.

---

### 🔑 Campi chiave

* `codice`: identificativo dominio (univoco).
* `descrizione`: descrizione funzionale.
* `attivo`: dominio attivo/inattivo.
* `meta`: estensioni.

---

### ✅ Ruolo operativo

1. Si inseriscono i domini applicativi ammessi.
2. Ogni task viene registrato in `dbops.pipeline_task_registry` con riferimento al dominio.
3. Il motore applicativo usa `codice`/`id` per risolvere i task consentiti.

---

{% include-markdown "signature-core.md" %}
