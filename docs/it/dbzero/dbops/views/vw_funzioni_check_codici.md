{% include-markdown "it/dbzero/dbops/manual/vw_funzioni_check_codici.md" %}
# 🔍 View `vw_funzioni_check_codici`

> 📝 **Descrizione**
>
> SEDE UNICA della risalita «funzione plpgsql -&gt; fn_check_* nominate nel corpo -&gt; codici che quelle nominano come motivo». Una riga per (funzione, check, codice); codice NULL se la check non nomina motivi (il legame compare lo stesso). motivo_chiave = 'campo'/'parametro' se il MOTIVO che nomina il codice porta la chiave del canale nel suo dettaglio (che fn_raise_primo_motivo_se_presente fonde nel context) — PESSIMISTA: solo se tutti i motivi di quel codice la portano; n_motivi = quante volte la check lo nomina.
> LETTORI: dbops.vw_punti_primo_motivo (il rubinetto: i soli punti che sollevano il primo motivo a mano) e dbops.vw_punti_canale_campo (il presidio C2: tutti i siti, bonificati compresi). Prima la risalita viveva dentro la sola vw_punti_primo_motivo, e la seconda l'avrebbe ricopiata.
> ⚠️ Le fn_check_* si cercano nel sorgente SENZA commenti; una riga per (funzione, check, codice) — la derivazione precedente dava un doppione quando la check nomina lo stesso codice in due motivi. ⚠️ La finestra di un motivo NON e' «fino al ;»: le check a CTE costruiscono piu' motivi in uno statement, quindi il sorgente si spezza sulle occorrenze di 'codice',. ⚠️ Euristica su pg_proc.prosrc: riconosce la forma scritta, non il significato. Brief: brief-be-presidio-ui-action-e-canale-campi §4.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW dbops.vw_funzioni_check_codici
WITH (security_invoker=true) AS
WITH funzioni AS MATERIALIZED (
         SELECT p.oid,
            (n.nspname)::text AS sch,
            (p.proname)::text AS fn,
            (((n.nspname)::text || '.'::text) || (p.proname)::text) AS funzione,
            regexp_replace(regexp_replace(p.prosrc, '/\*.*?\*/'::text, ''::text, 'g'::text), '--[^\n]*'::text, ''::text, 'g'::text) AS sorgente
           FROM (pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
          WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (p.prolang = ( SELECT pg_language.oid
                   FROM pg_language
                  WHERE (pg_language.lanname = 'plpgsql'::name))))
        ), legami AS (
         SELECT DISTINCT f.oid,
            f.sch,
            f.fn,
            f.funzione,
            m_1.m[1] AS csch,
            m_1.m[2] AS cfn
           FROM (funzioni f
             CROSS JOIN LATERAL regexp_matches(f.sorgente, '(\w+)\.(fn_check_\w+)\s*\('::text, 'g'::text) m_1(m))
        ), checks AS MATERIALIZED (
         SELECT DISTINCT c_1.oid AS check_oid,
            l_1.csch,
            l_1.cfn,
            (c_1.prosrc ~ '''valori'''::text) AS emette_valori,
            regexp_replace(regexp_replace(c_1.prosrc, '/\*.*?\*/'::text, ''::text, 'g'::text), '--[^\n]*'::text, ''::text, 'g'::text) AS csrc
           FROM ((( SELECT DISTINCT legami.csch,
                    legami.cfn
                   FROM legami) l_1
             JOIN pg_namespace cn ON ((cn.nspname = l_1.csch)))
             JOIN pg_proc c_1 ON (((c_1.proname = l_1.cfn) AND (c_1.pronamespace = cn.oid))))
        ), motivi AS (
         SELECT c_1.check_oid,
            (regexp_match(s.pz, '^''(E_[A-Z0-9_]+)'''::text))[1] AS codice,
            split_part(s.pz, ';'::text, 1) AS finestra
           FROM (checks c_1
             CROSS JOIN LATERAL regexp_split_to_table(c_1.csrc, '''codice''\s*,\s*'::text) WITH ORDINALITY s(pz, k))
          WHERE (s.k > 1)
        ), motivi_per_codice AS (
         SELECT motivi.check_oid,
            motivi.codice,
            (count(*))::integer AS n_motivi,
                CASE
                    WHEN bool_and((motivi.finestra ~ '''campo''\s*,'::text)) THEN 'campo'::text
                    WHEN bool_and((motivi.finestra ~ '''(campo|parametro)''\s*,'::text)) THEN 'parametro'::text
                    ELSE NULL::text
                END AS motivo_chiave
           FROM motivi
          WHERE (motivi.codice IS NOT NULL)
          GROUP BY motivi.check_oid, motivi.codice
        )
 SELECT l.sch,
    l.fn,
    l.funzione,
    l.csch AS check_schema,
    l.cfn AS check_funzione,
    c.emette_valori AS check_emette_valori,
    m.codice,
    m.n_motivi,
    m.motivo_chiave
   FROM ((legami l
     JOIN checks c ON (((c.csch = l.csch) AND (c.cfn = l.cfn))))
     LEFT JOIN motivi_per_codice m ON ((m.check_oid = c.check_oid)));
```


---
{% include-markdown "signature-core.md" %}
