# 🔍 View `vw_punti_primo_motivo`

> 📝 **Descrizione**
>
> I punti che sollevano il codice del PRIMO MOTIVO di una script.fn_check_* (linee-guida-sql §12.5.2), legati alla check da cui il motivo viene e ai codici che quella nomina. Una riga per (punto, check, codice).
> SEDE UNICA della risalita punto-&gt;check: prima viveva in una vista temporanea dentro db/pgtap/script/test-rubinetto-primo-motivo-v1.sql, quindi ogni altro presidio che ne avesse bisogno se la sarebbe ricopiata — ed e' cosi' che due presidi sullo stesso fatto cominciano a dissentire.
> COME SI USA. (A) il perimetro dell'helper: SELECT sch, fn, count(check_funzione) AS check_trovate, coalesce(bool_or(check_emette_valori), false) AS in_perimetro FROM dbops.vw_punti_primo_motivo GROUP BY 1,2; (B) i codici che un punto puo' sollevare: SELECT DISTINCT funzione, codice FROM dbops.vw_punti_primo_motivo WHERE codice IS NOT NULL.
> ⭐ PESSIMISTA DI PROPOSITO, ed e' la scelta portante: i codici sono l'UNIONE di quelli nominati da TUTTE le check citate nel corpo, perche' la vista legge il testo e non sa quale ramo sia stato preso. Un presidio che scegliesse il ramo ottimista assolverebbe il caso che deve segnalare; e un falso positivo qui costa una riga in piu' nel VARIADIC, non un rifiuto sbagliato.
> ⚠️ RAMO CIECO — un punto con check_funzione NULL non e' «a posto»: e' un sito che la lettura non sa legare alla sua check, e va visto. E' il test 3 di test-rubinetto-primo-motivo-v1.sql.
> ⛔ NON serve a dbops.vw_codici_errore_forme_condizione: quella classifica la forma della GUARDIA, e sopra questi punti la guardia e' sempre «IF jsonb_array_length(v_motivi) &gt; 0», che non dice niente. Li' si classifica dove il codice e' NOMINATO (changeSet 20260908-35).
> ⚠️ E' un'euristica su pg_proc.prosrc: riconosce la forma scritta, non il significato. Brief: docs/it/dev/work-in-progress/brief-db-i-motivi-si-fermano-dentro-la-check.md, passo V-0.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW dbops.vw_punti_primo_motivo
WITH (security_invoker=true) AS
WITH punti AS (
         SELECT (n.nspname)::text AS sch,
            (p.proname)::text AS fn,
            p.oid,
            p.prosrc
           FROM (pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
          WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (p.prolang = ( SELECT pg_language.oid
                   FROM pg_language
                  WHERE (pg_language.lanname = 'plpgsql'::name))) AND (p.prosrc ~ 'fn_log_and_raise_error\s*\([^;]*->> ''codice'''::text) AND (NOT ((n.nspname = 'script'::name) AND (p.proname = 'fn_raise_primo_motivo_se_presente'::name))))
        ), legami AS (
         SELECT DISTINCT pt_1.sch,
            pt_1.fn,
            m.m[1] AS csch,
            m.m[2] AS cfn
           FROM (punti pt_1
             CROSS JOIN LATERAL regexp_matches(pt_1.prosrc, '(\w+)\.(fn_check_\w+)\s*\('::text, 'g'::text) m(m))
        ), check_viste AS (
         SELECT l.sch,
            l.fn,
            l.csch,
            l.cfn,
            (c.prosrc ~ '''valori'''::text) AS emette_valori,
            c.prosrc AS csrc
           FROM ((legami l
             JOIN pg_namespace cn ON ((cn.nspname = l.csch)))
             JOIN pg_proc c ON (((c.proname = l.cfn) AND (c.pronamespace = cn.oid))))
        )
 SELECT pt.sch,
    pt.fn,
    ((pt.sch || '.'::text) || pt.fn) AS funzione,
    cv.csch AS check_schema,
    cv.cfn AS check_funzione,
    cv.emette_valori AS check_emette_valori,
    mc.m[1] AS codice
   FROM ((punti pt
     LEFT JOIN check_viste cv ON (((cv.sch = pt.sch) AND (cv.fn = pt.fn))))
     LEFT JOIN LATERAL regexp_matches(cv.csrc, '''codice''\s*,\s*''(E_[A-Z0-9_]+)'''::text, 'g'::text) mc(m) ON (true));
```


---
{% include-markdown "signature-core.md" %}
