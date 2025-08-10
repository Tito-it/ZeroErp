{% include-markdown "it/dbzero/dbops/manual/proc_sync_storico_set_storicizza.md" %}
# ⚙️ Procedura `proc_sync_storico_set_storicizza`

```sql
CREATE PROCEDURE proc_sync_storico_set_storicizza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE dbops.proc_sync_storico_set_storicizza()
 LANGUAGE plpgsql
AS $procedure$
    DECLARE
      rec RECORD;
    BEGIN
      FOR rec IN
        SELECT a.attrelid::regclass::text AS table_name
          FROM pg_attribute a
          JOIN pg_class c ON a.attrelid = c.oid AND c.relkind = 'r'
          JOIN pg_namespace n ON c.relnamespace = n.oid
          JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
        WHERE a.attname = 'storicizza'
          -- confronta la stringa dell’espressione, non fai cast
          AND pg_get_expr(ad.adbin, ad.adrelid) = 'true'
      LOOP
        INSERT INTO config.storico_set_storicizza(table_name, insert_manuale)
        VALUES (rec.table_name, false)
        ON CONFLICT (table_name) DO NOTHING;
      END LOOP;
    END;
    $procedure$
```
---
{% include-markdown "signature-core.md" %}
