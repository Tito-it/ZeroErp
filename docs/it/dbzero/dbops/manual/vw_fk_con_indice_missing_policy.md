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
> [dbops.fn_seed_fk_index_policy](/dbzero/dbops/funzioni/fn_seed_fk_index_policy)  
> [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy)  

La view **`dbops.vw_fk_con_indice_missing_policy`** elenca le **foreign key** che **hanno già un indice dedicato** ma **non** sono ancora gestite dalla tabella di policy `dbops.fk_index_policy`, limitandosi **agli schemi presenti in `dbops.automation_scope`**. Per ciascuna FK riporta il nome dell'indice trovato e il comando che lo ricrea.

È la view che `fn_seed_fk_index_policy()` legge per **portare sotto governo** indici già esistenti, registrandoli con `consentito = true`.

---
### 🎯 Scopo Principale
(latest review 27-07-26)

* **Identificare gli indici esistenti**
  Trova le FK già indicizzate che non dispongono di una policy dedicata.
* **Suggerimento DDL fedele**
  Genera la stringa `CREATE INDEX ...` che ricrea **quell'indice**, con il suo nome reale.
* **Supporto auditing e governance**
  Permette di scoprire indici non tracciati e inserirli in `fk_index_policy`.

---

### ⚠️ Questa view fabbricava indici duplicati

Fino al 27-07-2026 la view esponeva `index_name` — il nome **reale** dell'indice trovato — ma poi costruiva `create_index_suggestion` **sintetizzando un nome diverso**, con la vecchia convenzione `ix_<schema>_<tabella>_<colonne>` abbandonata mesi prima in favore di `ix_<tabella>_<colonne>`.

La conseguenza: `fn_seed_fk_index_policy()` registrava in policy un comando che creava un **secondo** indice, identico al primo ma con un altro nome. Al primo `CALL apply_fk_index_policy()` l'indice gemello nasceva.

> È così che un indice rimosso a gennaio è ricomparso a luglio senza che alcun changeSet lo creasse. Non era stato scritto a mano: lo aveva rigenerato la catena view → `fn_seed` → `apply`.

Adesso il comando usa il **nome reale** e le **colonne nell'ordine reale**: descrive l'indice che c'è, non uno inventato. Con `IF NOT EXISTS`, rieseguirlo è un no-op.

---

### 🔒 Si propongono solo indici DEDICATI

Non basta che un indice copra la FK: deve essere un indice che la policy possa **legittimamente possedere**. Sono quindi esclusi gli indici che:

| Esclusione | Perché |
| --- | --- |
| hanno colonne in più rispetto alla FK | è un indice che serve anche ad altro; la policy non può rivendicarlo |
| sono `UNIQUE` o `PRIMARY KEY` | impongono integrità, non sono solo acceleratori |
| sostengono un constraint (`pg_constraint.conindid`) | il `DROP` fallirebbe o porterebbe via il vincolo |
| sono la `REPLICA IDENTITY` | droparli rompe la replica |
| sono parziali o su espressioni | la policy sa creare solo indici totali su colonne: se droppati, non saprebbe ricrearli uguali |

Il motivo è tutto nel ramo `consentito = false` di `apply_fk_index_policy()`, che estrae il nome dal comando ed esegue `DROP INDEX`. **Un flag booleano deve poter togliere solo un acceleratore, mai un vincolo.**

Un primo tentativo di correzione — far puntare il comando al nome reale, qualunque esso fosse — è stato scartato proprio per questo: produceva righe come

```sql
CREATE INDEX IF NOT EXISTS uq_fatture_r_iva_key ON vendite.fatture_riepiloghi_iva(fattura_id);
```

innocue in creazione, letali con `consentito = false`.

Le FK coperte da un indice più largo o da una `UNIQUE` semplicemente **non si propongono più**: non c'è nulla da governare, e un indice dedicato sarebbe ridondante. È la stessa nozione di copertura di [vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice), applicata coerentemente.

---

### Flusso di Costruzione

1. **CTE `fk_grouped`**
   Estrae schema, tabella, nome del vincolo FK e l'insieme ordinato delle colonne coinvolte.
2. **CTE `idx_dedicati`**
   Elenca i soli indici che la policy può possedere: btree, validi, totali, senza `INCLUDE`, non unique, non PK, non replica identity, non a supporto di constraint.
3. **Join tra FK e indici dedicati**
   Accoppia quando l'insieme delle colonne chiave dell'indice **coincide** con quello della FK.
4. **Left join su `fk_index_policy`**
   Filtra solo le FK **senza** entry in policy (`pol.constraint_name IS NULL`).
5. **Output**

   * `schema_name`, `table_name`, `constraint_name`
   * `fk_cols` (array delle colonne FK)
   * `index_name` (nome reale dell'indice esistente)
   * `create_index_suggestion`:

     ```sql
     CREATE INDEX IF NOT EXISTS <index_name> ON <schema>.<table>(<colonne nell'ordine reale>);
     ```

---

### Vantaggi Operativi

* **Individuazione rapida**: mostra subito le FK con indice dedicato ma senza policy.
* **Governance**: aiuta a mantenere `fk_index_policy` completa e aggiornata.
* **Nessun gemello**: il comando nomina l'indice che esiste, quindi registrarlo non ne crea un secondo.
* **Sicurezza**: nessuna riga registrata può portare `apply` a droppare un vincolo di integrità.
* **Automazione**: integrabile in processi CI/CD o script di auditing.

---

> **“Questa view facilita la scoperta di indici FK non ancora tracciati, supportando una gestione centralizzata e coerente delle policy di indicizzazione.”**
