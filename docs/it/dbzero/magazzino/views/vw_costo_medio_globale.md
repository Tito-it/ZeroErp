{% include-markdown "it/dbzero/magazzino/manual/vw_costo_medio_globale.md" %}
# 🔍 View `vw_costo_medio_globale`

```sql
CREATE OR REPLACE VIEW magazzino.vw_costo_medio_globale AS
SELECT articolo_id,
    sum(qta) AS qta_tot,
    sum(valore) AS valore_tot,
        CASE
            WHEN (sum(qta) <> (0)::numeric) THEN (sum(valore) / sum(qta))
            ELSE NULL::numeric
        END AS costo_medio_globale
   FROM magazzino.costo_medio
  GROUP BY articolo_id;
```


---
{% include-markdown "signature-core.md" %}
