## 📘 Documentazione Funzione –  `dbops.trgfn_child_requires_active_parent`

---

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [`script.fn_log_and_raise_error`](/dbzero/dbops/funzioni/fn_log_and_raise_error)
> * [`script.fn_log_error_only`](/dbzero/dbops/funzioni/fn_log_error_only)
>
> Approfondimento tabelle:
>
> * [`dbops.error_log`](/dbzero/dbops/tabelle/error_log)
> * [`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl)

---

### 🎯 Scopo Principale

La funzione **`trgfn_child_requires_active_parent`** è un **trigger function** che impedisce l’attivazione di un record figlio se il relativo record padre non è attivo. Garantisce la coerenza dei dati in scenari in cui l’attributo `attivo` è vincolante per le relazioni.

---

### 📝 Dettagli

* **Firma**

  ```sql
  CREATE OR REPLACE FUNCTION dbops.trgfn_child_requires_active_parent()
  RETURNS trigger
  LANGUAGE plpgsql
  ```

* **Parametri (TG_ARGV)**

  1. `parent_schema` – schema della tabella padre
  2. `parent_table` – nome tabella padre
  3. `parent_attivo_col` – colonna di stato attivo nella tabella padre
  4. `fk_col` – colonna di FK nella tabella figlia
  5. `[parent_pk_col]` – colonna PK del padre (default = `id`)

* **Logica interna**

  * Se `NEW.attivo` non è `TRUE`, la funzione non applica controlli.
  * Estrae il valore della FK da `NEW`.
  * Se FK è `NULL` e il figlio è attivo → errore (`fn_log_and_raise_error`).
  * Ricava il tipo della PK del padre interrogando `pg_attribute`.
  * Costruisce ed esegue query per verificare:

    1. **Esistenza del padre**.
    2. **Stato attivo del padre**.
  * Se il padre manca o non è attivo → errore bloccante.
  * Usa `fn_log_error_only` per warning non bloccanti (es. uso PK di default).

* **Ritorno**: `trigger` → `NEW` (se i controlli sono superati).

---

### 🔧 Utilizzo tipico

1. Prevenire l’inserimento/aggiornamento di figli attivi con padre non attivo.
2. Garantire consistenza in domini gerarchici (es. `gestori` → `soggetti figlio`).
3. Applicato come **BEFORE INSERT/UPDATE** su tabelle figlie.

---

### 📊 Collegamento con automazione

* Può essere attivato da regole in `automation_rules_tbl`.
* Si integra con il sistema di **error logging** (`error_log`) e **audit**.
* Usa le funzioni standard di logging (`fn_log_and_raise_error`, `fn_log_error_only`) per coerenza.

---

### 💡 Esempio pratico

Creare trigger che impone la presenza di un padre attivo in `anagrafiche.soggetti`:

```sql
CREATE TRIGGER trg_child_active_requires_parent
BEFORE INSERT OR UPDATE ON anagrafiche.soggetti_figli
FOR EACH ROW
EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(
  'anagrafiche',
  'soggetti',
  'attivo',
  'soggetto_id'
);
```

➡️ Se `NEW.attivo = true` e il padre `soggetti.attivo` ≠ true, l’operazione viene bloccata con errore.

---

> 🧠 **In sintesi**: `trgfn_child_requires_active_parent` è un trigger function che rafforza le regole di business assicurando che **nessun figlio attivo esista senza un padre attivo**, centralizzando i controlli e uniformando la gestione degli errori.
