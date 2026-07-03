{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_mensile.md" %}
# 🔍 View `vw_dash_fatturazione_mensile`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_mensile AS
SELECT area,
    competenza_mese,
    sum(valore_totale) FILTER (WHERE (NOT is_abortito)) AS valore_totale,
    sum(valore_transitato) FILTER (WHERE (NOT is_abortito)) AS valore_transitato,
    count(*) FILTER (WHERE (NOT is_abortito)) AS n_documenti,
    count(*) FILTER (WHERE ((NOT is_abortito) AND is_transitato)) AS n_transitati,
    count(*) FILTER (WHERE ((NOT is_abortito) AND (NOT is_transitato))) AS n_fermi,
    count(*) FILTER (WHERE is_abortito) AS n_abortiti
   FROM vendite.vw_dash_fatturazione_documenti d
  GROUP BY area, competenza_mese;
```


---
{% include-markdown "signature-core.md" %}
