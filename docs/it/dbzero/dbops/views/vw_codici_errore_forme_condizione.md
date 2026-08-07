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
        ), marcata AS (
         SELECT r.sch,
            r.fn,
            r.oid,
            r.riga,
            r.n,
            (r.riga ~* 'fn_log_and_raise_error'::text) AS e_chiamata,
            (r.riga ~* '^\s*(IF|ELSIF|ELSE|EXCEPTION\s+WHEN|WHEN\s+OTHERS|WHEN\s+SQLSTATE)\M'::text) AS e_guardia,
                CASE
                    WHEN (r.riga !~ '^\s*--'::text) THEN (regexp_match(r.riga, '''(E_[A-Z0-9_]+)'''::text))[1]
                    ELSE NULL::text
                END AS codice
           FROM righe r
        ), isole AS (
         SELECT m.sch,
            m.fn,
            m.oid,
            m.riga,
            m.n,
            m.e_chiamata,
            m.e_guardia,
            m.codice,
            count(*) FILTER (WHERE m.e_guardia) OVER (PARTITION BY m.oid ORDER BY m.n) AS isola,
            bool_or(m.e_chiamata) OVER (PARTITION BY m.oid ORDER BY m.n ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS chiamata_vicina
           FROM marcata m
        ), propagata AS (
         SELECT i.sch,
            i.fn,
            i.oid,
            i.riga,
            i.n,
            i.e_chiamata,
            i.e_guardia,
            i.codice,
            i.isola,
            i.chiamata_vicina,
            first_value(i.riga) OVER (PARTITION BY i.oid, i.isola ORDER BY i.n) AS guardia,
            first_value(i.n) OVER (PARTITION BY i.oid, i.isola ORDER BY i.n) AS n_guardia
           FROM isole i
        ), classificato AS (
         SELECT p.codice,
            ((p.sch || '.'::text) || p.fn) AS funzione,
                CASE
                    WHEN (p.guardia ~* '(EXCEPTION\s+WHEN|WHEN\s+OTHERS|WHEN\s+SQLSTATE)'::text) THEN 'ECCEZIONE'::text
                    WHEN (p.guardia ~* '^\s*IF\s+NOT\s+FOUND\M'::text) THEN 'NOT_FOUND'::text
                    WHEN ((p.guardia ~* '(\mIS\s+NULL\M|<=\s*0|<\s*0)'::text) AND (p.guardia ~* '\mp_\w+'::text)) THEN 'PARAMETRO'::text
                    WHEN (p.guardia ~* 'NOT\s+IN\s*\('::text) THEN 'ENUM'::text
                    ELSE 'IGNOTO'::text
                END AS famiglia
           FROM propagata p
          WHERE ((p.codice IS NOT NULL) AND p.chiamata_vicina AND (p.isola > 0) AND ((p.n - p.n_guardia) <= 25))
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
