{% include-markdown "it/dbzero/dbops/manual/vw_codici_errore_forme_condizione.md" %}
# 🔍 View `vw_codici_errore_forme_condizione`

> 📝 **Descrizione**
>
> Misura degli accumulatori sulla FORMA DELLA CONDIZIONE al punto che solleva un codice (non sul dominio della funzione). NON filtra di proposito. Tre query canoniche, da usare INSIEME. (1) CANDIDATI: SELECT codice, n_punti, famiglie FROM dbops.vw_codici_errore_forme_condizione WHERE n_famiglie_note &gt; 1 ORDER BY n_punti DESC; (2) COPERTURA, senza cui la (1) si legge come una verita': SELECT count(*) AS codici, count(*) FILTER (WHERE NOT solo_ignoto) AS classificati, count(*) FILTER (WHERE solo_ignoto) AS invisibili FROM dbops.vw_codici_errore_forme_condizione; (3) LA CLASSE E' ANCORA VERA?, l'incrocio fra la guardia (cosa FA il punto) e la classe (cosa DICE il catalogo): SELECT unnest(f.famiglie) AS famiglia, c.classe, count(*) AS codici FROM dbops.vw_codici_errore_forme_condizione f JOIN config.codici_errore c USING (codice) WHERE NOT f.solo_ignoto AND c.obsoleto_dal IS NULL GROUP BY 1,2 ORDER BY 1, 3 DESC. Nella (3) le righe con famiglia IGNOTO non sono una famiglia: sono la misura che dichiara di non saper leggere quella guardia, e restano (toglierle farebbe sembrare piena la copertura); «fuori dominante» non vuol dire sbagliato. E' una lista DA GUARDARE, non di difetti. FAMIGLIE. VALORE_ATTESO: «il valore letto non e' quello ammesso» (x &lt;&gt; 'LETTERALE'), la forma delle guardie di stato e di perimetro; e' una famiglia a se' e non un ENUM allargato, perche' le letture di questa vista si confrontano nel tempo; il CASE la mette DOPO ENUM e PARAMETRO (un NOT IN resta ENUM, una guardia su un parametro nullo resta PARAMETRO). PARAMETRO non si legge su un campo di un record: in «IF p_ddt.causale_trasporto_id IS NULL» p_ddt e' il documento e la condizione e' un dato mancante (DATO_ERRATO), non un chiamante rotto (TECNICO); il p_ deve NON essere seguito da un punto, e se sulla riga c'e' anche un parametro vero resta PARAMETRO; chi non si legge cade in IGNOTO. Provato dai test 7-8 di db/pgtap/dbops/test-vw-codici-errore-motivo-nominato.sql. PUNTI. E' un punto anche la riga che DICHIARA un motivo ('codice', 'E_...') dentro una fn_check_* (il pattern «la madre chiama la check» di linee-guida-sql), con la guardia presa dall'IF che la precede dentro la check, dov'e' la condizione vera; NON si risale dalla chiamata alla check, perche' sopra il punto che solleva la guardia e' sempre «IF jsonb_array_length(v_motivi) &gt; 0», muta sul perche'. Il marcatore e' per FORMA, non per nome di funzione. Ogni codice distinto di una riga e' un punto, con la stessa guardia. Le righe si tagliano dal corpo letto da dbops.fn_corpo_funzione, senza commenti e con i letterali intatti; le distanze sono 6 righe per la chiamata vicina e 25 dalla guardia. IMPRECISIONE DICHIARATA: la forma prende anche del normale control-flow entro 25 righe da un RAISE (IF TG_OP = 'DELETE', IF v_id_type = 'uuid'): chi legge la (1) guarda i codici, non da' per buono il conteggio. PERIMETRO: il solo plpgsql, di proposito, a differenza delle viste sorelle sui codici (dbops.vw_codici_errore_da_dichiarare, dbops.vw_punti_canale_campo, dbops.vw_funzioni_check_codici, dbops.vw_punti_primo_motivo, dbops.vw_bersagli_non_dichiarati), che leggono ogni corpo leggibile: la guardia si riconosce dalle righe IF / ELSIF / ELSE / EXCEPTION WHEN, che una funzione sql non ha. Una funzione sql che solleva un codice resta visibile in dbops.vw_codici_errore_da_dichiarare. La vista e' una misura; il cancello e' il confronto in CI dello snapshot (scripts/sql/codici_errore_famiglie_snapshot.sql) con la sua baseline: un codice che allarga il proprio significato ferma la build. Implementata a window function.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

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
             CROSS JOIN LATERAL regexp_split_to_table((dbops.fn_corpo_funzione(p.oid) COLLATE "C"), '
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
            (r.riga ~ '''codice''\s*,\s*''E_[A-Z0-9_]+'''::text) AS e_motivo,
            (r.riga ~ '''E_[A-Z0-9_]+'''::text) AS ha_codice
           FROM righe r
        ), isole AS (
         SELECT m.sch,
            m.fn,
            m.oid,
            m.riga,
            m.n,
            m.e_chiamata,
            m.e_guardia,
            m.e_motivo,
            m.ha_codice,
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
            i.e_motivo,
            i.ha_codice,
            i.isola,
            i.chiamata_vicina,
            first_value(i.riga) OVER (PARTITION BY i.oid, i.isola ORDER BY i.n) AS guardia,
            first_value(i.n) OVER (PARTITION BY i.oid, i.isola ORDER BY i.n) AS n_guardia
           FROM isole i
        ), classificato AS (
         SELECT o.m[1] AS codice,
            p.oid,
            p.n,
            ((p.sch || '.'::text) || p.fn) AS funzione,
                CASE
                    WHEN (p.guardia ~* '(EXCEPTION\s+WHEN|WHEN\s+OTHERS|WHEN\s+SQLSTATE)'::text) THEN 'ECCEZIONE'::text
                    WHEN (p.guardia ~* '^\s*IF\s+NOT\s+FOUND\M'::text) THEN 'NOT_FOUND'::text
                    WHEN ((p.guardia ~* '(\mIS\s+NULL\M|<=\s*0|<\s*0)'::text) AND (p.guardia ~* '\mp_\w+\M(?!\s*\.)'::text)) THEN 'PARAMETRO'::text
                    WHEN (p.guardia ~* 'NOT\s+IN\s*\('::text) THEN 'ENUM'::text
                    WHEN (p.guardia ~* '(<>|!=|=)\s*''[A-Za-z0-9_]+'''::text) THEN 'VALORE_ATTESO'::text
                    ELSE 'IGNOTO'::text
                END AS famiglia
           FROM (propagata p
             CROSS JOIN LATERAL dbops.fn_regexp_occorrenze(p.riga, '''(E_[A-Z0-9_]+)'''::text) o(m))
          WHERE (p.ha_codice AND (p.chiamata_vicina OR p.e_motivo) AND (p.isola > 0) AND ((p.n - p.n_guardia) <= 25))
        )
 SELECT codice,
    (count(DISTINCT ROW(oid, n)))::integer AS n_punti,
    (count(DISTINCT funzione))::integer AS n_funzioni,
    array_agg(DISTINCT famiglia ORDER BY famiglia) AS famiglie,
    (count(DISTINCT famiglia))::integer AS n_famiglie,
    (count(DISTINCT famiglia) FILTER (WHERE (famiglia <> 'IGNOTO'::text)))::integer AS n_famiglie_note,
    bool_and((famiglia = 'IGNOTO'::text)) AS solo_ignoto
   FROM classificato
  GROUP BY codice;
```

</div>


---
{% include-markdown "signature-core.md" %}
