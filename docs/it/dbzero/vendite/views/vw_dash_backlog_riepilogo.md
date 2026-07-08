{% include-markdown "it/dbzero/vendite/manual/vw_dash_backlog_riepilogo.md" %}
# 🔍 View `vw_dash_backlog_riepilogo`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_backlog_riepilogo AS
SELECT classe,
    area,
    (count(*))::integer AS n_documenti,
    COALESCE(sum(valore_fermo), (0)::numeric) AS valore_fermo_tot,
    (COALESCE(sum(unita_ferme), (0)::bigint))::integer AS unita_ferme_tot,
    max(anzianita_giorni) AS anzianita_max_giorni
   FROM vendite.vw_dash_backlog_documenti
  GROUP BY classe, area;
```


---
{% include-markdown "signature-core.md" %}
