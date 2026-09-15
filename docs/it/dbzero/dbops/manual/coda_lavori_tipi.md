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
(latest review 14-09-2026)

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
> è worker-based (non in-transazione), quindi un tipo senza handler non abortisce
> nessuna transazione di dominio.
>
> ⛔ **Ma NON può nascere `attivo=true`, e questa riga lo diceva fino al
> 2026-09-14.** Diceva: *«in assenza dell'handler i job restano semplicemente
> `PENDING` finché il worker non atterra»*. Era vero prima del drenatore, e non
> lo è più: `draina_coda_lavori` **claima** il lavoro, `get_handler` solleva
> `E_CODA_HANDLER_NON_REGISTRATO` e il lavoro va in `ERRORE` (al primo colpo,
> se `max_tentativi = 1`) — visibile in `vw_coda_lavori_da_guardare`, non in
> attesa. ⇒ **Regola del binding**: il tipo nasce **`attivo = false`** e il DB
> lo accende quando il backend dichiara l'handler in servizio. L'ordine lo
> fissano due guardrail del backend, non una convenzione:
> `test_nessun_handler_orfano` (handler registrato prima del seed → rosso) e
> `test_ogni_tipo_attivo_ha_un_handler` (tipo acceso prima dell'handler →
> rosso). Precedenti: `NOTIFICA_DIGEST_MUTO` (nato spento l'11-09, acceso la
> sera stessa), `ESEGUI_PROCESSO` (14-09).

---

### I tipi a catalogo

| codice | handler_code | run_as_default | processo (canale) | che cosa fa |
| --- | --- | --- | --- | --- |
| `FATTURAZIONE_GIRO` | `fatturazione_giro_default` | `OPERATORE` | `FATTURAZIONE_GIRO` (`CODA`) | Giro fatturazione on-demand (C-3). |
| `FATTURAZIONE_NUMERA` | `fatturazione_numera_default` | `OPERATORE` | `FATTURAZIONE_NUMERA` (`CODA`) | Numerazione di perimetro (C-4). |
| `CHIUSURA_SCADENZE` | `chiusura_scadenze_default` | `OPERATORE` | `chiusura_scadenze_daily` (`CODA_AUTOMATICA`) | Chiusura per scadenza degli stati gestionali, un emittente alla volta: lo accoda pgAgent con l'identità tecnica dell'emittente. |
| `NOTIFICA_DIGEST_MUTO` | `notifica_digest_muto_default` | `SISTEMA` | `guardiano_digest` (`PGAGENT`) | Avvisa una persona che il digest dei presidi ha smesso di girare (uno al giorno). |
| `ESEGUI_PROCESSO` | `esegui_processo_default` | `OPERATORE` | `avvio_manuale` (`CODA`) | «Esegui ora» su una sveglia di deploy: il drenatore lancia il comando del timer come sottoprocesso, con l'identità di chi ha premuto. `max_tentativi 1`: un processo caduto a metà non è idempotente. Nato spento (brief `brief-db-avvio-manuale-di-un-processo`). |

⭐ I due giri di fatturazione appartengono a un processo di classe `DOMINIO`:
la coda li accetta **solo** come `OPERATORE`, con lo scope di chi li richiede
(guard di classe, sopra).

⭐ **Il canale del processo e il `run_as` del tipo si accordano, e non è un
caso** (dal 2026-09-14, `db/pgtap/dbops/test-coda-tipi-canale-e-run-as.sql`):
`CODA ⇒ OPERATORE` (lo accoda una persona, l'identità è la sua — è la
definizione del canale); `PGAGENT ⇒ SISTEMA` (una macchina non ha un nome da
prestare: se il lavoro vuole un'identità, il canale è `CODA_AUTOMATICA`);
nessun tipo sotto un `COMMAND` (lo esegue systemd, non il drenatore). Non c'è
un guard a DB per questo — la posta è l'audit, non il perimetro — e il seed lo
presidia quel pgTAP.

Brief: `brief-db-coda-lavori-generica` §2 e §4;
`brief-db-processi-automatici-identita-e-perimetro` §5;
`brief-db-quattro-processi-senza-presidio` §10.2;
`brief-db-avvio-manuale-di-un-processo` §8.

---

{% include-markdown "signature-core.md" %}
