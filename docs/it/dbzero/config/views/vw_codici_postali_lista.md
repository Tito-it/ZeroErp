# 🔍 View `vw_codici_postali_lista`

> 📝 **Descrizione**
>
> Vista di lista dei codici postali (ui.lista_definizione config.codici_postali). Porta la sigla della provincia del comune (NULL se il comune non ha provincia), che distingue comuni omonimi; varchar dal 20261010-26, senza spazi di riempimento. Brief: brief-db-liste-datatable-grezze §8 punto 6 e §9.2; brief-db-character-n-spazi-di-riempimento D-3.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW config.vw_codici_postali_lista
WITH (security_invoker=on) AS
SELECT cp.id,
    cp.codice,
    cp.comune_id,
    c.descrizione AS comune_descrizione,
    c.provincia_id,
    p.sigla AS provincia_sigla
   FROM ((config.codici_postali cp
     JOIN config.comuni c ON ((c.id = cp.comune_id)))
     LEFT JOIN config.province p ON ((p.id = c.provincia_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
