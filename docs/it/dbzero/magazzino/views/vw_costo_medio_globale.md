{% include-markdown "it/dbzero/magazzino/manual/vw_costo_medio_globale.md" %}
# 🔍 View `vw_costo_medio_globale`

> 📝 **Descrizione**
>
> Il costo medio di un articolo su TUTTI i magazzini VISIBILI a chi interroga: «globale» = i magazzini dell'emittente in sessione, ed e' la RLS di magazzini (via movimenti e valore_giacenza) a decidere il perimetro, non un filtro scritto qui (7-sexies, 6). qta_tot dal registro, valore_tot dalla copia; stessa regola di vw_costo_medio (rev 2026-09-18, C6: NULL se la quantita' totale e' &lt;= 0). security_invoker. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.8.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW magazzino.vw_costo_medio_globale
WITH (security_invoker=true) AS
SELECT g.articolo_id,
    sum(g.qta) AS qta_tot,
    sum(vg.valore) AS valore_tot,
        CASE
            WHEN (sum(g.qta) > (0)::numeric) THEN (sum(vg.valore) / sum(g.qta))
            ELSE NULL::numeric
        END AS costo_medio_globale
   FROM (magazzino.vw_giacenza g
     LEFT JOIN magazzino.valore_giacenza vg ON (((vg.articolo_id = g.articolo_id) AND (vg.magazzino_id = g.magazzino_id))))
  GROUP BY g.articolo_id;
```

</div>


---
{% include-markdown "signature-core.md" %}
