# ⚙️ Funzione `apply_fk_index_policy`

```sql
CREATE FUNCTION apply_fk_index_policy()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE dbops.apply_fk_index_policy()
 LANGUAGE plpgsql
AS $procedure$
DECLARE
  rec RECORD;
BEGIN
  FOR rec IN SELECT * FROM dbops.fk_index_policy LOOP
    IF rec.consentito THEN
      EXECUTE format(
        'CREATE INDEX IF NOT EXISTS ix_%I_%I ON %I.%I (%I)',
        rec.table_name,
        rec.constraint_name,
        rec.schema_name,
        rec.table_name,
        rec.constraint_name
      );
    ELSE
      EXECUTE format(
        'DROP INDEX IF EXISTS ix_%I_%I',
        rec.table_name,
        rec.constraint_name
      );
    END IF;
  END LOOP;
END;
$procedure$
```