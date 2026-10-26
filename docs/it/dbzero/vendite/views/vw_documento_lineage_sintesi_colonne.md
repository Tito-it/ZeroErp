{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage_sintesi_colonne.md" %}
# 🔍 View `vw_documento_lineage_sintesi_colonne`

> 📝 **Descrizione**
>
> Le colonne del risultato di vendite.fn_documento_lineage_sintesi, dal catalogo di sistema (una riga per colonna, con la posizione). E' la regola D-B2 del giro B di brief-db-lineage-seminata-per-chiave in un posto solo: una colonna di lista il cui campo_sorgente non sta nella vista di lista ma sta qui viene dalla SINTESI, e il backend la chiede per le chiavi della pagina (o dell'export, o del drawer). La leggono i presidi ui/test-lista-*-seed (test 7), il motore delle liste e l'export.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_documento_lineage_sintesi_colonne
WITH (security_invoker=on) AS
SELECT a.nome AS colonna,
    (a.n)::integer AS posizione
   FROM (pg_proc p
     CROSS JOIN LATERAL UNNEST(p.proargnames, p.proargmodes) WITH ORDINALITY a(nome, modo, n))
  WHERE ((p.oid = ('vendite.fn_documento_lineage_sintesi(bigint[],text[])'::regprocedure)::oid) AND (a.modo = 't'::"char"));
```

</div>


---
{% include-markdown "signature-core.md" %}
