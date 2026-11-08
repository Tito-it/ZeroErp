{% include-markdown "it/dbzero/dbops/manual/vw_riferimenti_morti_rientrati.md" %}
# 🔍 View `vw_riferimenti_morti_rientrati`

> 📝 **Descrizione**
>
> Voci del registro del debito (dbops.riferimenti_morti_esenzioni) che non corrispondono piu' a nessun difetto REALE o ORFANA: righe da TOGLIERE dal registro. E' cio' che impedisce al registro di diventare un elenco di eccezioni permanenti. ⚠️ Una voce la cui funzione plpgsql_check non ha potuto misurare (NON_MISURATO) non e' rientrata: di quella funzione non si sa niente. Il rosso della misura mancata sta in dbops.vw_riferimenti_morti_da_sanare e nel guardrail CI. Una funzione che non esiste piu' non compare nella misura, e la sua voce e' rientrata. La misura si legge una volta. Presidio a catalogo in dbops.presidi, soglia ZERO; lo prova db/pgtap/dbops/test-riferimenti-morti-v1.sql.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_riferimenti_morti_rientrati
WITH (security_invoker=true) AS
WITH misura AS MATERIALIZED (
         SELECT m.classe,
            m.schema_nome,
            m.funzione,
            m.esito
           FROM dbops.fn_check_funzioni_riferimenti_morti() m(classe, schema_nome, funzione, argomenti, esito)
        )
 SELECT id,
    schema_nome,
    funzione,
    esito_like,
    data_registrazione,
    motivo
   FROM dbops.riferimenti_morti_esenzioni e
  WHERE ((NOT (EXISTS ( SELECT 1
           FROM misura m
          WHERE ((m.classe = ANY (ARRAY['REALE'::text, 'ORFANA'::text])) AND (m.schema_nome = e.schema_nome) AND (m.funzione = e.funzione) AND (m.esito ~~ e.esito_like))))) AND (NOT (EXISTS ( SELECT 1
           FROM misura m
          WHERE ((m.classe = 'NON_MISURATO'::text) AND (m.schema_nome = e.schema_nome) AND (m.funzione = e.funzione))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
