## 📘 Documentazione Concettuale – Function `dbops.fn_search_column_usage(p_column_name TEXT)`

> 👀 **Vedi anche**
>
> * Catalogo delle view (`pg_catalog.pg_views`, `pg_catalog.pg_matviews`)
> * Catalogo delle funzioni e regole (`pg_catalog.pg_proc`, `pg_catalog.pg_rules`)
> * Constraint system (`pg_catalog.pg_constraint`)

La funzione **`dbops.fn_search_column_usage`** consente di ricercare riferimenti a un determinato nome di colonna all’interno di viste, materialized view, regole, funzioni e vincoli, restituendo il tipo di oggetto, lo schema e il nome dell’oggetto che la contiene.

---

### 🎯 Scopo

* Individuare rapidamente tutte le occorrenze di un campo in definizioni SQL presenti nel database.
* Facilitare attività di refactoring, pulizia del codice, e verifica di dipendenze tra oggetti del database.

---

### 🔍 Parametri e Firma

```sql
fn_search_column_usage(
  p_column_name TEXT
) RETURNS TABLE(
  object_type TEXT,
  schema_name TEXT,
  object_name TEXT
)
LANGUAGE sql
STABLE
ROWS 1000;
```

* **`p_column_name`**: nome della colonna (o frammento) da ricercare nelle definizioni.
* **Return**: una tabella con i seguenti campi:

  * `object_type`: tipo di oggetto (`view`, `materialized_view`, `rule`, `function`, `constraint`)
  * `schema_name`: schema di appartenenza dell’oggetto
  * `object_name`: nome dell’oggetto in cui viene utilizzata la colonna

---

### ⚙️ Logica e Flusso di Esecuzione

1. **Viste Standard** (`pg_views`): cerca la stringa in `definition` per individuare colonne referenziate.
2. **Materialized Views** (`pg_matviews`): analogamente alle view.
3. **Regole** (`pg_rules`): verifica il testo delle regole.
4. **Funzioni** (`pg_proc`): esamina il sorgente PL/pgSQL (`prosrc`).
5. **Constraint di Check** (`pg_constraint`): controlla la condizione BOOLEAN (`conbin`).

Tutti i risultati vengono uniti (`UNION ALL`) e restituiti come un unico set.

---

### 🔍 Esempi di Utilizzo

1. **Ricerca generica**

   ```sql
   SELECT *
     FROM dbops.fn_search_column_usage('customer_id');
   ```

   Restituisce tutte le view, funzioni, regole e vincoli che contengono la stringa `customer_id`.

2. **Filtrare solo le funzioni**

   ```sql
   SELECT schema_name, object_name
     FROM dbops.fn_search_column_usage('amount')
    WHERE object_type = 'function';
   ```

3. **Verificare vincoli che utilizzano un campo**

   ```sql
   SELECT schema_name, object_name
     FROM dbops.fn_search_column_usage('status')
    WHERE object_type = 'constraint';
   ```

4. **Esempio in contesto di refactoring**

   ```sql
   -- Trovare tutte le dipendenze di 'data_insert'
   WITH deps AS (
     SELECT *
       FROM dbops.fn_search_column_usage('data_insert')
   )
   SELECT * FROM deps;
   -- Procedi ad aggiornare o eliminare i riferimenti identificati
   ```

---

### 💡 Vantaggi Operativi

* **Refactoring sicuro**: individua tutte le dipendenze di un campo prima di rinominarlo o rimuoverlo.
* **Documentazione**: mappa le dipendenze tra oggetti di database per audit e analisi.
* **Efficienza**: evita di ispezionare manualmente definizioni distribuite in più cataloghi.

---

> 🧠 **“Con `fn_search_column_usage` è possibile gestire in modo centralizzato l’analisi degli utilizzi di un campo, semplificando manutenzione e refactoring a livello di schema.”**
