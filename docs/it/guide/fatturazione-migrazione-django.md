## 📘 Piano Migrazione – Fatturazione DB → Django (Best Practice)

> Obiettivo: mantenere in DB **primitive atomiche** e spostare in Django
> la **orchestrazione** e le logiche di pipeline.
>
---

### 1) Migrazione immediata (basso rischio)

**Da spostare in Django**

| Attuale in DB                             | Cosa fa oggi                                          | Da implementare in Django                               |
| ----------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------- |
| `vendite.pr_run_lotto_pipeline(...)`      | Orchestrazione completa pipeline (step + log + stato) | Service `PipelineRunner` con gestione transazioni e log |
| `vendite.fn_execute_pipeline_step(...)`   | Esecuzione task generici da `processi`                | Task runner con dispatch dinamico (whitelist funzioni)  |
| `vendite.fatturazione_pipeline` (lettura) | Configura step e task                                 | Config layer Django (lettura tabella + validazione)     |

**Note**
* Questa fase sposta **solo la regia**: il flusso si muove in Django, ma i dati
  continuano a essere prodotti/validati in DB tramite le primitive esistenti.
* In DB restano i log (`fatturazione_lotti_log`) e le funzioni “primitive” che
  garantiscono coerenza e concorrenza.
* Django gestisce retry, gestione errori, scheduling, controllo del job e reporting.

---

### 2) Migrazione con refactor (medio rischio)

**Da valutare per step successivi**

| Attuale in DB                                | Cosa fa oggi                     | Possibile refactor                                               |
| -------------------------------------------- | -------------------------------- | ---------------------------------------------------------------- |
| `vendite.fn_generate_fatture_righe(...)`     | Genera righe fattura da attività | Spostare logica di calcolo/importi in Django; DB mantiene insert |
| `vendite.fn_group_attivita_fatturabili(...)` | Aggregazione deterministica      | Portare aggregazione in Django se le regole cambiano spesso      |

**Prerequisiti**
* Prima di spostare la logica, servono **API DB stabili** per inserimento righe/testate,
  con idempotenza e controlli minimi.
* Il lock e la selezione devono restare su `fn_select_attivita_fatturabili(...)`
  per evitare doppie elaborazioni e problemi di concorrenza.

---

### 3) Rimangono in DB (alto valore DB)

**Non migrare: funzioni e trigger critici**

* `vendite.fn_select_attivita_fatturabili(...)` → lock atomico + idempotenza.
* `vendite.fn_get_or_create_fattura_header(...)` → unicita` e coerenza documento.
* `vendite.fn_get_registro_id(...)`, `vendite.fn_get_tipo_doc_fiscale_id(...)`, `vendite.fn_get_valuta_id(...)`.
* Trigger `trgfn_*` di coerenza e normalizzazione (guard/normalize).
* `vendite.fn_sync_fattura_critical(...)`, `vendite.fn_sync_lotto_fatture_stato(...)`.

**Motivo**
* Garantiscono **consistenza**, **concorrenza** e **performance** in DB.
* Sono la base su cui la parte applicativa può lavorare in modo sicuro.

---

### 📌 Deliverable Django (nuove funzioni/app)

* `PipelineRunner` → esegue step in ordine, aggiorna stato lotto, gestisce retry.
* `TaskDispatcher` → esegue task con whitelist di funzioni consentite.
* `LottoService` → crea/recupera lotto, richiama funzioni DB atomiche.
* `FatturaService` → genera righe/testate usando primitive DB.
* `JobLogService` → sincronizza log DB e stato applicativo.

**Nota**
Queste componenti non sostituiscono il DB: lo **usano come motore** per le
operazioni atomiche, mantenendo la logica di orchestrazione in Python.

---

### ✅ Regola d’oro

**DB = primitive atomiche + consistenza**  
**Django = orchestrazione e workflow**
