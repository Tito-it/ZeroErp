# 🔍 View `vw_province_lista`

> 📝 **Descrizione**
>
> Vista di lista delle province (ui.lista_definizione config.province). descrizione e sigla escono come sono: dal 20261010-26 sono varchar e non portano spazi di riempimento (prima character(n), con TRIM qui). Brief: brief-db-liste-datatable-grezze §8 punto 6; brief-db-character-n-spazi-di-riempimento D-3.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW config.vw_province_lista
WITH (security_invoker=on) AS
SELECT p.id,
    p.descrizione,
    p.sigla,
    p.regione_id,
    r.descrizione AS regione_descrizione
   FROM (config.province p
     LEFT JOIN config.regioni r ON ((r.id = p.regione_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
