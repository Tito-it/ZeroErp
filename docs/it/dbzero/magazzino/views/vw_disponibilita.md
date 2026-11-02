{% include-markdown "it/dbzero/magazzino/manual/vw_disponibilita.md" %}
# 🔍 View `vw_disponibilita`

> 📝 **Descrizione**
>
> La DISPONIBILITA' per articolo e magazzino, la formula in colonne: giacenza (vw_giacenza, il registro), bloccata (somma FIRMATA degli attesi APERTA in USCITA: negativa — un atteso in entrata e' merce in arrivo, non un blocco, e qui non si conta), disponibile = giacenza + bloccata (la somma, mai «meno»), n_blocchi. Lo stesso filtro di script.fn_check_disponibilita_uscita, che pero' esclude i blocchi di chi chiede: qui si contano tutti. Un articolo con blocchi e senza movimenti compare (giacenza 0, disponibile negativo). Niente impegnata / potenziale / in_arrivo finche' non c'e' chi le riempie. Il drill-down dei blocchi sono le righe di movimenti_attesi APERTA. security_invoker: il perimetro e' la RLS via magazzino.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW magazzino.vw_disponibilita
WITH (security_invoker=true) AS
WITH blocchi AS (
         SELECT a.articolo_id,
            a.magazzino_id,
            sum(a.qta) AS bloccata,
            count(*) AS n_blocchi
           FROM magazzino.movimenti_attesi a
          WHERE (((a.stato)::text = 'APERTA'::text) AND (a.qta < (0)::numeric))
          GROUP BY a.articolo_id, a.magazzino_id
        )
 SELECT COALESCE(g.articolo_id, b.articolo_id) AS articolo_id,
    COALESCE(g.magazzino_id, b.magazzino_id) AS magazzino_id,
    COALESCE(g.qta, (0)::numeric) AS giacenza,
    COALESCE(b.bloccata, (0)::numeric) AS bloccata,
    (COALESCE(g.qta, (0)::numeric) + COALESCE(b.bloccata, (0)::numeric)) AS disponibile,
    COALESCE(b.n_blocchi, (0)::bigint) AS n_blocchi
   FROM (magazzino.vw_giacenza g
     FULL JOIN blocchi b ON (((b.articolo_id = g.articolo_id) AND (b.magazzino_id = g.magazzino_id))));
```

</div>


---
{% include-markdown "signature-core.md" %}
