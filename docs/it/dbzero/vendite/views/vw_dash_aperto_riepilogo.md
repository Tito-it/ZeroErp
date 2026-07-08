{% include-markdown "it/dbzero/vendite/manual/vw_dash_aperto_riepilogo.md" %}
# 🔍 View `vw_dash_aperto_riepilogo`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_aperto_riepilogo AS
SELECT area,
    fase,
    (count(*))::integer AS n_documenti,
    (count(*) FILTER (WHERE is_aperto))::integer AS n_aperti,
    sum(valore_totale) AS valore_totale,
    sum(valore_transitato) AS valore_transitato
   FROM vendite.vw_dash_aperto_documenti
  GROUP BY area, fase;
```


---
{% include-markdown "signature-core.md" %}
