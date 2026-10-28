{% include-markdown "it/dbzero/dbops/manual/vw_non_editable_fields.md" %}
# 🔍 View `vw_non_editable_fields`

> 📝 **Descrizione**
>
> Alias semantico su dbops.automation_lock_columns: elenca i campi non editabili (lock incondizionato) per ciascuna (target_schema, target_table). Filtrata su enabled=true. Non copre i lock condizionali stato-dipendenti gestiti da trigger custom.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

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
