{% include-markdown "it/dbzero/magazzino/manual/vw_giacenza.md" %}
# 🔍 View `vw_giacenza`

> 📝 **Descrizione**
>
> La GIACENZA: somma delle quantita' del registro per articolo e magazzino. E' corretta SENZA join alle causali perche' la quantita' del registro e' gia' firmata (sign(qta) = causali.segno, guard trgfn_movimenti_guard_verso, M-1): applicare il segno qui lo applicherebbe due volte e trasformerebbe ogni uscita in un'entrata. Una sola fonte, il registro: valore_giacenza non porta quantita'. security_invoker: la RLS di movimenti passa attraverso, l'operatore vede i magazzini del suo emittente. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.8.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW magazzino.vw_giacenza
WITH (security_invoker=true) AS
SELECT articolo_id,
    magazzino_id,
    sum(qta) AS qta
   FROM magazzino.movimenti m
  GROUP BY articolo_id, magazzino_id;
```

</div>


---
{% include-markdown "signature-core.md" %}
