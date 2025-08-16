## 📘 Documentazione Concettuale – View `dbops.vw_function_list`

> 👀 **Vedi anche**
>
> * Catalogo funzioni PostgreSQL (`pg_proc`, `pg_namespace`, `pg_description`)   
>
> Altre view di catalogazione:
>  
> * [dbops.vw_catalogo_oggetti](/dbzero/dbops/manual/vw_catalogo_oggetti)  

La view **`dbops.vw_function_list`** fornisce un inventario completo delle funzioni definite negli schemi **`dbops`** e **`script`**, mostrando firma, tipo di ritorno, numero di parametri e commenti associati.

---

### 🎯 Scopo Principale

* Agevolare il **discovery** delle funzioni personalizzate per manutenzione e documentazione.
* Rendere immediatamente disponibili:

  * OID (per gestire overload)
  * Lista degli argomenti
  * Tipo di ritorno
  * Numero di parametri
  * Commenti descrittivi

---

### 🔍 Definizione (DDL)

```sql
CREATE OR REPLACE VIEW dbops.vw_function_list AS
SELECT
  n.nspname                             AS schema,
  p.oid                                 AS function_oid,
  p.proname                             AS function_name,
  pg_get_function_arguments(p.oid)     AS arguments,
  pg_get_function_result(p.oid)        AS return_type,
  array_length(
    string_to_array(
      pg_get_function_arguments(p.oid), ','
    ), 1
  )                                      AS num_args,
  d.description                        AS comment
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
LEFT JOIN pg_description d ON p.oid = d.objoid
WHERE n.nspname = ANY (ARRAY['dbops', 'script']);
```

**Owner**: `postgres`

**Commento**: "Elenco completo delle funzioni negli schemi dbops e script. Include:

* OID per identificare overload
* Argomenti e tipo di ritorno
* Numero di argomenti
* Commenti/documentazione (se presenti)"

---

### 🔍 Colonne e Significato

| Colonna         | Descrizione                                                                       |
| --------------- | --------------------------------------------------------------------------------- |
| `schema`        | Schema di appartenenza della funzione                                             |
| `function_oid`  | OID univoco della funzione (utilizzato internamente da PostgreSQL)                |
| `function_name` | Nome della funzione                                                               |
| `arguments`     | Lista degli argomenti con tipo e nome (ad esempio: `arg1 integer, arg2 text`)     |
| `return_type`   | Tipo di ritorno dichiarato dalla funzione (ad esempio: `integer`, `SETOF record`) |
| `num_args`      | Numero di argomenti (calcolato in base alle virgole nella lista degli argomenti)  |
| `comment`       | Testo del commento associato tramite `COMMENT ON FUNCTION` (se presente)          |

---

### ⚙️ Esempi di Utilizzo

1. **Elencare tutte le funzioni senza commento**:

   ```sql
   SELECT schema, function_name
     FROM dbops.vw_function_list
    WHERE comment IS NULL;
   ```

2. **Contare le funzioni per schema**:

   ```sql
   SELECT schema, COUNT(*) AS total_functions
     FROM dbops.vw_function_list
    GROUP BY schema;
   ```

3. **Trovare funzioni con più di 3 parametri**:

   ```sql
   SELECT schema, function_name, num_args
     FROM dbops.vw_function_list
    WHERE num_args > 3;
   ```

4. **Ricerca per nome e visualizzazione firma completa**:

   ```sql
   SELECT function_name, arguments, return_type
     FROM dbops.vw_function_list
    WHERE function_name ILIKE '%iva%';
   ```

---

### 💡 Vantaggi Operativi

* **Manutenzione semplificata**: individua rapidamente funzioni non documentate.
* **Analisi delle API interne**: mappa le signature disponibili per integrazioni o refactoring.
* **Supporto al refactoring**: OID e overload chiaramente identificati consentono modifiche mirate.

---

> 🧠 **“Una panoramica centralizzata delle funzioni del database accelera il lavoro di sviluppo, auditing e documentazione del codice SQL.”**
