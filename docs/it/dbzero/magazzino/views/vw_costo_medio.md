{% include-markdown "it/dbzero/magazzino/manual/vw_costo_medio.md" %}
# 🔍 View `vw_costo_medio`

> 📝 **Descrizione**
>
> Il COSTO MEDIO (un tasso) per articolo e magazzino: valore_giacenza.valore / vw_giacenza.qta. La quantita' viene dal REGISTRO e il valore dalla COPIA ricostruibile (M-4): due fonti, non una letta due volte. ⭐ rev 2026-09-18 (Lotto 2, C6): NULL quando la quantita' e' &lt;= 0 — non solo a zero: con consente_stock_negativo la giacenza puo' essere negativa e il rapporto non e' un costo — oppure senza riga di valore. E' la SEDE UNICA della «media corrente» di D-L2-c: la primitiva magazzino.fn_scrivi_movimento la legge dentro il lock per valorizzare ogni uscita e le entrate senza costo. security_invoker. Brief: brief-db-magazzino-lotto-2-motore, sezione 6-ter C6.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW magazzino.vw_costo_medio
WITH (security_invoker=true) AS
SELECT g.articolo_id,
    g.magazzino_id,
        CASE
            WHEN (g.qta > (0)::numeric) THEN (vg.valore / g.qta)
            ELSE NULL::numeric
        END AS costo_medio
   FROM (magazzino.vw_giacenza g
     LEFT JOIN magazzino.valore_giacenza vg ON (((vg.articolo_id = g.articolo_id) AND (vg.magazzino_id = g.magazzino_id))));
```

</div>


---
{% include-markdown "signature-core.md" %}
