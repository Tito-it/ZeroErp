# 🔍 View `vw_codici_errore_identita`

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW config.vw_codici_errore_identita
WITH (security_invoker=true) AS
SELECT codice,
    classe,
    obsoleto_dal,
    note
   FROM config.codici_errore c
  ORDER BY codice;
```


---
{% include-markdown "signature-core.md" %}
