{% include-markdown "it/dbzero/dbops/manual/vw_non_editable_fields.md" %}
# 🔍 View `vw_non_editable_fields`

> 📝 **Descrizione**
>
> Alias semantico su dbops.automation_lock_columns: elenca i campi non editabili (lock incondizionato) per ciascuna (target_schema, target_table). Filtrata su enabled=true. Non copre i lock condizionali stato-dipendenti gestiti da trigger custom.

<div data-search-exclude markdown>

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

</div>


---
{% include-markdown "signature-core.md" %}
