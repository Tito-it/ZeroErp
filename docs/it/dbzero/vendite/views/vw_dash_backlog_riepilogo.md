{% include-markdown "it/dbzero/vendite/manual/vw_dash_backlog_riepilogo.md" %}
# 🔍 View `vw_dash_backlog_riepilogo`

> 📝 **Descrizione**
>
> Lente 2 Backlog: contatori di testata per classe x area (RECUPERABILE/ANOMALIA/SOLLECITO_CLIENTE; il FISIOLOGICO e' escluso a monte). n documenti, valore fermo totale (NULL-safe: 0 per aree a conteggi), unita' ferme, anzianita' massima in giorni. Scope ereditato. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_backlog_riepilogo
WITH (security_invoker=on) AS
SELECT classe,
    area,
    (count(*))::integer AS n_documenti,
    COALESCE(sum(valore_fermo), (0)::numeric) AS valore_fermo_tot,
    (COALESCE(sum(unita_ferme), (0)::bigint))::integer AS unita_ferme_tot,
    max(anzianita_giorni) AS anzianita_max_giorni
   FROM vendite.vw_dash_backlog_documenti
  GROUP BY classe, area;
```

</div>


---
{% include-markdown "signature-core.md" %}
