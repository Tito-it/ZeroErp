{% include-markdown "it/dbzero/dbops/manual/vw_stati_check_scrittori.md" %}
# 🔍 View `vw_stati_check_scrittori`

> 📝 **Descrizione**
>
> PRESIDIO C1 — uno stato previsto dal modello (nel CHECK a lista di una colonna di stato) e mai scritto. Una riga per (colonna, valore) con il suo esito: SCRITTO (una funzione scrive la tabella e nomina il letterale, oppure lo passa a uno scrittore posizionale: il secondo salto), SCRITTO_DA_DEFAULT, DICHIARATO_APPLICAZIONE / ESENTE (sta in dbops.stati_check_dichiarazioni), NON_DICHIARATO (il debito da sanare) e DEBITO_ESTINTO nei due versi. ⚠️ Il criterio e' TESTUALE e ha due limiti, dichiarati nel suo pgTAP: nominare non e' scrivere (test 6) e a tre salti il letterale non si segue piu' (test 9). ⭐ Rev 2026-09-22: stessa misura, estratta UNA volta invece che provata per coppia — i nomi scritti da ogni funzione e i letterali citati si ricavano con un passaggio solo, poi si confrontano per uguaglianza. Output identico riga per riga (EXCEPT nei due versi su dbdev), costo per chiamata da ~535 ms a ~230 ms. ⛔ Rev 2026-09-23: le funzioni di fixture pgTAP (prefisso fn_pgtap_ in dbops e script) NON contano, ne' come scrittori ne' come chiamanti: il presidio misura il sistema, non le fixture che lo collaudano. Brief: brief-db-presidio-stati-mai-scritti §3-bis; brief-db-fixture-che-costruiscono-giro-2 §11.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

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
            (dbops.fn_corpo_funzione(p.oid) COLLATE "C") AS sorgente
           FROM (pg_proc p
             JOIN pg_namespace pn ON ((pn.oid = p.pronamespace)))
          WHERE ((pn.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND dbops.fn_corpo_leggibile(p.prolang) AND (NOT ((pn.nspname = ANY (ARRAY['dbops'::name, 'script'::name])) AND ((p.proname)::text ~~ 'fn\_pgtap\_%'::text))))
        ), scritture AS MATERIALIZED (
         SELECT f.oid,
            f.proname,
            f.funzione,
            f.sorgente,
            lower(m.m[3]) AS tabella_scritta
           FROM funzioni f,
            LATERAL regexp_matches(f.sorgente, '(?i)(update|insert\s+into|merge\s+into)\s+(only\s+)?([a-z_][a-z0-9_$]*\.[a-z_][a-z0-9_$]*)'::text, 'g'::text) m(m)
        ), scrittori AS MATERIALIZED (
         SELECT DISTINCT t.schema_tabella,
            t.nome_tabella,
            s.oid,
            s.proname,
            s.funzione,
            s.sorgente
           FROM (( SELECT DISTINCT colonne.schema_tabella,
                    colonne.nome_tabella
                   FROM colonne) t
             JOIN scritture s ON ((s.tabella_scritta = ((t.schema_tabella || '.'::text) || t.nome_tabella))))
        ), letterali AS (
         SELECT (('''('::text || string_agg(DISTINCT regexp_replace(v.valore, '([.^$|()\[\]{}*+?\\-])'::text, '\\\&'::text, 'g'::text), '|'::text)) || ')'''::text) AS rx
           FROM valori v
        ), funzioni_citanti AS MATERIALIZED (
         SELECT f.oid,
            f.proname,
            f.funzione,
            f.sorgente
           FROM funzioni f,
            letterali l
          WHERE (f.sorgente ~ l.rx)
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
             JOIN scrittori s ON (((s.schema_tabella = v.schema_tabella) AND (s.nome_tabella = v.nome_tabella))))
             JOIN funzioni_citanti c ON (((c.oid <> s.oid) AND (strpos(c.sorgente, v.letterale) > 0) AND (strpos(c.sorgente, s.proname) > 0) AND (c.sorgente ~ ((('\m'::text || s.proname) || '\s*\([^;]*'::text) || v.letterale)))))
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

</div>


---
{% include-markdown "signature-core.md" %}
