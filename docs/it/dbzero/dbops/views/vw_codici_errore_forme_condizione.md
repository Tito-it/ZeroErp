# 🔍 View `vw_codici_errore_forme_condizione`

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW dbops.vw_codici_errore_forme_condizione
WITH (security_invoker=true) AS
WITH righe AS (
         SELECT (n.nspname)::text AS sch,
            (p.proname)::text AS fn,
            p.oid,
            l.riga,
            l.n
           FROM ((pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
             CROSS JOIN LATERAL regexp_split_to_table(p.prosrc, '
'::text) WITH ORDINALITY l(riga, n))
          WHERE ((p.prolang = ( SELECT pg_language.oid
                   FROM pg_language
                  WHERE (pg_language.lanname = 'plpgsql'::name))) AND (n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])))
        ), punti AS (
         SELECT r.sch,
            r.fn,
            r.oid,
            r.n,
            (regexp_match(r.riga, '''(E_[A-Z0-9_]+)'''::text))[1] AS codice
           FROM righe r
          WHERE ((r.riga ~ '''E_[A-Z0-9_]+'''::text) AND (r.riga !~ '^\s*--'::text) AND (EXISTS ( SELECT 1
                   FROM righe p2
                  WHERE ((p2.oid = r.oid) AND ((p2.n >= (r.n - 6)) AND (p2.n <= r.n)) AND (p2.riga ~* 'fn_log_and_raise_error'::text)))))
        ), con_guardia AS (
         SELECT pt.sch,
            pt.fn,
            pt.oid,
            pt.n,
            pt.codice,
            ( SELECT g.riga
                   FROM righe g
                  WHERE ((g.oid = pt.oid) AND (g.n <= pt.n) AND (g.n >= (pt.n - 25)) AND (g.riga ~* '^\s*(IF|ELSIF|ELSE|EXCEPTION\s+WHEN|WHEN\s+OTHERS|WHEN\s+SQLSTATE)\M'::text))
                  ORDER BY g.n DESC
                 LIMIT 1) AS guardia
           FROM punti pt
        ), classificato AS (
         SELECT c.codice,
            ((c.sch || '.'::text) || c.fn) AS funzione,
                CASE
                    WHEN (c.guardia ~* '(EXCEPTION\s+WHEN|WHEN\s+OTHERS|WHEN\s+SQLSTATE)'::text) THEN 'ECCEZIONE'::text
                    WHEN (c.guardia ~* '^\s*IF\s+NOT\s+FOUND\M'::text) THEN 'NOT_FOUND'::text
                    WHEN ((c.guardia ~* '(\mIS\s+NULL\M|<=\s*0|<\s*0)'::text) AND (c.guardia ~* '\mp_\w+'::text)) THEN 'PARAMETRO'::text
                    WHEN (c.guardia ~* 'NOT\s+IN\s*\('::text) THEN 'ENUM'::text
                    ELSE 'IGNOTO'::text
                END AS famiglia
           FROM con_guardia c
          WHERE (c.guardia IS NOT NULL)
        )
 SELECT codice,
    (count(*))::integer AS n_punti,
    (count(DISTINCT funzione))::integer AS n_funzioni,
    array_agg(DISTINCT famiglia ORDER BY famiglia) AS famiglie,
    (count(DISTINCT famiglia))::integer AS n_famiglie,
    (count(DISTINCT famiglia) FILTER (WHERE (famiglia <> 'IGNOTO'::text)))::integer AS n_famiglie_note,
    bool_and((famiglia = 'IGNOTO'::text)) AS solo_ignoto
   FROM classificato
  GROUP BY codice;
```


---
{% include-markdown "signature-core.md" %}
