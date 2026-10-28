{% include-markdown "it/dbzero/magazzino/manual/vw_disponibilita_articolo.md" %}
# 🔍 View `vw_disponibilita_articolo`

> 📝 **Descrizione**
>
> La disponibilita' di un articolo su TUTTI i magazzini VISIBILI a chi interroga: dentro l'emittente attivo e' tutto, ed e' la RLS di movimenti e attesi (via magazzino) a decidere il perimetro, non un filtro scritto qui (c/s 7-sexies, 6 — come vw_costo_medio_globale). giacenza, bloccata, disponibile sommate da vw_disponibilita; n_magazzini = quanti ne concorrono. security_invoker. Brief: brief-db-magazzino-lotto-2-motore, sezione 4.6.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW magazzino.vw_disponibilita_articolo
WITH (security_invoker=true) AS
SELECT articolo_id,
    sum(giacenza) AS giacenza,
    sum(bloccata) AS bloccata,
    sum(disponibile) AS disponibile,
    count(DISTINCT magazzino_id) AS n_magazzini
   FROM magazzino.vw_disponibilita d
  GROUP BY articolo_id;
```

</div>


---
{% include-markdown "signature-core.md" %}
