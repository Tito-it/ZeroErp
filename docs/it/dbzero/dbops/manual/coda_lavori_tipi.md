## 📘 Documentazione Concettuale – Tabella `dbops.coda_lavori_tipi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.coda_lavori](/dbzero/dbops/manual/coda_lavori)  
> • [dbops.pipeline_task_registry_impl](/dbzero/dbops/manual/pipeline_task_registry_impl)  
>
**Approfondimento funzioni:**
>
• [dbops.fn_accoda_lavoro](/dbzero/dbops/manual/fn_accoda_lavoro)  
>

### 🎯 Scopo Principale
(latest review 20-07-2026)

`dbops.coda_lavori_tipi` è il **registry dei tipi di job** della coda lavori
generica ([dbops.coda_lavori](/dbzero/dbops/manual/coda_lavori)). Una riga per
`job_type`: il DB **valida** il tipo all'enqueue e porta i **default per-tipo**
(`run_as`, `max_tentativi`), mentre il **binding** `handler_code → callable`
resta in Python (dict `handler_registry`, registrato al boot — **no dynamic
import**). È il mirror leggero di
[dbops.pipeline_task_registry_impl](/dbzero/dbops/manual/pipeline_task_registry_impl),
applicato alla coda generica.

---

### Campi chiave

* `codice`: identificativo stabile del tipo = `coda_lavori.job_type` (UNIQUE).
  È la **chiave naturale** referenziata in hard FK da `coda_lavori`; non
  rinominare (contratto cross-ambiente).
* `handler_code`: chiave logica di dispatch verso il `handler_registry` Python.
  Il DB non conosce il callable, solo la stringa.
* `run_as_default`: default per `coda_lavori.run_as` se non passato all'enqueue
  (`SISTEMA` | `OPERATORE`).
* `max_tentativi_default`: default per `coda_lavori.max_tentativi`.
* `attivo`: se `false`, `fn_accoda_lavoro` **rifiuta** l'enqueue del tipo
  (`E_JOB_TYPE_NON_ATTIVO`).
* `meta`: estensioni JSONB per-tipo.

---

### Ruolo operativo

1. Si registra un nuovo tipo di job con una riga di **seed** (CSV in
   `80_data/sql/dbops/coda_lavori_tipi.csv`, upsert su `codice`).
2. Il **binding** dell'handler avviene lato BE (`register_handler` al boot);
   il DB porta solo i default e la validazione.
3. `fn_accoda_lavoro` legge la riga del tipo per validare (`attivo`) e risolvere
   i default (`run_as`, `max_tentativi`).

> **Un nuovo tipo di job = un seed qui + un handler BE. Zero DDL.** Il dispatch
> è worker-based (non in-transazione), quindi il tipo può nascere `attivo=true`:
> in assenza dell'handler i job restano semplicemente `PENDING` finché il worker
> non atterra, senza abortire nessuna transazione di dominio.

---

### Primo tipo seed

| codice | handler_code | run_as_default | descrizione |
| --- | --- | --- | --- |
| `FATTURAZIONE_GIRO` | `fatturazione_giro_default` | `OPERATORE` | Giro fatturazione on-demand (C-3). |

Brief: `brief-db-coda-lavori-generica` §2 e §4.

---

{% include-markdown "signature-core.md" %}
