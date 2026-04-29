{% include-markdown "it/dbzero/script/manual/vw_audit_sources.md" %}
# 🔍 View `vw_audit_sources`

```sql
CREATE OR REPLACE VIEW script.vw_audit_sources AS
SELECT code,
    label_key,
    area_funzionale
   FROM dbops.audit_sources
  WHERE (attivo = true)
  ORDER BY code;
```


---
{% include-markdown "signature-core.md" %}
