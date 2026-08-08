# 🔍 View `vw_codici_errore_forme_condizione`

> 📝 **Descrizione**
>
> Misura degli accumulatori sulla FORMA DELLA CONDIZIONE al punto che solleva (non sul dominio della funzione: quell'asse segnalava E_VALIDAZIONE, che e' il caso su cui la risposta e' no). NON filtra di proposito.
> TRE query canoniche, da usare INSIEME.
> (1) CANDIDATI — SELECT codice, n_punti, famiglie FROM dbops.vw_codici_errore_forme_condizione WHERE n_famiglie_note &gt; 1 ORDER BY n_punti DESC;
> (2) COPERTURA, senza cui la (1) si legge come una verita' — SELECT count(*) AS codici, count(*) FILTER (WHERE NOT solo_ignoto) AS classificati, count(*) FILTER (WHERE solo_ignoto) AS invisibili FROM dbops.vw_codici_errore_forme_condizione;
> (3) LA CLASSE E' ANCORA VERA? incrocia le due letture indipendenti dello stesso codice — la guardia (cosa FA il punto) e la classe (cosa DICE il catalogo). E' la query che ha trovato E_ERRORE_PARAMETRI, 4 punti su 13 che dicevano il falso:
>     SELECT unnest(f.famiglie) AS famiglia, c.classe, count(*) AS codici
>       FROM dbops.vw_codici_errore_forme_condizione f
>       JOIN config.codici_errore c USING (codice)
>      WHERE NOT f.solo_ignoto AND c.obsoleto_dal IS NULL
>      GROUP BY 1,2 ORDER BY 1, 3 DESC;
> COME SI LEGGE LA (3): le righe famiglia = IGNOTO NON sono una famiglia, sono la misura che dichiara di non saper leggere quella guardia — vanno lasciate (toglierle farebbe sembrare piena la copertura) ma non lette come un incrocio. E "fuori dominante" non vuol dire sbagliato: NOT_FOUND ha 19 codici su NON_TROVATO e 20 altrove, e la maggioranza dei 20 e' deliberata ("guard parametro NULL riconducibile a NOT FOUND", scritto dentro le funzioni). E' una lista DA GUARDARE, non una lista di difetti.
> Al 2026-08-08: 344 codici, 75 classificati, 269 invisibili. E' una MISURA, non un cancello: un codice legittimamente trasversale esiste. Implementazione a window function (20260808-01): 349 ms, contro i 145 secondi della prima versione a sottoquery correlate.

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
