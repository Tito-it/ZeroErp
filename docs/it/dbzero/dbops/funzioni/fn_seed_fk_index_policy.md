{% include-markdown "it/dbzero/dbops/manual/fn_seed_fk_index_policy.md" %}
# ⚙️ Funzione `fn_seed_fk_index_policy`

```sql
CREATE FUNCTION fn_seed_fk_index_policy()
```

**Definizione completa:**

<div data-search-exclude markdown>

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
      WHERE EXISTS (
        SELECT 1
          FROM dbops.automation_scope sc
         WHERE sc.schema_name = vw.schema_name
      )
      ON CONFLICT (schema_name, table_name, constraint_name) DO NOTHING;
    END;
    $function$

COMMENT ON FUNCTION dbops.fn_seed_fk_index_policy()
IS 'Registro policy indici per foreign key: seed automatico da view';
```

</div>

---
{% include-markdown "signature-core.md" %}
