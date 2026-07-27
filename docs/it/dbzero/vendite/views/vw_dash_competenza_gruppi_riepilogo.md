{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_gruppi_riepilogo.md" %}
# 🔍 View `vw_dash_competenza_gruppi_riepilogo`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_gruppi_riepilogo
WITH (security_invoker=on) AS
SELECT competenza_mese,
    stadio,
    emittente_soggetto_ruolo_id,
    (count(*))::integer AS n_gruppi,
    (COALESCE(sum(n_attivita), (0)::numeric))::bigint AS n_attivita,
    COALESCE(sum(valore), (0)::numeric) AS valore,
    (count(*) FILTER (WHERE ((tipo_gruppo)::text = 'ONERI_COMMESSA'::text)))::integer AS n_gruppi_oneri
   FROM vendite.vw_dash_competenza_gruppi g
  GROUP BY competenza_mese, stadio, emittente_soggetto_ruolo_id;
```


---
{% include-markdown "signature-core.md" %}
