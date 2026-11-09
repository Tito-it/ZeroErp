{% include-markdown "it/dbzero/dbops/manual/vw_punti_canale_campo.md" %}
# 🔍 View `vw_punti_canale_campo`

> 📝 **Descrizione**
>
> La meta' database del presidio C2 (brief-be-presidio-ui-action-e-canale-campi §4): per ogni (funzione dal corpo leggibile, plpgsql o sql — dbops.fn_corpo_leggibile —, codice E_*) COME il codice viene sollevato e SE il context porta la chiave che script.fn_log_and_raise_error legge per la COLUMN dell'eccezione ('campo', ripiego 'parametro') — cioe' il canale che a video accende il campo del form (fields -&gt; campiErrati), l'unico che realizza la promessa ui_action = highlight_form_fields.
> via: DIRETTO (chiamata a fn_log_and_raise_error col codice letterale, o col codice in variabile), PRIMO_MOTIVO (il codice di un motivo, via fn_raise_primo_motivo_se_presente o a mano: codici = UNIONE delle fn_check_* del corpo, da vw_funzioni_check_codici), MOTIVO (la fn_check_* che lo emette: sede del campo, non un sito), NOMINATO (letterale nel corpo, mai sollevato con l'helper: canale NULL).
> canale: IN_CHIAMATA (chiave nella chiamata, o p_campo letterale, o nel motivo della check), IN_VARIABILE (in una variabile del corpo, o non attribuibile — mai un «ok» silenzioso), CHIAVE_NON_LETTA (la colonna sta nel context come CHIAVE: sanabile, nome_in_chiave dice quale), NESSUNO. chiave: campo / parametro.
> ⭐ Per (funzione, codice) il canale e' il MIGLIORE fra le chiamate attribuite — la regola e' «almeno un punto» — e n_chiamate / n_con_canale dicono quando una funzione lo porta in 2 chiamate su 3. Il verso 1 del presidio si legge da canale IN (IN_CHIAMATA, IN_VARIABILE) su via IN (DIRETTO, PRIMO_MOTIVO); il verso 2 da n_con_canale = n_chiamate.
> ⭐ rev 20261103-02: i codici della funzione sono quelli del corpo PIU' quelli che un trigger le passa negli ARGOMENTI (dbops.vw_codici_errore_argomenti_trigger): un building block trigger che riceve il codice da TG_ARGV e lo solleva da una variabile e' un sito DIRETTO, attribuito al massimo IN_VARIABILE. Prima per la vista quel sito non esisteva (D24).
> ⚠️ Euristica sul sorgente senza commenti: chiamata = testo fino al primo `;`; p_campo letto a un livello di parentesi; solo i corpi leggibili (plpgsql e sql); i RAISE diretti non si vedono. Gli helper sono esclusi. Presidio: db/pgtap/dbops/test-punti-canale-campo-v1.sql.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_punti_canale_campo
WITH (security_invoker=true) AS
WITH funzioni AS MATERIALIZED (
         SELECT p.oid,
            (((n.nspname)::text || '.'::text) || (p.proname)::text) AS funzione,
            (dbops.fn_corpo_funzione(p.oid) COLLATE "C") AS sorgente
           FROM (pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
          WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND dbops.fn_corpo_leggibile(p.prolang) AND (NOT ((n.nspname = 'script'::name) AND (p.proname = ANY (ARRAY['fn_log_and_raise_error'::name, 'fn_raise_primo_motivo_se_presente'::name])))))
        ), letterali AS (
         SELECT f.oid,
            f.funzione,
            m.m[1] AS codice
           FROM (funzioni f
             CROSS JOIN LATERAL regexp_matches(f.sorgente, '''(E_[A-Z0-9_]+)'''::text, 'g'::text) m(m))
        UNION
         SELECT f.oid,
            f.funzione,
            t.codice
           FROM (funzioni f
             JOIN dbops.vw_codici_errore_argomenti_trigger t ON ((t.funzione_oid = f.oid)))
        ), variabili_con_chiave AS MATERIALIZED (
         SELECT DISTINCT f.oid,
            m.m[1] AS variabile,
                CASE
                    WHEN (m.m[2] = 'campo'::text) THEN 'campo'::text
                    ELSE 'parametro'::text
                END AS chiave
           FROM (funzioni f
             CROSS JOIN LATERAL regexp_matches(f.sorgente, '\m([a-z_][a-z0-9_]*)\s*:=\s*[^;]*''(campo|parametro)''\s*,'::text, 'g'::text) m(m))
        ), chiamate AS MATERIALIZED (
         SELECT f.oid,
            f.funzione,
            m.k AS n,
                CASE
                    WHEN (m.t ~ '^fn_raise_primo_motivo_se_presente'::text) THEN 'PRIMO_MOTIVO'::text
                    WHEN (m.t ~ '->>\s*''codice'''::text) THEN 'PRIMO_MOTIVO'::text
                    ELSE 'DIRETTO'::text
                END AS via,
            m.t AS testo
           FROM (funzioni f
             CROSS JOIN LATERAL ( SELECT r.m[1] AS t,
                    r.k
                   FROM regexp_matches(f.sorgente, '((?:fn_log_and_raise_error|fn_raise_primo_motivo_se_presente)\s*\([^;]*;)'::text, 'g'::text) WITH ORDINALITY r(m, k)) m)
        ), chiamate_variabile AS (
         SELECT c.oid,
            c.n,
            min(v.chiave) AS chiave
           FROM (chiamate c
             JOIN variabili_con_chiave v ON (((v.oid = c.oid) AND (c.testo ~ (('\m'::text || v.variabile) || '\M'::text)))))
          GROUP BY c.oid, c.n
        ), chiamate_classificate AS (
         SELECT c.oid,
            c.funzione,
            c.n,
            c.via,
            c.testo,
            (regexp_match(c.testo, '^fn_raise_primo_motivo_se_presente\s*\(\s*(?:''(?:[^'']|'''')*''|[^,()'']+(?:\([^()]*\))?)\s*,\s*(?:''(?:[^'']|'''')*''|[^,()'']+(?:\([^()]*\))?)\s*,\s*(?:''(?:[^'']|'''')*''|[^,()'']+(?:\([^()]*\))?)\s*,\s*([^,()]+?)\s*[,)]'::text))[1] AS p_campo,
            (c.testo ~ '''campo''\s*,'::text) AS ha_campo,
            (c.testo ~ '''parametro''\s*,'::text) AS ha_parametro,
            cv.chiave AS chiave_in_variabile,
            (regexp_match(c.testo, '''([a-z_][a-z0-9_]*)''\s*,\s*(?:NEW|OLD)\.\1\M'::text))[1] AS nome_in_chiave
           FROM (chiamate c
             LEFT JOIN chiamate_variabile cv ON (((cv.oid = c.oid) AND (cv.n = c.n))))
        ), chiamate_canale AS (
         SELECT cc.oid,
            cc.funzione,
            cc.n,
            cc.via,
            cc.testo,
            cc.p_campo,
            cc.ha_campo,
            cc.ha_parametro,
            cc.chiave_in_variabile,
            cc.nome_in_chiave,
                CASE
                    WHEN (cc.ha_campo OR cc.ha_parametro) THEN 'IN_CHIAMATA'::text
                    WHEN (cc.p_campo ~ '^''[^'']+''$'::text) THEN 'IN_CHIAMATA'::text
                    WHEN (cc.chiave_in_variabile IS NOT NULL) THEN 'IN_VARIABILE'::text
                    WHEN ((cc.p_campo ~ '^[a-z_][a-z0-9_]*$'::text) AND (upper(cc.p_campo) <> 'NULL'::text)) THEN 'IN_VARIABILE'::text
                    WHEN (cc.nome_in_chiave IS NOT NULL) THEN 'CHIAVE_NON_LETTA'::text
                    ELSE 'NESSUNO'::text
                END AS canale,
                CASE
                    WHEN cc.ha_campo THEN 'campo'::text
                    WHEN (cc.p_campo ~ '^''[^'']+''$'::text) THEN 'campo'::text
                    WHEN cc.ha_parametro THEN 'parametro'::text
                    ELSE cc.chiave_in_variabile
                END AS chiave
           FROM chiamate_classificate cc
        ), rango AS (
         SELECT r.canale,
            r.rango
           FROM ( VALUES ('NESSUNO'::text,0), ('CHIAVE_NON_LETTA'::text,1), ('IN_VARIABILE'::text,2), ('IN_CHIAMATA'::text,3)) r(canale, rango)
        ), diretti AS (
         SELECT cc.oid,
            cc.funzione,
            m.m[1] AS codice,
            cc.n,
            cc.canale,
            cc.chiave,
            cc.nome_in_chiave
           FROM (chiamate_canale cc
             CROSS JOIN LATERAL regexp_matches(cc.testo, '''(E_[A-Z0-9_]+)'''::text, 'g'::text) m(m))
          WHERE (cc.via = 'DIRETTO'::text)
        ), diretti_variabile AS (
         SELECT l.oid,
            l.funzione,
            l.codice,
            cc.n,
                CASE
                    WHEN (cc.canale = 'IN_CHIAMATA'::text) THEN 'IN_VARIABILE'::text
                    ELSE cc.canale
                END AS canale,
            cc.chiave,
            cc.nome_in_chiave
           FROM (letterali l
             JOIN chiamate_canale cc ON (((cc.oid = l.oid) AND (cc.via = 'DIRETTO'::text) AND (cc.testo !~ '''E_[A-Z0-9_]+'''::text))))
          WHERE (NOT (EXISTS ( SELECT 1
                   FROM diretti d
                  WHERE ((d.oid = l.oid) AND (d.codice = l.codice)))))
        ), primo_motivo AS (
         SELECT cc.oid,
            cc.funzione,
            k.codice,
            cc.n,
                CASE
                    WHEN (cc.canale = 'IN_CHIAMATA'::text) THEN 'IN_CHIAMATA'::text
                    WHEN (k.motivo_chiave IS NOT NULL) THEN 'IN_CHIAMATA'::text
                    ELSE cc.canale
                END AS canale,
            COALESCE(cc.chiave, k.motivo_chiave) AS chiave,
            cc.nome_in_chiave,
            k.check_funzione
           FROM (chiamate_canale cc
             LEFT JOIN dbops.vw_funzioni_check_codici k ON ((k.funzione = cc.funzione)))
          WHERE (cc.via = 'PRIMO_MOTIVO'::text)
        ), motivo AS (
         SELECT DISTINCT ((k.check_schema || '.'::text) || k.check_funzione) AS funzione,
            k.codice,
                CASE
                    WHEN (k.motivo_chiave IS NOT NULL) THEN 'IN_CHIAMATA'::text
                    ELSE 'NESSUNO'::text
                END AS canale,
            k.motivo_chiave AS chiave
           FROM dbops.vw_funzioni_check_codici k
          WHERE (k.codice IS NOT NULL)
        ), tutti AS (
         SELECT diretti.oid,
            diretti.funzione,
            diretti.codice,
            'DIRETTO'::text AS via,
            diretti.n,
            diretti.canale,
            diretti.chiave,
            diretti.nome_in_chiave,
            NULL::text AS check_funzione
           FROM diretti
        UNION ALL
         SELECT diretti_variabile.oid,
            diretti_variabile.funzione,
            diretti_variabile.codice,
            'DIRETTO'::text,
            diretti_variabile.n,
            diretti_variabile.canale,
            diretti_variabile.chiave,
            diretti_variabile.nome_in_chiave,
            NULL::text
           FROM diretti_variabile
        UNION ALL
         SELECT primo_motivo.oid,
            primo_motivo.funzione,
            primo_motivo.codice,
            'PRIMO_MOTIVO'::text,
            primo_motivo.n,
            primo_motivo.canale,
            primo_motivo.chiave,
            primo_motivo.nome_in_chiave,
            primo_motivo.check_funzione
           FROM primo_motivo
        ), aggregati AS (
         SELECT t.funzione,
            t.codice,
            t.via,
            (array_agg(t.canale ORDER BY r.rango DESC, t.n))[1] AS canale,
            (array_agg(t.chiave ORDER BY r.rango DESC, t.n))[1] AS chiave,
            (array_agg(t.nome_in_chiave ORDER BY r.rango DESC, t.n))[1] AS nome_in_chiave,
            (count(DISTINCT t.n))::integer AS n_chiamate,
            (count(DISTINCT t.n) FILTER (WHERE (t.canale = ANY (ARRAY['IN_CHIAMATA'::text, 'IN_VARIABILE'::text]))))::integer AS n_con_canale,
            string_agg(DISTINCT t.check_funzione, ', '::text ORDER BY t.check_funzione) AS check_funzioni
           FROM (tutti t
             JOIN rango r ON ((r.canale = t.canale)))
          GROUP BY t.funzione, t.codice, t.via
        )
 SELECT aggregati.funzione,
    aggregati.codice,
    aggregati.via,
    aggregati.canale,
    aggregati.chiave,
    aggregati.nome_in_chiave,
    aggregati.n_chiamate,
    aggregati.n_con_canale,
    aggregati.check_funzioni
   FROM aggregati
UNION ALL
 SELECT motivo.funzione,
    motivo.codice,
    'MOTIVO'::text AS via,
    motivo.canale,
    motivo.chiave,
    NULL::text AS nome_in_chiave,
    NULL::integer AS n_chiamate,
    NULL::integer AS n_con_canale,
    NULL::text AS check_funzioni
   FROM motivo
UNION ALL
 SELECT l.funzione,
    l.codice,
    'NOMINATO'::text AS via,
    NULL::text AS canale,
    NULL::text AS chiave,
    NULL::text AS nome_in_chiave,
    NULL::integer AS n_chiamate,
    NULL::integer AS n_con_canale,
    NULL::text AS check_funzioni
   FROM letterali l
  WHERE ((NOT (EXISTS ( SELECT 1
           FROM tutti t
          WHERE ((t.oid = l.oid) AND (t.codice = l.codice))))) AND (NOT (EXISTS ( SELECT 1
           FROM motivo m
          WHERE ((m.funzione = l.funzione) AND (m.codice = l.codice))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
