{% include-markdown "it/dbzero/vendite/manual/vw_dash_aperto_riepilogo.md" %}
# 🔍 View `vw_dash_aperto_riepilogo`

> 📝 **Descrizione**
>
> Situazione aperta v2: card area x fase sullo stock aperti-non-conclusi (vw_dash_aperto_documenti v2). n_documenti = tutti aperti della cella; valore_totale NULL per OFFERTE/CONTRATTI (aree a conteggi, DL-11). Via n_aperti (=n_documenti nel perimetro v2) e valore_transitato (concetto transito eliminato, DL-14). Fasi presenti: APERTO/IN_ATTESA/IN_CORSO (CHIUSO escluso a monte). Nessun asse temporale. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_aperto_riepilogo
WITH (security_invoker=on) AS
SELECT area,
    fase,
    (count(*))::integer AS n_documenti,
    sum(valore_totale) AS valore_totale
   FROM vendite.vw_dash_aperto_documenti
  GROUP BY area, fase;
```

</div>


---
{% include-markdown "signature-core.md" %}
