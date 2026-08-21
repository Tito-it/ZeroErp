{% include-markdown "it/dbzero/magazzino/manual/vw_giacenza_valorizzata.md" %}
# 🔍 View `vw_giacenza_valorizzata`

```sql
CREATE OR REPLACE VIEW magazzino.vw_giacenza_valorizzata AS
SELECT g.articolo_id,
    g.magazzino_id,
    g.qta,
    cm.costo_medio,
    ((g.qta * cm.costo_medio))::numeric(18,6) AS valore
   FROM (magazzino.vw_giacenza g
     LEFT JOIN magazzino.vw_costo_medio cm ON (((cm.articolo_id = g.articolo_id) AND (cm.magazzino_id = g.magazzino_id))));
```


---
{% include-markdown "signature-core.md" %}
