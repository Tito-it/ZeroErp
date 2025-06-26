{% include-markdown "it/dbzero/dbops/manual/fn_populate_fk_index_policy.md" %}
# ⚙️ Funzione `fn_populate_fk_index_policy`

```sql
CREATE FUNCTION fn_populate_fk_index_policy()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_populate_fk_index_policy()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  rec RECORD;
BEGIN
  FOR rec IN
    SELECT schema_name, table_name, constraint_name
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
      note
    ) VALUES (
      rec.schema_name,
      rec.table_name,
      rec.constraint_name,
      false,
      format(
        'Autopopulated: missing ix_%s_%s index',
        rec.table_name,
        rec.constraint_name
      )
    );
  END LOOP;
END;
$function$
```