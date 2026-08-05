# 🔍 View `vw_codici_errore_da_dichiarare`

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW dbops.vw_codici_errore_da_dichiarare
WITH (security_invoker=true) AS
SELECT m.m[1] AS codice,
    bool_or(t.agganciata) AS da_trigger,
    count(DISTINCT p.oid) AS n_funzioni,
    string_agg(DISTINCT (((n.nspname)::text || '.'::text) || (p.proname)::text), ', '::text ORDER BY (((n.nspname)::text || '.'::text) || (p.proname)::text)) AS funzioni
   FROM ((pg_proc p
     JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
     CROSS JOIN LATERAL ( SELECT (EXISTS ( SELECT 1
                   FROM pg_trigger tg
                  WHERE ((tg.tgfoid = p.oid) AND (NOT tg.tgisinternal)))) AS agganciata) t),
    LATERAL regexp_matches(regexp_replace(p.prosrc, '--[^\n]*'::text, ''::text, 'g'::text), '''(E_[A-Z0-9_]+)'''::text, 'g'::text) m(m)
  WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (p.prolang = ( SELECT pg_language.oid
           FROM pg_language
          WHERE (pg_language.lanname = 'plpgsql'::name))))
  GROUP BY m.m[1];
```


---
{% include-markdown "signature-core.md" %}
