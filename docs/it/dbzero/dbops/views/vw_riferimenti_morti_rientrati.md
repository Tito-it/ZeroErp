{% include-markdown "it/dbzero/dbops/manual/vw_riferimenti_morti_rientrati.md" %}
# 🔍 View `vw_riferimenti_morti_rientrati`

> 📝 **Descrizione**
>
> Voci del registro del debito che non corrispondono piu' a nessun difetto: righe da TOGLIERE. E' cio' che impedisce al registro di diventare un elenco di eccezioni permanenti.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_riferimenti_morti_rientrati
WITH (security_invoker=on) AS
SELECT id,
    schema_nome,
    funzione,
    esito_like,
    data_registrazione,
    motivo
   FROM dbops.riferimenti_morti_esenzioni e
  WHERE (NOT (EXISTS ( SELECT 1
           FROM dbops.fn_check_funzioni_riferimenti_morti() m(classe, schema_nome, funzione, argomenti, esito)
          WHERE ((m.classe = ANY (ARRAY['REALE'::text, 'ORFANA'::text])) AND (m.schema_nome = e.schema_nome) AND (m.funzione = e.funzione) AND (m.esito ~~ e.esito_like)))));
```

</div>


---
{% include-markdown "signature-core.md" %}
