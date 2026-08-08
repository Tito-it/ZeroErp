{% include-markdown "it/dbzero/script/manual/vw_audit_sources.md" %}
# 🔍 View `vw_audit_sources`

> 📝 **Descrizione**
>
> Vista pubblica delle storico audit-abili dal drawer admin (Fase 5 P1 2026-04-29). Espone solo (code, label_key, area_funzionale) come contratto API: storico_table / storico_pk_col restano colonne tecniche di dbops.audit_sources, lette solo da script.fn_audit_summary per dispatch dinamico.

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
