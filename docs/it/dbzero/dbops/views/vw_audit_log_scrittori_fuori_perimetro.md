{% include-markdown "it/dbzero/dbops/manual/vw_audit_log_scrittori_fuori_perimetro.md" %}
# 🔍 View `vw_audit_log_scrittori_fuori_perimetro`

> 📝 **Descrizione**
>
> CANCELLO — deve restare VUOTA. Le funzioni che scrivono in dbops.audit_log (DML diretto, o via fn_audit_log_once / fn_audit_begin / fn_audit_end) e che stanno FUORI dal perimetro dichiarato nella vista stessa: dbops e maintenance. dbops.audit_log è un registro TECNICO — le automazioni e gli strumenti DBA, letto dall'amministrazione — e non deve poter contenere dati di dominio (decisione §8.3, brief brief-db-rls-storico-scope-congelato, 2026-09-11): il presidio giusto non è una policy di perimetro sul log ma impedire alla fonte che una funzione di vendite, anagrafiche, pagamenti ci scriva. Una riga qui fa rosso db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql, che gira in CI. Allargare il perimetro è un changeSet su questa vista, firmato. Il sorgente si legge senza i commenti di riga; le letture del registro non contano; le tre funzioni di audit sono la porta e sono escluse per nome. security_invoker: legge solo il catalogo.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_audit_log_scrittori_fuori_perimetro
WITH (security_invoker=true) AS
WITH perimetro AS (
         SELECT unnest(ARRAY['dbops'::name, 'maintenance'::name]) AS nspname
        ), sorgenti AS (
         SELECT p.oid,
            n.nspname,
            p.proname,
            regexp_replace(p.prosrc, '--[^\n]*'::text, ''::text, 'g'::text) AS corpo
           FROM (pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
          WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (p.prokind = ANY (ARRAY['f'::"char", 'p'::"char"])))
        )
 SELECT (((nspname)::text || '.'::text) || (proname)::text) AS funzione,
    (nspname)::text AS schema_funzione,
        CASE
            WHEN (corpo ~* '(insert\s+into|update|delete\s+from)\s+dbops\.audit_log\M'::text) THEN 'DML_DIRETTO'::text
            ELSE 'VIA_FN_AUDIT'::text
        END AS come_scrive
   FROM sorgenti s
  WHERE (((corpo ~* '(insert\s+into|update|delete\s+from)\s+dbops\.audit_log\M'::text) OR (corpo ~ '\mfn_audit_(log_once|begin|end)\s*\('::text)) AND (NOT (EXISTS ( SELECT 1
           FROM perimetro pe
          WHERE (pe.nspname = s.nspname)))) AND (NOT ((nspname = 'dbops'::name) AND (proname = ANY (ARRAY['fn_audit_log_once'::name, 'fn_audit_begin'::name, 'fn_audit_end'::name])))))
  ORDER BY (((nspname)::text || '.'::text) || (proname)::text);
```

</div>


---
{% include-markdown "signature-core.md" %}
