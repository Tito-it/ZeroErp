# 🔍 View `vw_comuni_lista`

> 📝 **Descrizione**
>
> Vista di lista dei comuni (ui.lista_definizione config.comuni). Sigla e nome della provincia come sono: varchar dal 20261010-26, senza spazi di riempimento (prima character(n), con TRIM qui). Brief: brief-db-liste-datatable-grezze §8 punto 6; brief-db-character-n-spazi-di-riempimento D-3.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW config.vw_comuni_lista
WITH (security_invoker=on) AS
SELECT c.id,
    c.descrizione,
    c.provincia_id,
    p.sigla AS provincia_sigla,
    p.descrizione AS provincia_descrizione,
    p.regione_id,
    r.descrizione AS regione_descrizione
   FROM ((config.comuni c
     LEFT JOIN config.province p ON ((p.id = c.provincia_id)))
     LEFT JOIN config.regioni r ON ((r.id = p.regione_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
