{% include-markdown "it/dbzero/dbops/manual/vw_funzioni_check_codici.md" %}
# 🔍 View `vw_funzioni_check_codici`

> 📝 **Descrizione**
>
> SEDE UNICA della risalita «funzione dal corpo leggibile (plpgsql o sql: dbops.fn_corpo_leggibile) -&gt; fn_check_* nominate nel corpo -&gt; codici che quelle nominano come motivo». Una riga per (funzione, check, codice); codice NULL se la check non nomina motivi (il legame compare lo stesso). motivo_chiave = 'campo'/'parametro' se il MOTIVO che nomina il codice porta la chiave del canale nel suo dettaglio (che fn_raise_primo_motivo_se_presente fonde nel context): PESSIMISTA, solo se tutti i motivi di quel codice la portano; n_motivi = quante volte la check lo nomina. LA DELEGA: una check che RESTITUISCE i motivi di un'altra fn_check_* (v_motivi || x.fn_check_…, v_m := x.fn_check_…, jsonb_agg sugli elementi) ne EREDITA i codici, a qualunque profondita'; una che la CONSUMA (count, EXISTS, IF) no: emette un motivo suo. Se nell'istruzione della delega il codice e' confrontato con dei letterali (-&gt;&gt; 'codice' = 'E_X' o IN (…)) eredita SOLO quelli: script.fn_check_prezzi_in_attesa eredita da fn_check_prezzi_autorizzati il solo E_DOC_PREZZO_PENDENTE. Anche check_emette_valori si propaga. &lt;&gt; e NOT IN non sono riconosciuti come filtro: si eredita tutto, cioe' un legame in piu', mai un ramo cieco. Lettori: dbops.vw_punti_primo_motivo (i soli punti che sollevano il primo motivo a mano) e dbops.vw_punti_canale_campo (tutti i siti). Le fn_check_* si cercano nel corpo SENZA commenti (dbops.fn_corpo_funzione, che lascia intatti i letterali); un codice che arriva da piu' strade si aggrega. La finestra di un motivo NON e' «fino al ;»: le check a CTE costruiscono piu' motivi in uno statement, quindi il corpo si spezza sulle occorrenze di 'codice',. Euristica sulla forma scritta, non sul significato. PRESTAZIONI, proprieta' invisibili nei risultati: un prefiltro prosrc LIKE '%fn\_check\_%' sulla CTE delle funzioni (piu' le sql BEGIN ATOMIC, che hanno prosrc vuoto e passano tutte al filtro sul corpo) tiene la stima sotto la soglia del JIT; le estrazioni passano da dbops.fn_regexp_occorrenze (ROWS 1), il taglio dei motivi da unnest(regexp_split_to_array), e le deleghe si estraggono una volta in una CTE MATERIALIZED. Un REPLACE che le perde non rompe niente e torna lento: le presidia db/pgtap/dbops/test-vw-funzioni-check-codici-sotto-jit-v1.sql.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_funzioni_check_codici
WITH (security_invoker=true) AS
WITH RECURSIVE funzioni AS MATERIALIZED (
         SELECT p.oid,
            (n.nspname)::text AS sch,
            (p.proname)::text AS fn,
            (((n.nspname)::text || '.'::text) || (p.proname)::text) AS funzione,
            (dbops.fn_corpo_funzione(p.oid) COLLATE "C") AS sorgente
           FROM (pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
          WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND dbops.fn_corpo_leggibile(p.prolang) AND ((p.prosrc ~~ '%fn\_check\_%'::text) OR (p.prosqlbody IS NOT NULL)))
        ), legami AS (
         SELECT DISTINCT f.oid,
            f.sch,
            f.fn,
            f.funzione,
            m_1.m[1] AS csch,
            m_1.m[2] AS cfn
           FROM (funzioni f
             CROSS JOIN LATERAL dbops.fn_regexp_occorrenze(f.sorgente, '(\w+)\.(fn_check_\w+)\s*\('::text) m_1(m))
        ), check_nomi(csch, cfn) AS (
         SELECT l_1.csch,
            l_1.cfn
           FROM legami l_1
        UNION
         SELECT d.m[1] AS m,
            d.m[2] AS m
           FROM (((check_nomi cn
             JOIN pg_namespace ns ON ((ns.nspname = cn.csch)))
             JOIN pg_proc p ON (((p.proname = cn.cfn) AND (p.pronamespace = ns.oid))))
             CROSS JOIN LATERAL dbops.fn_regexp_occorrenze((dbops.fn_corpo_funzione(p.oid) COLLATE "C"), '(\w+)\.(fn_check_\w+)\s*\('::text) d(m))
        ), checks AS MATERIALIZED (
         SELECT DISTINCT c_1.oid AS check_oid,
            cn.csch,
            cn.cfn,
            ((dbops.fn_corpo_funzione(c_1.oid) COLLATE "C") ~ '''valori'''::text) AS emette_valori,
            (dbops.fn_corpo_funzione(c_1.oid) COLLATE "C") AS csrc
           FROM ((check_nomi cn
             JOIN pg_namespace ns ON ((ns.nspname = cn.csch)))
             JOIN pg_proc c_1 ON (((c_1.proname = cn.cfn) AND (c_1.pronamespace = ns.oid))))
        ), deleghe_grezze AS MATERIALIZED (
         SELECT c_1.check_oid,
            x.dsch,
            x.dfn,
            x.resto
           FROM (checks c_1
             CROSS JOIN LATERAL ( SELECT m_1.m[1] AS dsch,
                    m_1.m[2] AS dfn,
                    m_1.m[3] AS resto
                   FROM dbops.fn_regexp_occorrenze(c_1.csrc, '(?:\|\||:=)\s*(\w+)\.(fn_check_\w+)\s*\(([^;]*)'::text) m_1(m)
                UNION ALL
                 SELECT m_1.m[1] AS m,
                    m_1.m[2] AS m,
                    m_1.m[3] AS m
                   FROM dbops.fn_regexp_occorrenze(c_1.csrc, 'jsonb_agg\s*\([^;]*?jsonb_array_elements\s*\(\s*(\w+)\.(fn_check_\w+)\s*\(([^;]*)'::text) m_1(m)) x)
        ), deleghe AS (
         SELECT DISTINCT g.check_oid,
            d.check_oid AS delegata_oid,
            g.resto
           FROM (deleghe_grezze g
             JOIN checks d ON (((d.csch = g.dsch) AND (d.cfn = g.dfn))))
          WHERE (d.check_oid <> g.check_oid)
        ), filtri AS (
         SELECT DISTINCT dl.check_oid,
            dl.delegata_oid,
            l_1.m[1] AS codice
           FROM ((deleghe dl
             CROSS JOIN LATERAL dbops.fn_regexp_occorrenze(dl.resto, '->>\s*''codice''\s*(?:=\s*''E_[A-Z0-9_]+''|IN\s*\([^)]*\))'::text) f(m))
             CROSS JOIN LATERAL dbops.fn_regexp_occorrenze(f.m[1], '''(E_[A-Z0-9_]+)'''::text) l_1(m))
        ), motivi AS (
         SELECT c_1.check_oid,
            (regexp_match(s.pz, '^''(E_[A-Z0-9_]+)'''::text))[1] AS codice,
            split_part(s.pz, ';'::text, 1) AS finestra
           FROM (checks c_1
             CROSS JOIN LATERAL unnest(regexp_split_to_array(c_1.csrc, '''codice''\s*,\s*'::text)) WITH ORDINALITY s(pz, k))
          WHERE (s.k > 1)
        ), motivi_propri AS (
         SELECT m_1.check_oid,
            m_1.codice,
            (count(*))::integer AS n_motivi,
                CASE
                    WHEN bool_and((m_1.finestra ~ '''campo''\s*,'::text)) THEN 'campo'::text
                    WHEN bool_and((m_1.finestra ~ '''(campo|parametro)''\s*,'::text)) THEN 'parametro'::text
                    ELSE NULL::text
                END AS motivo_chiave
           FROM motivi m_1
          WHERE (m_1.codice IS NOT NULL)
          GROUP BY m_1.check_oid, m_1.codice
        ), codici_rec(check_oid, codice, n_motivi, motivo_chiave) AS (
         SELECT mp.check_oid,
            mp.codice,
            mp.n_motivi,
            mp.motivo_chiave
           FROM motivi_propri mp
        UNION
         SELECT dl.check_oid,
            cr.codice,
            cr.n_motivi,
            cr.motivo_chiave
           FROM (deleghe dl
             JOIN codici_rec cr ON ((cr.check_oid = dl.delegata_oid)))
          WHERE ((NOT (EXISTS ( SELECT 1
                   FROM filtri f
                  WHERE ((f.check_oid = dl.check_oid) AND (f.delegata_oid = dl.delegata_oid))))) OR (EXISTS ( SELECT 1
                   FROM filtri f
                  WHERE ((f.check_oid = dl.check_oid) AND (f.delegata_oid = dl.delegata_oid) AND (f.codice = cr.codice)))))
        ), motivi_per_codice AS (
         SELECT cr.check_oid,
            cr.codice,
            (sum(cr.n_motivi))::integer AS n_motivi,
                CASE
                    WHEN bool_and((NOT (cr.motivo_chiave IS DISTINCT FROM 'campo'::text))) THEN 'campo'::text
                    WHEN bool_and((cr.motivo_chiave = ANY (ARRAY['campo'::text, 'parametro'::text]))) THEN 'parametro'::text
                    ELSE NULL::text
                END AS motivo_chiave
           FROM codici_rec cr
          GROUP BY cr.check_oid, cr.codice
        ), valori_rec(check_oid) AS (
         SELECT c_1.check_oid
           FROM checks c_1
          WHERE c_1.emette_valori
        UNION
         SELECT dl.check_oid
           FROM (deleghe dl
             JOIN valori_rec v ON ((v.check_oid = dl.delegata_oid)))
        )
 SELECT l.sch,
    l.fn,
    l.funzione,
    l.csch AS check_schema,
    l.cfn AS check_funzione,
    (EXISTS ( SELECT 1
           FROM valori_rec v
          WHERE (v.check_oid = c.check_oid))) AS check_emette_valori,
    m.codice,
    m.n_motivi,
    m.motivo_chiave
   FROM ((legami l
     JOIN checks c ON (((c.csch = l.csch) AND (c.cfn = l.cfn))))
     LEFT JOIN motivi_per_codice m ON ((m.check_oid = c.check_oid)));
```

</div>


---
{% include-markdown "signature-core.md" %}
