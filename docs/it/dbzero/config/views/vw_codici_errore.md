# 🔍 View `vw_codici_errore`

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW config.vw_codici_errore
WITH (security_invoker=true) AS
SELECT c.codice,
    c.classe,
    c.obsoleto_dal,
    c.note,
    m.lingua,
    m.messaggio,
    m.causa,
    m.soluzione
   FROM (config.codici_errore c
     LEFT JOIN config.messaggi_errore m ON ((m.codice = c.codice)));
```


---
{% include-markdown "signature-core.md" %}
