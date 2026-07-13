{% include-markdown "it/dbzero/vendite/manual/vw_dash_aperto_documenti.md" %}
# 🔍 View `vw_dash_aperto_documenti`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_aperto_documenti
WITH (security_invoker=on) AS
SELECT area,
    documento_id,
    documento_uid,
    codice,
    emittente_fiscale_id,
    emittente_soggetto_ruolo_id,
    cliente_display,
    fase,
    stato_codice_interno,
    stato_codice,
    valore_totale,
    unita_totali,
    motivo_fermo,
    data_riferimento
   FROM vendite.vw_dash_fatturazione_documenti d
  WHERE (((area)::text <> 'COMMESSE'::text) AND (NOT is_abortito) AND (is_transitato IS DISTINCT FROM true) AND ((fase)::text <> 'CHIUSO'::text));
```


---
{% include-markdown "signature-core.md" %}
