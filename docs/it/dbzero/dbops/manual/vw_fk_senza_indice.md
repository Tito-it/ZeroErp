## 📘 Documentazione Concettuale – View `dbops.vw_fk_senza_indice`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)      
>
> Approfondimento funzioni:   
>
> * [dbops.fn_populate_fk_index_policy](/dbzero/dbops/manual/fn_populate_fk_index_policy)   
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/manual/vw_fk_con_indice_missing_policy)   
> * [dbops.vw_duplicate_indexes](/dbzero/dbops/views/vw_duplicate_indexes)     
> 
> * Catalogo dei vincoli FK in PostgreSQL (`pg_constraint`, `pg_class`, `pg_namespace`)

La view **`dbops.vw_fk_senza_indice`** elenca tutte le foreign key definite **solo negli schemi presenti in `dbops.automation_scope`** che **non hanno un indice associato** sulle colonne di riferimento, suggerendo lo statement `CREATE INDEX` corrispondente e rispettando eventuali eccezioni definite in `dbops.fk_index_policy`. La view considera anche i **vincoli UNIQUE** esistenti: se una FK e` gia` coperta da un `UNIQUE` con le stesse colonne, non viene proposta.

---

### 🎯 Scopo Principale

(latest review 16-01-26)
* Individuare automaticamente vincoli di integrità referenziale (FK) privi di indice, potenziali colli di bottiglia nelle operazioni di JOIN e DELETE.
* Fornire suggerimenti di creazione indice coerenti, facilitando l’ottimizzazione delle performance.
* Applicare eventuali policy di esclusione gestite in `dbops.fk_index_policy`.


### 🔍 Colonne e Descrizione

| Colonna                   | Descrizione                                                   |
| ------------------------- | ------------------------------------------------------------- |
| `schema_name`             | Schema in cui si trova la tabella con FK                      |
| `table_name`              | Nome della tabella che contiene la FK                         |
| `constraint_name`         | Nome del vincolo di foreign key                               |
| `fk_cols`                 | Elenco delle colonne coinvolte nella FK                       |
| `create_index_suggestion` | Statement SQL suggerito per creare l’indice su queste colonne |

---

### ⚙️ Esempi di Utilizzo

1. **Verificare FK senza indice**:

   ```sql
   SELECT *
     FROM dbops.vw_fk_senza_indice;
   ```

2. **Creare l’indice suggerito** (per la prima riga restituita):

   ```sql
   DO $$ DECLARE rec RECORD; BEGIN
     SELECT create_index_suggestion INTO rec
       FROM dbops.vw_fk_senza_indice
      LIMIT 1;
     EXECUTE rec.create_index_suggestion;
   END $$;
   ```

3. **Escludere esplicitamente un vincolo tramite policy**:

   ```sql
   INSERT INTO dbops.fk_index_policy (schema_name, table_name, constraint_name, consentito)
   VALUES ('public', 'orders', 'orders_customer_id_fkey', false);
   -- Ora la view non mostrerà più questo vincolo
   ```

---

### 💡 Vantaggi Operativi

* **Miglioramento performance**: individuazione rapida di join e delete lenti dovuti a FK senza indice.
* **Automazione**: suggerimenti pronti all’uso per l’ottimizzazione.
* **Governance**: rispetto di policy aziendali per eccezioni a indice automatico.

---

> 🧠 **“Con una view dedicata alle FK prive di indice e ai suggerimenti di creazione, si ottimizzano le query e si mantiene il controllo sulle eccezioni di policy.”**
