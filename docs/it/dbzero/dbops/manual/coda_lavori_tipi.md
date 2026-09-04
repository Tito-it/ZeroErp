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
* `processo_codice`: **di quale processo** è questo tipo di job (hard FK verso
  [dbops.processi](/dbzero/dbops/manual/processi)). Vedi sotto — è il campo da
  cui dipende il guard di classe.
* `meta`: estensioni JSONB per-tipo.

---

### ⭐ Rev 2026-09-04 — ogni tipo dichiara di quale PROCESSO è

`processo_codice` è **obbligatorio**, e serve a una cosa sola: far sapere alla
coda se il lavoro che sta accodando **appartiene a un'azienda** o no.

⛔ **Il buco che chiude.** `run_as_default` è un *suggerimento*: chi accoda può
sovrascriverlo passando `p_run_as`. Un tipo di dominio accodato come `SISTEMA`
passava tutti i controlli e girava **senza perimetro** — cioè senza sapere per
conto di quale azienda stesse lavorando.

⭐ **La classe NON è duplicata qui.** Sarebbe stata una seconda scrittura dello
stesso fatto, e due scritture prima o poi dissentono: si mette il puntatore al
processo, e la classe si **legge** da `dbops.processi`. Fonte unica.

⚠️ Il `CHECK` di tabella non prende quel caso, e non è un difetto suo: controlla
la coerenza fra `run_as` e `scope`, non la **natura** del lavoro. Sono due
domande diverse, e servono due presidi.

⇒ Registrare un tipo nuovo vuol dire adesso: **prima** il processo in
`dbops.processi`, poi il tipo che lo cita.

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
| `FATTURAZIONE_NUMERA` | `fatturazione_numera_default` | `OPERATORE` | Numerazione di perimetro (C-4). |

⭐ Entrambi appartengono a un processo di classe `DOMINIO`: la coda li accetta
**solo** come `OPERATORE`, con lo scope di chi li richiede.

Brief: `brief-db-coda-lavori-generica` §2 e §4.

---

{% include-markdown "signature-core.md" %}
