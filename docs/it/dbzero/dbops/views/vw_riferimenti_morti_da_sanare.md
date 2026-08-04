# 🔍 View `vw_riferimenti_morti_da_sanare`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW dbops.vw_riferimenti_morti_da_sanare
WITH (security_invoker=on) AS
SELECT classe,
    schema_nome,
    funzione,
    argomenti,
    esito
   FROM dbops.fn_check_funzioni_riferimenti_morti() m(classe, schema_nome, funzione, argomenti, esito)
  WHERE ((classe = ANY (ARRAY['REALE'::text, 'ORFANA'::text])) AND (NOT (EXISTS ( SELECT 1
           FROM dbops.riferimenti_morti_esenzioni e
          WHERE ((e.schema_nome = m.schema_nome) AND (e.funzione = m.funzione) AND (m.esito ~~ e.esito_like))))));
```


---
{% include-markdown "signature-core.md" %}
