{% include-markdown "it/dbzero/dbops/manual/proc_apply_storicizza_defaults.md" %}
# ⚙️ Procedura `proc_apply_storicizza_defaults`

```sql
CREATE PROCEDURE proc_apply_storicizza_defaults()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE dbops.proc_apply_storicizza_defaults()
 LANGUAGE plpgsql
AS $procedure$
  DECLARE
    rec RECORD;
    sch TEXT;
    tbl TEXT;
  BEGIN
    FOR rec IN
      SELECT table_name
        FROM config.storico_set_storicizza
    LOOP
      -- separa "schema.tabella" in due parti
      sch := split_part(rec.table_name, '.', 1);
      tbl := split_part(rec.table_name, '.', 2);

      -- esegue: ALTER TABLE schema.tabella ALTER COLUMN storicizza SET DEFAULT true
      EXECUTE format(
        'ALTER TABLE %I.%I ALTER COLUMN storicizza SET DEFAULT true',
        sch,
        tbl
      );
    END LOOP;
  END;
  $procedure$
```
---
{% include-markdown "signature-core.md" %}
