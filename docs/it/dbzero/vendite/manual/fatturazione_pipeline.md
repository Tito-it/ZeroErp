## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_pipeline`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)  
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

### ✅ Note operative

* La pipeline governa il **workflow dei lotti** (non la numerazione o i dettagli
  del documento fiscale).
* L’orchestratore legge questa tabella per decidere **quali processi** eseguire
  e come gestire il **rollback**.
* I singoli processi devono essere **idempotenti** o progettati per gestire retry.

---

{% include-markdown "signature-core.md" %}
