{% include-markdown "it/dbzero/dbops/manual/vw_punti_primo_motivo.md" %}
# 🔍 View `vw_punti_primo_motivo`

> 📝 **Descrizione**
>
> I punti che sollevano il codice del PRIMO MOTIVO di una script.fn_check_* (linee-guida-sql §12.5.2) A MANO — `fn_log_and_raise_error(... -&gt;&gt; 'codice'` — legati alla check da cui il motivo viene e ai codici che quella nomina. Una riga per (punto, check, codice). E' il RUBINETTO: i chiamanti di script.fn_raise_primo_motivo_se_presente (i bonificati) NON ci stanno, per costruzione.
> ⭐ DAL 2026-09-21 LA RISALITA punto-&gt;check-&gt;codici si LEGGE da dbops.vw_funzioni_check_codici (sede unica, condivisa col presidio C2 dbops.vw_punti_canale_campo); qui resta il solo marcatore dei punti. Prima viveva in una vista temporanea dentro db/pgtap/script/test-rubinetto-primo-motivo-v1.sql, poi in questa vista — e la seconda lettrice l'avrebbe ricopiata.
> COME SI USA. (A) il perimetro dell'helper: SELECT sch, fn, count(check_funzione) AS check_trovate, coalesce(bool_or(check_emette_valori), false) AS in_perimetro FROM dbops.vw_punti_primo_motivo GROUP BY 1,2; (B) i codici che un punto puo' sollevare: SELECT DISTINCT funzione, codice FROM dbops.vw_punti_primo_motivo WHERE codice IS NOT NULL.
> ⭐ PESSIMISTA DI PROPOSITO: i codici sono l'UNIONE di quelli nominati da TUTTE le check citate nel corpo, perche' la vista legge il testo e non sa quale ramo sia stato preso. Un presidio che scegliesse il ramo ottimista assolverebbe il caso che deve segnalare; un falso positivo qui costa una riga in piu' nel VARIADIC, non un rifiuto sbagliato.
> ⚠️ RAMO CIECO — un punto con check_funzione NULL non e' «a posto»: e' un sito che la lettura non sa legare alla sua check, e va visto. E' il test 3 di test-rubinetto-primo-motivo-v1.sql.
> ⛔ NON serve a dbops.vw_codici_errore_forme_condizione: quella classifica la forma della GUARDIA, e sopra questi punti la guardia e' sempre «IF jsonb_array_length(v_motivi) &gt; 0», che non dice niente. Li' si classifica dove il codice e' NOMINATO (changeSet 20260908-35).
> ⚠️ E' un'euristica sul corpo senza commenti (dbops.fn_corpo_funzione): riconosce la forma scritta, non il significato; una chiamata rimasta in un commento non e' un punto. Brief: brief-db-i-motivi-si-fermano-dentro-la-check.md (V-0); risalita condivisa: brief-be-presidio-ui-action-e-canale-campi §4.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_punti_primo_motivo
WITH (security_invoker=true) AS
WITH punti AS (
         SELECT (n.nspname)::text AS sch,
            (p.proname)::text AS fn
           FROM (pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
          WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (p.prolang = ( SELECT pg_language.oid
                   FROM pg_language
                  WHERE (pg_language.lanname = 'plpgsql'::name))) AND (p.prosrc ~ 'fn_log_and_raise_error\s*\([^;]*->> ''codice'''::text) AND ((dbops.fn_corpo_funzione(p.oid) COLLATE "C") ~ 'fn_log_and_raise_error\s*\([^;]*->> ''codice'''::text) AND (NOT ((n.nspname = 'script'::name) AND (p.proname = 'fn_raise_primo_motivo_se_presente'::name))))
        )
 SELECT pt.sch,
    pt.fn,
    ((pt.sch || '.'::text) || pt.fn) AS funzione,
    k.check_schema,
    k.check_funzione,
    k.check_emette_valori,
    k.codice
   FROM (punti pt
     LEFT JOIN dbops.vw_funzioni_check_codici k ON (((k.sch = pt.sch) AND (k.fn = pt.fn))));
```

</div>


---
{% include-markdown "signature-core.md" %}
