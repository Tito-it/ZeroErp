{% include-markdown "it/dbzero/dbops/manual/fn_foreign_keys_info.md" %}
# ⚙️ Funzione `fn_foreign_keys_info`

```sql
CREATE FUNCTION fn_foreign_keys_info(tabella text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_foreign_keys_info(tabella text)
 RETURNS TABLE(relazione text, constraint_name text, source_table text, source_column text, target_table text, target_column text)
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- INCOMING FK (altre tabelle che puntano alla tabella indicata)
    RETURN QUERY
    SELECT
        'incoming'::TEXT AS relazione,
        tc.constraint_name::TEXT,
        tc.table_name::TEXT,
        kcu.column_name::TEXT,
        ccu.table_name::TEXT,
        ccu.column_name::TEXT
    FROM
        information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
           AND tc.constraint_schema = kcu.constraint_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
           AND ccu.constraint_schema = tc.constraint_schema
    WHERE
        tc.constraint_type = 'FOREIGN KEY'
        AND ccu.table_name = tabella;

    -- OUTGOING FK (chiavi esterne definite nella tabella specificata)
    RETURN QUERY
    SELECT
        'outgoing'::TEXT AS relazione,
        tc.constraint_name::TEXT,
        tc.table_name::TEXT,
        kcu.column_name::TEXT,
        ccu.table_name::TEXT,
        ccu.column_name::TEXT
    FROM
        information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
           AND tc.constraint_schema = kcu.constraint_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
           AND ccu.constraint_schema = tc.constraint_schema
    WHERE
        tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = tabella;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
