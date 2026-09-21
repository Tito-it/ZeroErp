{% include-markdown "it/dbzero/dbops/manual/vw_stati_check_scrittori.md" %}
# 🔍 View `vw_stati_check_scrittori`

> 📝 **Descrizione**
>
> La misura del presidio C1: per ogni valore ammesso dal CHECK di una colonna di stato (una colonna, forma = ANY(ARRAY[...]) in entrambe le scritture del cast, nome ^stato(_|$) | status | esito | severity — il filtro sul nome e' il confine dichiarato fra stato e classificazione), chi lo scrive: il DEFAULT di colonna, una funzione che scrive la tabella col letterale nel corpo (scrittori_fn), una funzione che chiama uno scrittore passandogli il letterale nella chiamata (scrittori_indiretti). Esito: SCRITTO, SCRITTO_DA_DEFAULT, DICHIARATO_APPLICAZIONE e ESENTE (dal registro dbops.stati_check_dichiarazioni), DEBITO_ESTINTO (riga di registro il cui valore ha trovato uno scrittore o e' uscito dal CHECK: da togliere), NON_DICHIARATO (allarme). ⛔ L'invariante NON e' «vuota»: e' «nessuna NON_DICHIARATO e nessuna DEBITO_ESTINTO». ⚠️ Limiti: nominare non e' scrivere (un letterale in un WHERE dentro uno scrittore conta); due salti e non tre; una copia colonna→colonna e un valore in variabile fuori dallo scrittore restano invisibili (si dichiarano ESENTE); un repository Python il database non lo vede (si dichiara APPLICAZIONE, lo verifica il backend). Sorgenti letti senza commenti. Presidio: db/pgtap/dbops/test-stati-check-scrittori-v1.sql. Brief: brief-db-presidio-stati-mai-scritti §2 e §3-bis.

