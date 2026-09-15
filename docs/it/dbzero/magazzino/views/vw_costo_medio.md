{% include-markdown "it/dbzero/magazzino/manual/vw_costo_medio.md" %}
# 🔍 View `vw_costo_medio`

> 📝 **Descrizione**
>
> Il COSTO MEDIO (un tasso) per articolo e magazzino: valore_giacenza.valore / vw_giacenza.qta. La quantita' viene dal REGISTRO e il valore dalla COPIA ricostruibile (M-4): due fonti, non una letta due volte. NULL a quantita' zero o senza riga di valore. Fino al 2026-09-15 portava anche qta e valore dall'accumulatore: oggi la situazione (quantita', valore, tasso) e' vw_giacenza_valorizzata. security_invoker. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.8.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW magazzino.vw_costo_medio
WITH (security_invoker=true) AS
SELECT g.articolo_id,
    g.magazzino_id,
        CASE
            WHEN (g.qta <> (0)::numeric) THEN (vg.valore / g.qta)
            ELSE NULL::numeric
        END AS costo_medio
   FROM (magazzino.vw_giacenza g
     LEFT JOIN magazzino.valore_giacenza vg ON (((vg.articolo_id = g.articolo_id) AND (vg.magazzino_id = g.magazzino_id))));
```


---
{% include-markdown "signature-core.md" %}
