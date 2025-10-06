# 🔍 View `vw_giacenza`

```sql
CREATE OR REPLACE VIEW magazzino.vw_giacenza AS
SELECT articolo_id,
    magazzino_id,
    sum(qta) AS qta
   FROM magazzino.movimenti m
  GROUP BY articolo_id, magazzino_id;
```


---
{% include-markdown "signature-core.md" %}
