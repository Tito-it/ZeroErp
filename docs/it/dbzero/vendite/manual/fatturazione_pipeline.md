## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_pipeline`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)  
>
**Approfondimento funzioni:**
>
• [`backend.fn_execute_pipeline_step`](/backend/vendite/funzioni/fn_execute_pipeline_step)   
> • [`vendite.fn_select_attivita_fatturabili`](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili)  
>
### 🎯 Scopo Principale
(latest review 24-11-2026)  
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

### Regole principali

* `stato_doc_fiscale_id` collega lo step agli **stati lotto** (non agli stati fattura).
* `tipo_lotto` distingue pipeline MASSIVO vs GIORNALIERO.
* `utility_id` e `tipo_doc_fiscale_id` sono opzionali e permettono varianti specifiche.
* `processi` contiene una lista di “task” tecnici da eseguire (payload jsonb).
* `rollback` contiene le azioni di pulizia per tornare allo stato precedente.
* Solo gli step con `attivo=true` vengono eseguiti dalla pipeline.
* `auto_step_rollback` accende il rollback automatico della corsia: al rilancio di un lotto in
  errore il runner esegue da solo il `rollback` dello step, se
  `vendite.fn_check_rollback_step_automatico` lo ammette (rollback non vuoto, nessun task
  distruttivo, spento o sconosciuto). Default false. La chiave `auto_step_rollback` nel `meta` è
  rifiutata (`chk_fatturazione_pipeline_meta_senza_auto_step_rollback`): la sede è la colonna.
  Test: `db/pgtap/vendite/test-rollback-step-automatico-v1.sql`.

---

### Struttura di `processi` e `rollback`

Le colonne `processi` e `rollback` sono **jsonb** e contengono una lista di step
tecnici. Esempio (schema indicativo):

```json
[
  { "task": "select_attivita", "params": {"lock": true} },
  { "task": "generate_righe", "params": {"mode": "standard"} }
]
```

---

### Esempi

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

### Note operative

* La pipeline governa il **workflow dei lotti**; nel modello corrente la
  numerazione e` prevista nello step `DEFINITIVA`.
* L’orchestratore legge questa tabella per decidere **quali processi** eseguire
  e come gestire il **rollback**.
* I singoli processi devono essere **idempotenti** o progettati per gestire retry.
* I task eseguiti sono gestiti dal runtime Django (`PipelineStepExecutor`) tramite
  whitelist (es. `select_attivita`, `genera_fondi_source_lotto`,
  `applica_fondi_lotto`, `ricalcola_iva_lotto`, `prepare_sdi_payload_lotto`, `numera_fatture`,
  `noop`, `log_only`).
* Nessuna pipeline del seed ha un `rollback` (tutti `[]`): il task `reset_lotto_draft`, che
  era il rollback dello step `EMESSA` della corsia `MASSIVO`, e` ritirato dal 2026-11-24.
  L'annullo del lotto e` il verbo `vendite.fn_annulla_lotto_da_draft`, dall'endpoint.
  Un task nominato nel `rollback` deve essere registrato e avere la sua policy, come quelli
  dei `processi` (`test-pipeline-processi-invariante-v1.sql`, test 8 e 9).
* Nel flusso `MASSIVO`, lo step `EMESSA` include il ciclo:
  source fondi -> applicazione fondi -> ricalcolo IVA/totali.
  La numerazione resta nello step `DEFINITIVA`.
* Lo step `INVIATA` del massivo prepara il payload SDI di lotto e apre/riusa
  i tentativi in `vendite.fatture_sdi`.
* Risoluzione configurazione con fallback (per `tipo_lotto + stato_doc_fiscale_id`):
  * 1) match esatto `utility_id + tipo_doc_fiscale_id`
  * 2) match `utility_id` con `tipo_doc_fiscale_id = NULL`
  * 3) match `tipo_doc_fiscale_id` con `utility_id = NULL`
  * 4) fallback globale `utility_id = NULL` e `tipo_doc_fiscale_id = NULL`
* Ogni livello e` unico per evitare ambiguita` di configurazione.

* **Regola di sicurezza: i task devono usare **solo `lotto_id`** come input; i parametri operativi devono essere recuperati dal lotto (o da tabelle collegate).**


---

{% include-markdown "signature-core.md" %}
