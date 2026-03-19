## 📘 Documentazione Concettuale – View `dbops.vw_fk_con_indice_missing_policy`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:   
>
[dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)      
>
Approfondimento funzioni:   
>
[dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice)    
> [dbops.vw_duplicate_indexes](/dbzero/dbops/views/vw_duplicate_indexes)    

La view **`dbops.vw_fk_con_indice_missing_policy`** elenca tutte le **foreign key** che **hanno un indice** (prefisso `ix_`) ma **non** sono ancora gestite dalla tabella di policy `dbops.fk_index_policy`, limitandosi **agli schemi presenti in `dbops.automation_scope`**. Per ciascuna FK, viene suggerito il comando SQL di creazione dell’indice.

---
### 🎯 Scopo Principale
(latest review 16-01-26)
* **Identificare gli indici esistenti**
  Trova le FK già indicizzate che non dispongono di una policy dedicata.
* **Suggerimento DDL**
  Genera automaticamente la stringa `CREATE INDEX ...` per uniformare naming e struttura.
* **Supporto auditing e governance**
  Permette di scoprire eventuali indici non tracciati, inserendoli poi in `fk_index_policy`.

---

### Flusso di Costruzione

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

### Vantaggi Operativi

* **Individuazione rapida**: mostra subito le FK con indice esistente ma senza policy.
* **Governance**: aiuta a mantenere `fk_index_policy` completa e aggiornata.
* **Coerenza naming**: suggerimento DDL uniforme con prefisso `ix_`.
* **Automazione**: integrabile in processi CI/CD o script di auditing.

---

> **“Questa view facilita la scoperta di indici FK non ancora tracciati, supportando una gestione centralizzata e coerente delle policy di indicizzazione.”**
