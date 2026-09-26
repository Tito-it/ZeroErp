# 🔍 View `vw_province_lista`

> 📝 **Descrizione**
>
> Vista di lista delle province (ui.lista_definizione config.province). descrizione e sigla sono character(n) nella tabella: qui escono con TRIM. Brief: brief-db-liste-datatable-grezze §8 punto 6 (2026-09-27).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW config.vw_province_lista
WITH (security_invoker=on) AS
SELECT p.id,
    TRIM(BOTH FROM p.descrizione) AS descrizione,
    TRIM(BOTH FROM p.sigla) AS sigla,
    p.regione_id,
    r.descrizione AS regione_descrizione
   FROM (config.province p
     LEFT JOIN config.regioni r ON ((r.id = p.regione_id)));
```


---
{% include-markdown "signature-core.md" %}
