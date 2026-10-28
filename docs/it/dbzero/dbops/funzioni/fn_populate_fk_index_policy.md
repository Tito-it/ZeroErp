{% include-markdown "it/dbzero/dbops/manual/fn_populate_fk_index_policy.md" %}
# ⚙️ Funzione `fn_populate_fk_index_policy`

```sql
CREATE FUNCTION fn_populate_fk_index_policy()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_populate_fk_index_policy()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  rec RECORD;
BEGIN
  FOR rec IN
    SELECT schema_name, table_name, constraint_name, create_index_suggestion  
      FROM dbops.vw_fk_senza_indice
    WHERE (schema_name, table_name, constraint_name)
      NOT IN (
        SELECT schema_name, table_name, constraint_name
          FROM dbops.fk_index_policy
      )
  LOOP
    INSERT INTO dbops.fk_index_policy(
      schema_name,
      table_name,
      constraint_name,
      consentito,
      dll_command
    ) VALUES (
      rec.schema_name,
      rec.table_name,
      rec.constraint_name,
      false,
      rec.create_index_suggestion
    );
  END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_populate_fk_index_policy()
IS 'Popola automaticamente dbops.fk_index_policy per tutte le FK senza indice, con consentito=false.';
```

</div>

---
{% include-markdown "signature-core.md" %}
