## 📘 Documentazione Concettuale – View `dbops.vw_fk_senza_indice`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> - [dbops.fk_index_policy](\dbzero\dbops\tabelle\fk_index_policy)      
>
> Approfondimento funzioni:   
> - [dbops.fn_populate_fk_index_policy](\dbzero\dbops\manual\fn_populate_fk_index_policy)   
> - [dbops.vw_fk_senza_indice](\dbzero\dbops\manual\vw_fk_con_indice_missing_policy)   
> - [dbops.vw_duplicate_indexes](\dbzero\dbops\manual\vw_duplicate_indexes)  
> 
> * Catalogo dei vincoli FK in PostgreSQL (`pg_constraint`, `pg_class`, `pg_namespace`)

La view **`dbops.vw_fk_senza_indice`** elenca tutte le foreign key definite negli schemi monitorati che **non hanno un indice associato** sulle colonne di riferimento, suggerendo lo statement `CREATE INDEX` corrispondente e rispettando eventuali eccezioni definite in `dbops.fk_index_policy`.

---

### 🎯 Scopo Principale

* Individuare automaticamente vincoli di integrità referenziale (FK) privi di indice, potenziali colli di bottiglia nelle operazioni di JOIN e DELETE.
* Fornire suggerimenti di creazione indice coerenti, facilitando l’ottimizzazione delle performance.
* Applicare eventuali policy di esclusione gestite in `dbops.fk_index_policy`.

---

### 🔍 Definizione (DDL)

```sql
CREATE OR REPLACE VIEW dbops.vw_fk_senza_indice AS
WITH fk_columns AS (
  SELECT con.oid AS constraint_oid,
         con.conname AS constraint_name,
         nsp.nspname AS schema_name,
         rel.relname AS table_name,
         unnest(con.conkey) AS attnum,
         con.conrelid
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
   WHERE con.contype = 'f'
), fk_fields AS (
  SELECT fk.constraint_name,
         fk.schema_name,
         fk.table_name,
         a.attname AS column_name,
         fk.conrelid,
         fk.constraint_oid
    FROM fk_columns fk
    JOIN pg_attribute a ON a.attrelid = fk.conrelid AND a.attnum = fk.attnum
), indexed_columns AS (
  SELECT i.relname AS index_name,
         n.nspname AS schema_name,
         t.relname AS table_name,
         array_agg(a.attname ORDER BY x.ordinality) AS indexed_cols
    FROM pg_index ix
    JOIN pg_class i ON i.oid = ix.indexrelid
    JOIN pg_class t ON t.oid = ix.indrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY x(attnum, ordinality) ON true
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = x.attnum
GROUP BY i.relname, n.nspname, t.relname
), fk_grouped AS (
  SELECT fk.constraint_name,
         fk.schema_name,
         fk.table_name,
         array_agg(fk.column_name ORDER BY fk.column_name) AS fk_cols
    FROM fk_fields fk
GROUP BY fk.constraint_name, fk.schema_name, fk.table_name
)
SELECT
  fk.schema_name,
  fk.table_name,
  fk.constraint_name,
  fk.fk_cols,
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
LEFT JOIN indexed_columns idx
  ON fk.schema_name = idx.schema_name
 AND fk.table_name  = idx.table_name
 AND fk.fk_cols      = idx.indexed_cols
LEFT JOIN dbops.fk_index_policy pol
  ON fk.schema_name     = pol.schema_name
 AND fk.table_name      = pol.table_name
 AND fk.constraint_name = pol.constraint_name
WHERE idx.index_name IS NULL
  AND COALESCE(pol.consentito, true) = true
ORDER BY fk.schema_name, fk.table_name;
```

**Owner**: `postgres`

**Commento**: "Elenco delle foreign key senza indice esplicito, con suggerimento CREATE INDEX e rispetto policy da dbops.fk\_index\_policy"

---

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