```sql
CREATE OR REPLACE VIEW dbops.vw_stati_check_scrittori AS
WITH colonne AS (
         SELECT (n.nspname)::text AS schema_tabella,
            (c.relname)::text AS nome_tabella,
            (a.attname)::text AS colonna,
            k.oid AS con_oid,
            (k.conname)::text AS vincolo,
            "substring"(pg_get_expr(d.adbin, d.adrelid), '^''([^'']*)'''::text) AS valore_default
           FROM ((((pg_constraint k
             JOIN pg_class c ON ((c.oid = k.conrelid)))
             JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
             JOIN pg_attribute a ON (((a.attrelid = c.oid) AND (a.attnum = k.conkey[1]))))
             LEFT JOIN pg_attrdef d ON (((d.adrelid = c.oid) AND (d.adnum = a.attnum))))
          WHERE ((k.contype = 'c'::"char") AND (array_length(k.conkey, 1) = 1) AND (c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])) AND (n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (pg_get_constraintdef(k.oid) ~ '= ANY \(\(?ARRAY\['::text) AND ((a.attname ~ '^stato(_|$)'::text) OR (a.attname = 'status'::name) OR (a.attname = 'esito'::name) OR (a.attname = 'severity'::name)))
        ), valori AS (
         SELECT co.schema_tabella,
            co.nome_tabella,
            co.colonna,
            co.con_oid,
            co.vincolo,
            co.valore_default,
            m.m[1] AS valore,
            ((''''::text || m.m[1]) || ''''::text) AS letterale
           FROM colonne co,
            LATERAL regexp_matches(pg_get_constraintdef(co.con_oid), '''([^'']*)''::'::text, 'g'::text) m(m)
        ), funzioni AS MATERIALIZED (
         SELECT p.oid,
            (p.proname)::text AS proname,
            (((pn.nspname)::text || '.'::text) || (p.proname)::text) AS funzione,
            regexp_replace(regexp_replace(p.prosrc, '/\*.*?\*/'::text, ''::text, 'g'::text), '--[^\n]*'::text, ''::text, 'g'::text) AS sorgente
           FROM ((pg_proc p
             JOIN pg_namespace pn ON ((pn.oid = p.pronamespace)))
             JOIN pg_language l ON ((l.oid = p.prolang)))
          WHERE ((pn.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (l.lanname = ANY (ARRAY['plpgsql'::name, 'sql'::name])))
        ), scrittori AS MATERIALIZED (
         SELECT t.schema_tabella,
            t.nome_tabella,
            f.oid,
            f.proname,
            f.funzione,
            f.sorgente
           FROM (( SELECT DISTINCT colonne.schema_tabella,
                    colonne.nome_tabella
                   FROM colonne) t
             JOIN funzioni f ON (((strpos(lower(f.sorgente), ((t.schema_tabella || '.'::text) || t.nome_tabella)) > 0) AND (f.sorgente ~* (((('(UPDATE|INSERT\s+INTO|MERGE\s+INTO)\s+(ONLY\s+)?'::text || t.schema_tabella) || '\.'::text) || t.nome_tabella) || '\M'::text)))))
        ), diretti AS (
         SELECT v.con_oid,
            v.valore,
            s.funzione
           FROM (valori v
             JOIN scrittori s ON (((s.schema_tabella = v.schema_tabella) AND (s.nome_tabella = v.nome_tabella) AND (strpos(s.sorgente, v.letterale) > 0))))
        ), indiretti AS (
         SELECT DISTINCT v.con_oid,
            v.valore,
            c.funzione
           FROM ((valori v
             JOIN funzioni c ON ((strpos(c.sorgente, v.letterale) > 0)))
             JOIN scrittori s ON (((s.schema_tabella = v.schema_tabella) AND (s.nome_tabella = v.nome_tabella) AND (s.oid <> c.oid) AND (strpos(c.sorgente, s.proname) > 0) AND (c.sorgente ~ ((('\m'::text || s.proname) || '\s*\([^;]*'::text) || v.letterale)))))
        ), misura AS (
         SELECT v.schema_tabella,
            v.nome_tabella,
            v.colonna,
            v.vincolo,
            v.valore,
            (v.valore_default = v.valore) AS ha_default,
            ( SELECT (count(*))::integer AS count
                   FROM diretti x
                  WHERE ((x.con_oid = v.con_oid) AND (x.valore = v.valore))) AS scrittori_fn,
            ( SELECT (count(*))::integer AS count
                   FROM indiretti x
                  WHERE ((x.con_oid = v.con_oid) AND (x.valore = v.valore))) AS scrittori_indiretti,
            ( SELECT string_agg(DISTINCT x.funzione, ', '::text ORDER BY x.funzione) AS string_agg
                   FROM ( SELECT diretti.funzione
                           FROM diretti
                          WHERE ((diretti.con_oid = v.con_oid) AND (diretti.valore = v.valore))
                        UNION ALL
                         SELECT indiretti.funzione
                           FROM indiretti
                          WHERE ((indiretti.con_oid = v.con_oid) AND (indiretti.valore = v.valore))) x) AS scrittori_nomi,
            ( SELECT string_agg(DISTINCT s.funzione, ', '::text ORDER BY s.funzione) AS string_agg
                   FROM scrittori s
                  WHERE ((s.schema_tabella = v.schema_tabella) AND (s.nome_tabella = v.nome_tabella))) AS scrittori_tabella
           FROM valori v
        )
 SELECT m.schema_tabella,
    m.nome_tabella,
    m.colonna,
    m.vincolo,
    m.valore,
    m.ha_default,
    m.scrittori_fn,
    m.scrittori_indiretti,
    m.scrittori_nomi,
    m.scrittori_tabella,
        CASE
            WHEN ((m.scrittori_fn > 0) OR (m.scrittori_indiretti > 0)) THEN
            CASE
                WHEN (d.id IS NULL) THEN 'SCRITTO'::text
                ELSE 'DEBITO_ESTINTO'::text
            END
            WHEN m.ha_default THEN
            CASE
                WHEN (d.id IS NULL) THEN 'SCRITTO_DA_DEFAULT'::text
                ELSE 'DEBITO_ESTINTO'::text
            END
            WHEN (d.id IS NULL) THEN 'NON_DICHIARATO'::text
            WHEN (d.canale = 'APPLICAZIONE'::text) THEN 'DICHIARATO_APPLICAZIONE'::text
            ELSE 'ESENTE'::text
        END AS esito,
    d.canale,
    d.ragione,
    d.data_registrazione
   FROM (misura m
     LEFT JOIN dbops.stati_check_dichiarazioni d ON (((d.schema_tabella = m.schema_tabella) AND (d.nome_tabella = m.nome_tabella) AND (d.colonna = m.colonna) AND (d.valore = m.valore))))
UNION ALL
 SELECT d.schema_tabella,
    d.nome_tabella,
    d.colonna,
    NULL::text AS vincolo,
    d.valore,
    NULL::boolean AS ha_default,
    NULL::integer AS scrittori_fn,
    NULL::integer AS scrittori_indiretti,
    NULL::text AS scrittori_nomi,
    NULL::text AS scrittori_tabella,
    'DEBITO_ESTINTO'::text AS esito,
    d.canale,
    d.ragione,
    d.data_registrazione
   FROM dbops.stati_check_dichiarazioni d
  WHERE (NOT (EXISTS ( SELECT 1
           FROM valori v
          WHERE ((v.schema_tabella = d.schema_tabella) AND (v.nome_tabella = d.nome_tabella) AND (v.colonna = d.colonna) AND (v.valore = d.valore)))));
```


---
{% include-markdown "signature-core.md" %}
