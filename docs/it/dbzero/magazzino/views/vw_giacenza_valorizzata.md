{% include-markdown "it/dbzero/magazzino/manual/vw_giacenza_valorizzata.md" %}
# 🔍 View `vw_giacenza_valorizzata`

> 📝 **Descrizione**
>
> La SITUAZIONE della giacenza: quantita' dal registro (vw_giacenza), valore dalla copia (valore_giacenza), costo medio = valore / qta — con la stessa regola di vw_costo_medio (rev 2026-09-18, C6: NULL se qta &lt;= 0 o senza riga di valore). Fino al 2026-09-15 era tautologica (qta * (valore / qta) = valore, con qta nell'accumulatore): ora il join e' fra due fonti e una divergenza si vede — valore NULL su una giacenza con movimenti e' un'anomalia da guardare (vw_magazzino_valore_giacenza_divergente), non un caso da nascondere. security_invoker. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.8; Lotto 2, C6.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW magazzino.vw_giacenza_valorizzata
WITH (security_invoker=true) AS
SELECT g.articolo_id,
    g.magazzino_id,
    g.qta,
    vg.valore,
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
