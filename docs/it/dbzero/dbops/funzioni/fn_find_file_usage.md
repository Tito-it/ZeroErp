{% include-markdown "it/dbzero/dbops/manual/fn_find_file_usage.md" %}
# ⚙️ Funzione `fn_find_file_usage`

### 🎯 Scopo Principale
* **Analisi d’impatto**  
  Identificare rapidamente tutte le relazioni di FK verso una tabella, utile per valutare dipendenze e conseguenze di modifiche, cancellazioni o refactoring di schema.

* **Documentazione automatica**  
  Fornire un’elenco puntuale di constraint FK anziché esplorare manualmente il catalogo di sistema.

---

```sql
CREATE FUNCTION fn_find_file_usage(p_target_table regclass)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_find_file_usage(p_target_table regclass)
 RETURNS TABLE(table_with_fk regclass, fk_column name, referenced_table regclass, pk_column name)
 LANGUAGE sql
 STABLE
AS $function$
  -- ================================================
  -- Funzione: dbops.fn_find_file_usage(regclass)
  -- Scopo:   trova tutte le foreign key che fanno riferimento
  --          ad una tabella specificata in input
  -- ================================================

  SELECT
    c.conrelid::regclass               AS table_with_fk,
    a.attname                          AS fk_column,
    c.confrelid::regclass             AS referenced_table,
    af.attname                         AS pk_column
  FROM pg_constraint c
  JOIN pg_class t   ON c.conrelid = t.oid
  JOIN pg_attribute a ON a.attrelid = t.oid
                    AND a.attnum = ANY(c.conkey)
  JOIN pg_class ft  ON c.confrelid = ft.oid
  JOIN pg_attribute af ON af.attrelid = ft.oid
                      AND af.attnum = ANY(c.confkey)
  WHERE c.contype = 'f'
    AND c.confrelid = p_target_table;
$function$
```