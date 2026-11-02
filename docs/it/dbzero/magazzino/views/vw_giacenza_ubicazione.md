{% include-markdown "it/dbzero/magazzino/manual/vw_giacenza_ubicazione.md" %}
# 🔍 View `vw_giacenza_ubicazione`

> 📝 **Descrizione**
>
> La giacenza per POSIZIONE: somma delle quantita' per articolo, magazzino e ubicazione (NULL = senza posizione, un gruppo come gli altri). Uno spostamento fra ubicazioni e' una coppia OUT/IN sul registro con la stessa sorgente: in vw_giacenza si annulla, qui si vede. security_invoker.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW magazzino.vw_giacenza_ubicazione
WITH (security_invoker=true) AS
SELECT articolo_id,
    magazzino_id,
    ubicazione_id,
    sum(qta) AS qta
   FROM magazzino.movimenti m
  GROUP BY articolo_id, magazzino_id, ubicazione_id;
```

</div>


---
{% include-markdown "signature-core.md" %}
