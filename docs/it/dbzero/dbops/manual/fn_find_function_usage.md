## 📘 Documentazione Concettuale – Function `dbops.fn_find_function_usage(p_function_name TEXT)`

> 👀 **Vedi anche**
>
> Altre view di catalogazione:  
>
> * [dbops.vw_function_list](/dbzero/dbops/manual/vw_function_list)  
> * [dbops.vw_trigger_functions](/dbzero/dbops/manual/vw_trigger_functions)  


La funzione **`dbops.fn_find_function_usage`** restituisce l’elenco delle entità del database (funzioni, trigger, event trigger) che fanno riferimento a una specifica funzione indicata dal nome, facilitando l’analisi delle dipendenze e degli impatti di modifiche o refactoring.

---

### 🎯 Scopo Principale

* **Discovery delle dipendenze**: individuare tutte le occorrenze di una funzione all’interno del codice PL/pgSQL, dei trigger e degli event trigger.
* **Supporto al refactoring**: identificare facilmente i punti di utilizzo prima di rinominare o modificare una funzione.

---

### 🔍 Firma e Restituzione

```sql
fn_find_function_usage(
  p_function_name TEXT
) RETURNS TABLE(
  object_type TEXT,   -- 'function', 'trigger' o 'event_trigger'
  schema_name TEXT,   -- schema di appartenenza (NULL per event trigger)
  object_name TEXT    -- nome dell’oggetto o firma della funzione
);
```

* **`p_function_name`**: nome della funzione da ricercare.
* **object\_type**: tipo di oggetto che invoca la funzione.
* **schema\_name**: schema in cui risiede l’oggetto (event trigger non ha schema).
* **object\_name**: per le funzioni, include firma e argomenti; per trigger/event trigger, nome dell’oggetto.

---

### ⚙️ Logica di Esecuzione

1. **Funzioni**: cerca all’interno di `pg_proc.prosrc` le dichiarazioni che contengono il nome `p_function_name`, escludendo la funzione stessa.
2. **Trigger**: individua i trigger definiti in `pg_trigger` che richiamano la funzione `p_function_name`.
3. **Event Trigger**: include gli event trigger di `pg_event_trigger` associati a `p_function_name`.

I risultati di ciascuna ricerca vengono uniti con `UNION ALL` e restituiti in un unico set.

---

### ⚙️ Esempi di Utilizzo

1. **Ricerca generale di dipendenze**

   ```sql
   SELECT *
     FROM dbops.fn_find_function_usage('process_order');
   ```

2. **Filtrare solo i trigger**

   ```sql
   SELECT schema_name, object_name
     FROM dbops.fn_find_function_usage('audit_update')
    WHERE object_type = 'trigger';
   ```

3. **Contare le dipendenze per schema**

   ```sql
   SELECT object_type, schema_name, COUNT(*) AS usage_count
     FROM dbops.fn_find_function_usage('compute_tax')
    GROUP BY object_type, schema_name;
   ```

---

### 💡 Vantaggi Operativi

* **Chiarezza delle dipendenze**: evita ricerche manuali tra cataloghi multipli.
* **Riduzione degli errori**: garantisce che nessun utilizzo venga trascurato in fase di modifica.
* **Automazione**: integrabile in script di migrazione o refactoring per validare l’assenza di riferimenti obsoleti.

---

> 🧠 **“Con `fn_find_function_usage`, refactoring e manutenzione del codice PL/pgSQL diventano operazioni sicure e documentate, grazie all’individuazione automatica delle dipendenze.”**
