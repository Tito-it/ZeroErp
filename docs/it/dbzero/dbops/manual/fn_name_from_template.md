## 📘 Documentazione Funzione –  `dbops.fn_name_from_template`

---

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [`dbops.fn_run_automations`](/dbzero/dbops/funzioni/fn_run_automations)   
> * [`dbops.fn_run_automations_tx_id`](/dbzero/dbops/funzioni/fn_run_automations_tx_id)    
> * [`dbops.fn_run_automations_storico_provision`](/dbzero/dbops/funzioni/fn_run_automations_storico_provision)   
>
> Approfondimento tabelle:
>
> * [`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl)  
> * [`dbops.automation_overrides_cols`](/dbzero/dbops/tabelle/automation_overrides_cols)   

---

### 🎯 Scopo Principale

La funzione **`fn_name_from_template`** genera in modo consistente un **nome normalizzato** (per trigger, constraint, indici, ecc.) a partire da un **template testuale** con *placeholder* e da un set di parametri (schema, tabella, parent/child, nome FK, operazione).

---

### 📝 Dettagli

**Firma**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_name_from_template(
  p_template text,
  p_schema   text,
  p_table    text,
  p_parent   text DEFAULT NULL,
  p_child    text DEFAULT NULL,
  p_fk       text DEFAULT NULL,
  p_op       text DEFAULT NULL
) RETURNS text
```

**Comportamento**

* Applica sostituzioni nel template per i placeholder:

  * `{schema}`, `{table}`, `{parent}`, `{child}`, `{fk}`, `{op}`.
* Supporta *hash opzionale* basato su `p_fk`:

  * `{fkhash6}` → sostituito sempre con i **primi 6** caratteri dell’**hash** di `p_fk` (se `p_fk` è valorizzato).
  * `{fkhash6_if_long}` → sostituito con lo stesso hash **solo se** il nome risultante supera **63** caratteri; altrimenti rimosso.
* Normalizza il risultato finale:

  * comprime **underscore** ripetuti in singolo `_`;
  * rimuove underscore **iniziali/finali**.
* **Guard 63 caratteri**: se la stringa risultante è ancora > 63, viene troncata e arricchita con un **hash stabile** di 6 caratteri (`…_hhhhhh`).

**Valore di ritorno**

* `text` – nome generato conforme a regole di lunghezza e normalizzazione PostgreSQL.

---

### 🔧 Utilizzo tipico

1. **Naming di trigger**: es. `trg_{table}_{op}_{fkhash6_if_long}`.
2. **Naming FK**: es. `fk_{child}_{parent}{fkhash6_if_long}` per evitare collisioni su nomi lunghi/composti.
3. **Naming indici**: es. `ix_{table}_{fk}_fk{fkhash6_if_long}`.
4. **Standardizzazione** in automazioni: produrre nomi deterministici a partire da regole in `automation_rules_tbl`.

---

### 📊 Collegamento con automazione

La funzione è usata dai processi di automazione (es. `fn_run_automations`, gruppi *TX_ID*, *ATTIVO*, *STORICO*, *FK_NAMING*) per:

* generare nomi **coerenti e ripetibili**;
* prevenire errori di lunghezza o duplicazioni;
* codificare in maniera compatta informazioni rilevanti (es. *hash* della FK) quando richiesto.

---

### 💡 Esempi pratici

**1) Nome trigger UPDATE con hash condizionale**

```sql
SELECT dbops.fn_name_from_template(
  'trg_{table}_upd_{fkhash6_if_long}',
  'anagrafiche',
  'soggetti',
  NULL,
  NULL,
  'soggetto_id',
  'UPD'
);
-- → es. "trg_soggetti_upd" oppure "trg_soggetti_upd_ab12cd" se > 63 char
```

**2) Nome vincolo FK deterministico**

```sql
SELECT dbops.fn_name_from_template(
  'fk_{child}_{parent}{fkhash6_if_long}',
  'anagrafiche',
  'contatti',
  'soggetti',   -- parent
  'contatti',   -- child
  'soggetto_id',
  NULL
);
-- → es. "fk_contatti_soggetti" (o con hash se nome lungo)
```

**3) Nome indice supporto FK**

```sql
SELECT dbops.fn_name_from_template(
  'ix_{table}_{fk}_fk{fkhash6_if_long}',
  'config',
  'stradario',
  NULL,
  NULL,
  'toponomastica_id',
  NULL
);
-- → es. "ix_stradario_toponomastica_id_fk"
```

---

> 🧠 **In sintesi**: `fn_name_from_template` fornisce un **contratto di naming** chiaro e robusto per tutti gli oggetti DDL generati dall’automazione, con gestione integrata di lunghezza massima, underscore e collisioni tramite *hash* coerente.
