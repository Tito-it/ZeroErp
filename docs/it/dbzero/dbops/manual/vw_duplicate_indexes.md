## 📘 Documentazione Concettuale – View `dbops.vw_duplicate_indexes`

> 👀 **Vedi anche**
>
> Approfondimento funzioni:   
> - [dbops.vw_fk_senza_indice](/dbzero/dbops/manual/vw_fk_senza_indice)   
> - [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/manual/vw_fk_con_indice_missing_policy)     

La view **`dbops.vw_duplicate_indexes`** identifica gli **indici duplicati** all’interno dello stesso schema e tabella, cioè quegli indici che coprono esattamente lo stesso insieme di colonne (`cols`). Per ciascun gruppo di colonne con più indici, la view restituisce i nomi degli indici coinvolti e il numero totale di occorrenze.

---

### 🎯 Scopo Principale

* **Individuare indici ridondanti**
  Scoprire indici che hanno lo stesso set di colonne e possono quindi essere unificati o rimossi.
* **Ottimizzazione dello storage e delle performance**
  Ridurre overhead di manutenzione e migliorare le prestazioni di scrittura eliminando duplicazioni.
* **Governance della struttura**
  Supportare analisi periodiche per mantenere lo schema pulito e coerente.

---

### ⚙️ Flusso di Costruzione

1. **CTE `index_cols`**

   * Estrae da `pg_index` le informazioni sugli indici:

     * `index_oid`, `schema_name`, `table_name`, `index_name`
     * Flag `is_unique`, `is_primary`
     * Array `cols` con i nomi delle colonne indicizzate (ordinati).
   * Filtra fuori gli indici primari (`indisprimary`) e considera solo gli indici di tipo `i`.
2. **Aggregazione e raggruppamento**

   * Raggruppa per `schema_name`, `table_name` e `cols`.
   * Calcola:

     * `duplicate_index_names`: array dei nomi degli indici che condividono le colonne.
     * `count_of_indexes`: conteggio degli indici nel gruppo.
   * Applica `HAVING count(*) > 1` per ottenere solo i gruppi con più di un indice.

---

### 🔖 DDL della View

```sql
CREATE OR REPLACE VIEW dbops.vw_duplicate_indexes AS
WITH index_cols AS (
  SELECT
    i.oid                    AS index_oid,
    n.nspname                AS schema_name,
    t.relname                AS table_name,
    i.relname                AS index_name,
    ix.indisunique           AS is_unique,
    ix.indisprimary          AS is_primary,
    array_agg(a.attname ORDER BY x.ordinality) AS cols
  FROM pg_index ix
  JOIN pg_class i    ON i.oid = ix.indexrelid
  JOIN pg_class t    ON t.oid = ix.indrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY x(attnum, ordinality) ON true
  JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = x.attnum
  WHERE NOT ix.indisprimary    -- escludi indici PK
    AND i.relkind = 'i'         -- solo indici
  GROUP BY i.oid, n.nspname, t.relname, i.relname, ix.indisunique, ix.indisprimary
)
SELECT
  schema_name,
  table_name,
  cols                 AS index_columns,
  array_agg(index_name) AS duplicate_index_names,
  count(*)             AS count_of_indexes
FROM index_cols
GROUP BY schema_name, table_name, cols
HAVING count(*) > 1
ORDER BY schema_name, table_name, count_of_indexes DESC;

COMMENT ON VIEW dbops.vw_duplicate_indexes IS
  'Elenca gli indici duplicati (stesso insieme di colonne) per schema e tabella, mostrando i nomi degli indici e il conteggio.';
```

---

### 💡 Vantaggi Operativi

* **Riduzione di ridondanze**: facilita la rimozione di indici duplicati per liberare spazio e ridurre costi di manutenzione.
* **Chiarezza**: fornisce un elenco immediato dei gruppi di indici da esaminare.
* **Automazione**: utile in script di auditing o pulizia periodica.

---

> 🧠 **“Con `vw_duplicate_indexes`, tenere sotto controllo gli indici duplicati diventa semplice, supportando azioni di consolidamento per ottimizzare il database.”**
