{% include-markdown "it/dbzero/dbops/manual/apply_fk_index_policy.md" %}
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
  idx_name TEXT;
BEGIN
  FOR rec IN SELECT * FROM dbops.fk_index_policy LOOP
    IF rec.consentito THEN
      EXECUTE rec.dll_command;
    ELSE
         -- estraggo solo il nome dell'indice
        idx_name := split_part(rec.dll_command, ' ', 6);
        EXECUTE format(
          'DROP INDEX IF EXISTS %I.%I',
          rec.schema_name,
          idx_name
      );
    END IF;
  END LOOP;
END;
$procedure$
```
---
{% include-markdown "signature-core.md" %}
