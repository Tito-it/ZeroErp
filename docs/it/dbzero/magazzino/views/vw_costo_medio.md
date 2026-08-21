{% include-markdown "it/dbzero/magazzino/manual/vw_costo_medio.md" %}
# 🔍 View `vw_costo_medio`

```sql
CREATE OR REPLACE VIEW magazzino.vw_costo_medio AS
SELECT articolo_id,
    magazzino_id,
    qta,
    valore,
        CASE
            WHEN (qta <> (0)::numeric) THEN (valore / qta)
            ELSE NULL::numeric
        END AS costo_medio
   FROM magazzino.costo_medio cm;
```


---
{% include-markdown "signature-core.md" %}
