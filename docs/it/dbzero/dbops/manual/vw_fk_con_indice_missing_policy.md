## 📘 Documentazione Concettuale – View `dbops.vw_fk_con_indice_missing_policy`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> - [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)      
>
> Approfondimento funzioni:   
> - [dbops.vw_fk_senza_indice](/dbzero/dbops/manual/vw_fk_senza_indice)   
> - [dbops.vw_duplicate_indexes](/dbzero/dbops/manual/vw_duplicate_indexes)  

La view **`dbops.vw_fk_con_indice_missing_policy`** elenca tutte le **foreign key** che **hanno un indice** (prefisso `ix_`) ma **non** sono ancora gestite dalla tabella di policy `dbops.fk_index_policy`. Per ciascuna FK, viene suggerito il comando SQL di creazione dell’indice.

---

### 🎯 Scopo Principale

* **Identificare gli indici esistenti**
  Trova le FK già indicizzate che non dispongono di una policy dedicata.
* **Suggerimento DDL**
  Genera automaticamente la stringa `CREATE INDEX ...` per uniformare naming e struttura.
* **Supporto auditing e governance**
  Permette di scoprire eventuali indici non tracciati, inserendoli poi in `fk_index_policy`.

---

### ⚙️ Flusso di Costruzione

1. **CTE `fk_columns` e `fk_fields`**
   Estrae schema, tabella, nome del vincolo FK e lista delle colonne coinvolte.
2. **CTE `indexed_columns`**
   Elenca gli indici esistenti sulle tabelle, raggruppando le colonne per ciascun indice.
3. **CTE `fk_grouped`**
   Raggruppa le colonne di ogni FK in array ordinate.
4. **Join tra FK e indici**
   Seleziona le FK le cui colonne coincidono con un indice (array di colonne uguali).
5. **Left join su `fk_index_policy`**
   Filtra solo quelle FK **senza** entry in policy (`pol.constraint_name IS NULL`).
6. **Output**
   Restituisce:

   * `schema_name`, `table_name`, `constraint_name`
   * `fk_cols` (array delle colonne FK)
   * `index_name` (nome indice esistente)
   * `create_index_suggestion` con formato:

     ```sql
     CREATE INDEX ix_<schema>_<table>_<columns> ON <schema>.<table>(<columns>);
     ```

---

### 🔖 DDL della View

```sql
CREATE OR REPLACE VIEW dbops.vw_fk_con_indice_missing_policy AS
WITH
  fk_columns AS (...),
  fk_fields  AS (...),
  indexed_columns AS (...),
  fk_grouped AS (...)
SELECT
  fk.schema_name,
  fk.table_name,
  fk.constraint_name,
  fk.fk_cols,
  idx.index_name,
  format(
    'CREATE INDEX ix_%I_%I_%s ON %I.%I(%s);',
    fk.schema_name,
    fk.table_name,
    array_to_string(fk.fk_cols, '_'),
    fk.schema_name,
    fk.table_name,
    array_to_string(fk.fk_cols, ', ')
  ) AS create_index_suggestion
FROM fk_grouped fk
  JOIN indexed_columns idx
    ON fk.schema_name = idx.schema_name
   AND fk.table_name  = idx.table_name
   AND fk.fk_cols     = idx.indexed_cols
  LEFT JOIN dbops.fk_index_policy pol
    ON fk.schema_name     = pol.schema_name
   AND fk.table_name      = pol.table_name
   AND fk.constraint_name = pol.constraint_name
WHERE pol.constraint_name IS NULL
ORDER BY fk.schema_name, fk.table_name;

COMMENT ON VIEW dbops.vw_fk_con_indice_missing_policy IS
  'Elenco dei vincoli foreign key già indicizzati (prefisso ix_) che non sono ancora definiti in fk_index_policy';
```

---

### 💡 Vantaggi Operativi

* **Individuazione rapida**: mostra subito le FK con indice esistente ma senza policy.
* **Governance**: aiuta a mantenere `fk_index_policy` completa e aggiornata.
* **Coerenza naming**: suggerimento DDL uniforme con prefisso `ix_`.
* **Automazione**: integrabile in processi CI/CD o script di auditing.

---

> 🧠 **“Questa view facilita la scoperta di indici FK non ancora tracciati, supportando una gestione centralizzata e coerente delle policy di indicizzazione.”**
