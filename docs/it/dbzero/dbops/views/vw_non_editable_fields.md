{% include-markdown "it/dbzero/dbops/manual/vw_non_editable_fields.md" %}
# 🔍 View `vw_non_editable_fields`

```sql
CREATE OR REPLACE VIEW dbops.vw_non_editable_fields AS
SELECT target_schema,
    target_table,
    column_name,
    error_code,
    exec_mode,
    note
   FROM dbops.automation_lock_columns alc
  WHERE (enabled = true);
```


---
{% include-markdown "signature-core.md" %}
