# 🔍 View `vw_regioni_lista`

> 📝 **Descrizione**
>
> Vista di lista delle regioni (ui.lista_definizione config.regioni): la riga che il repository consegna, cosi' il database valida i campo_sorgente contro le colonne vere. Brief: brief-db-liste-datatable-grezze §8 punto 6 (2026-09-27).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW config.vw_regioni_lista
WITH (security_invoker=on) AS
SELECT r.id,
    r.descrizione,
    r.stato_id,
    s.descrizione AS stato_descrizione
   FROM (config.regioni r
     JOIN config.stati s ON ((s.id = r.stato_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
