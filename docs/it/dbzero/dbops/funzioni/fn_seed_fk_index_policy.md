{% include-markdown "it/dbzero/dbops/manual/fn_seed_fk_index_policy.md" %}
# ⚙️ Funzione `fn_seed_fk_index_policy`

```sql
CREATE FUNCTION fn_seed_fk_index_policy()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_fk_index_policy()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
    BEGIN
      INSERT INTO dbops.fk_index_policy(
        schema_name,
        table_name,
        constraint_name,
        dll_command,
        consentito,
        generated_by_script
        
      )
      SELECT
        vw.schema_name,
        vw.table_name,
        vw.constraint_name,
        vw.create_index_suggestion,
        true,
        true
        
      FROM dbops.vw_fk_con_indice_missing_policy vw
      ON CONFLICT (schema_name, table_name, constraint_name) DO NOTHING;
    END;
    $function$
```
---
{% include-markdown "signature-core.md" %}
