{% include-markdown "it/dbzero/dbops/manual/vw_magazzino_valore_giacenza_divergente.md" %}
# 🔍 View `vw_magazzino_valore_giacenza_divergente`

> 📝 **Descrizione**
>
> Le coppie (articolo, magazzino) in cui la COPIA del valore (valore_giacenza) e la RI-SOMMA del registro (round(qta * costo, 6) per movimento) DIFFERISCONO — IS DISTINCT FROM su un FULL JOIN: una giacenza con movimenti e senza riga di valore, e una riga di valore senza movimenti, sono divergenze. DEVE RESTARE VUOTA. Non prova l'aritmetica (l'accumulatore somma gli stessi round che la primitiva ha scritto: coincidono per costruzione): prova che NESSUNO HA SCRITTO FUORI DALLA PORTA (M-4, D-L2-b). Il rimedio e' fn_ricalcola_valore_giacenza. security_invoker; presidio natura ZERO, perimetro DEFINER (la legge fn_conta_presidio: da un percorso senza contesto darebbe zero per cecita'), cadenza SETTIMANALE. Brief: brief-db-magazzino-lotto-2-motore, sezione 4.4.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_magazzino_valore_giacenza_divergente
WITH (security_invoker=true) AS
WITH registro AS (
         SELECT m.articolo_id,
            m.magazzino_id,
            sum(round((m.qta * COALESCE(m.costo_unitario, (0)::numeric)), 6)) AS valore_registro
           FROM magazzino.movimenti m
          GROUP BY m.articolo_id, m.magazzino_id
        )
 SELECT COALESCE(r.articolo_id, vg.articolo_id) AS articolo_id,
    COALESCE(r.magazzino_id, vg.magazzino_id) AS magazzino_id,
    vg.valore AS valore_copia,
    r.valore_registro
   FROM (registro r
     FULL JOIN magazzino.valore_giacenza vg ON (((vg.articolo_id = r.articolo_id) AND (vg.magazzino_id = r.magazzino_id))))
  WHERE (vg.valore IS DISTINCT FROM r.valore_registro);
```

</div>


---
{% include-markdown "signature-core.md" %}
