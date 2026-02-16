## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_pipeline`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)  
>
>
> **Approfondimento funzioni:**
>
> • [`vendite.fn_execute_pipeline_step`](/dbzero/vendite/funzioni/fn_execute_pipeline_step)   
> • [`vendite.fn_select_attivita_fatturabili`](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili)  
>
---

### 🎯 Scopo Principale

(latest review 28-01-2026)  
La tabella **`vendite.fatturazione_pipeline`** descrive la **pipeline configurabile**
dei processi di fatturazione.  
Ogni riga rappresenta uno **step** logico (coerente con gli stati lotto definiti
in `config.stati_doc_fiscale`, limitati alla parte *lotti*), e definisce:

* i **processi** da eseguire nello step,
* le **azioni di rollback/cleanup** in caso di ritorno allo step precedente.

Questa struttura permette di avere una **procedura orchestratrice** configurabile
che esegue i processi secondo la pipeline, riducendo hard‑coding e facilitando
evoluzioni (nuovi step o processi senza refactor massivo).

---

### ✅ Regole principali

* `stato_doc_fiscale_id` collega lo step agli **stati lotto** (non agli stati fattura).
* `tipo_lotto` distingue pipeline MASSIVO vs GIORNALIERO.
* `utility_id` e `tipo_doc_fiscale_id` sono opzionali e permettono varianti specifiche.
* `processi` contiene una lista di “task” tecnici da eseguire (payload jsonb).
* `rollback` contiene le azioni di pulizia per tornare allo stato precedente.
* Solo gli step con `attivo=true` vengono eseguiti dalla pipeline.

---

### 🧩 Struttura di `processi` e `rollback`

Le colonne `processi` e `rollback` sono **jsonb** e contengono una lista di step
tecnici. Esempio (schema indicativo):

```json
[
  { "task": "select_attivita", "params": {"lock": true} },
  { "task": "generate_righe", "params": {"mode": "standard"} }
]
```

---

### 🧪 Esempi

**Pipeline per stato CALCOLO (esempio base)**

```json
[
  { "task": "select_attivita", "fase": "Caricamento lista attivita", "params": {"lock": true} },
  { "task": "validate_attivita", "fase": "Validazioni preliminari", "params": {} }
]
```

**Override funzione (opzionale)**

```json
[
  {
    "task": "select_attivita",
    "fase": "Caricamento lista attivita",
    "params": {"lock": true, "fn": "vendite.fn_select_attivita_fatturabili"}
  }
]
```

**Rollback per stato CALCOLO**

```json
[
  { "task": "unlock_attivita", "fase": "Sblocco righe", "params": {} }
]
```

**Pipeline per stato BOZZA**

```json
[
  { "task": "generate_righe", "fase": "Generazione righe fattura", "params": {"mode": "standard"} },
  { "task": "apply_note", "fase": "Aggancio note su righe", "params": {} }
]
```

---

### ✅ Note operative

* La pipeline governa il **workflow dei lotti**; nel modello corrente la
  numerazione e` prevista nello step `DEFINITIVA`.
* L’orchestratore legge questa tabella per decidere **quali processi** eseguire
  e come gestire il **rollback**.
* I singoli processi devono essere **idempotenti** o progettati per gestire retry.
* I task eseguiti sono gestiti da `vendite.fn_execute_pipeline_step` tramite
  whitelist (es. `select_attivita`, `genera_fondi_source_lotto`,
  `applica_fondi_lotto`, `ricalcola_iva_lotto`, `numera_fatture`,
  `reset_lotto_draft`, `noop`, `log_only`).
* Il reset tecnico in pipeline e` previsto solo per il flusso `MASSIVO`
  (sezione `rollback` dello step `EMESSA`).
* Nel flusso `MASSIVO`, lo step `EMESSA` include il ciclo:
  source fondi -> applicazione fondi -> ricalcolo IVA/totali.
  La numerazione resta nello step `DEFINITIVA`.
* Risoluzione configurazione con fallback (per `tipo_lotto + stato_doc_fiscale_id`):
  * 1) match esatto `utility_id + tipo_doc_fiscale_id`
  * 2) match `utility_id` con `tipo_doc_fiscale_id = NULL`
  * 3) match `tipo_doc_fiscale_id` con `utility_id = NULL`
  * 4) fallback globale `utility_id = NULL` e `tipo_doc_fiscale_id = NULL`
* Ogni livello e` unico per evitare ambiguita` di configurazione.

* **Regola di sicurezza: i task devono usare **solo `lotto_id`** come input; i parametri operativi devono essere recuperati dal lotto (o da tabelle collegate).**


---

{% include-markdown "signature-core.md" %}
