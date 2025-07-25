{% include-markdown "it/dbzero/dbops/manual/vw_trigger_functions.md" %}
# 🔍 View `vw_trigger_functions`

```sql
CREATE OR REPLACE VIEW dbops.vw_trigger_functions AS
SELECT n.nspname AS schema,
    cls.relname AS tabella,
    trg.tgname AS nome_trigger,
    p.proname AS nome_funzione,
    pg_get_functiondef(p.oid) AS definizione_funzione
   FROM (((pg_trigger trg
     JOIN pg_class cls ON ((trg.tgrelid = cls.oid)))
     JOIN pg_proc p ON ((trg.tgfoid = p.oid)))
     JOIN pg_namespace n ON ((n.oid = cls.relnamespace)))
  WHERE (NOT trg.tgisinternal)
  ORDER BY n.nspname, cls.relname, trg.tgname;
```

---
{% include-markdown "signature-core.md" %}
