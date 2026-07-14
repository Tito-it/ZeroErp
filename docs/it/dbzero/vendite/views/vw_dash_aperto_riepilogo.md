{% include-markdown "it/dbzero/vendite/manual/vw_dash_aperto_riepilogo.md" %}
# 🔍 View `vw_dash_aperto_riepilogo`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_aperto_riepilogo
WITH (security_invoker=on) AS
SELECT area,
    fase,
    (count(*))::integer AS n_documenti,
    sum(valore_totale) AS valore_totale
   FROM vendite.vw_dash_aperto_documenti
  GROUP BY area, fase;
```


---
{% include-markdown "signature-core.md" %}
