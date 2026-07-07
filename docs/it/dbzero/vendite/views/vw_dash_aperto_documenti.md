{% include-markdown "it/dbzero/vendite/manual/vw_dash_aperto_documenti.md" %}
# 🔍 View `vw_dash_aperto_documenti`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_aperto_documenti AS
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
    valore_transitato,
    unita_totali,
    unita_transitate,
    is_transitato,
    (is_transitato IS DISTINCT FROM true) AS is_aperto,
    motivo_fermo,
    data_riferimento
   FROM vendite.vw_dash_fatturazione_documenti d
  WHERE (((area)::text <> 'COMMESSE'::text) AND (NOT is_abortito));
```


---
{% include-markdown "signature-core.md" %}
