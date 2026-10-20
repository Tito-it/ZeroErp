{% include-markdown "it/dbzero/vendite/manual/fn_documento_lineage_sintesi.md" %}
# ⚙️ Funzione `fn_documento_lineage_sintesi`

```sql
CREATE FUNCTION fn_documento_lineage_sintesi(p_tipo_ids bigint[], p_uids text[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_lineage_sintesi(p_tipo_ids bigint[], p_uids text[])
 RETURNS TABLE(tipo_id bigint, uid text, codice character varying, stato_codice_interno character varying, stato_codice character varying, stato_descrizione character varying, fase character varying, is_abortito boolean, pratica_id bigint, pratica_numero text, n_pratiche bigint, frontiera_tipo_id bigint, frontiera_uid text, frontiera_codice character varying, frontiera_stato_codice_interno character varying, frontiera_fase character varying, n_discendenti_diretti bigint, n_discendenti_attivi bigint, is_transitato boolean, n_sorgenti bigint, root_tipo_id bigint, root_uid text, root_codice character varying, natura_doc_codice_interno character varying, natura_doc_descrizione character varying, frontiera_natura_doc_codice_interno character varying, tipo_codice_interno character varying, frontiera_tipo_codice_interno character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la SINTESI della lineage — pratica, frontiera, discendenti, sorgenti
--   e radice — per i soli documenti chiesti (la pagina di una lista, il drawer
--   di un documento). E' la regola che stava in vw_documento_lineage, costruita
--   UN LIVELLO ALLA VOLTA dalle funzioni per chiave invece che dall'intero
--   grafo. Brief: brief-db-lineage-seminata-per-chiave, giro A.
-- La regola e' quella della vista, punto per punto:
--   * cammino in AVANTI dai nodi del seme sui soli archi non di ritorno
--     (is_ramo_inverso = false), per PERCORSI con la guardia dei cicli sul
--     percorso (assente al primo passo), al massimo 10 livelli;
--   * frontiera = fra il nodo stesso (livello 0) e i nodi raggiunti, il primo
--     per: attivo (fase <> CHIUSO e non abortito) prima, livello piu' alto,
--     pipeline_rank piu' alto, poi tipo e uid;
--   * discendenti diretti = nodi distinti al livello 1, e quanti attivi;
--   * sorgenti = archi ENTRANTI non di ritorno (ogni arco conta), radice = il
--     primo per ruolo ROOT, rango_origine, from_uid;
--   * pratica = pratiche.fn_pratica_del_documento (la prima per id, e quante).
-- ⭐ E' la sede UNICA della regola dal giro B (rev 20261011-96/-98): la vista
--   vw_documento_lineage, che ne era la seconda copia, si ritira; liste,
--   export e drawer leggono le colonne del grafo da qui.
-- Un nodo che chi legge non vede non esce (come nella vista, che parte dai
--   nodi); i suoi vicini invisibili escono con le colonne del nodo NULL.
DECLARE
    v_stati   jsonb;                 -- [{o_t, o_u, t, u, v:[...]}] i percorsi aperti
    v_walk    jsonb := '[]'::jsonb;  -- [{o_t, o_u, d_t, d_u, l}]
    v_inc     jsonb;                 -- gli archi entranti nei nodi del seme
    v_livello integer := 0;          -- contatore dei livelli, nessuna colonna dietro
    v_tipi    bigint[];              -- config.sorgenti.id, ma `%TYPE[]` non esiste
    v_uids    text[];                -- chiavi polimorfe dei nodi, rese a text
    v_archi   jsonb;                 -- gli archi del livello
    v_nuovi   jsonb;                 -- i passi nuovi del livello
BEGIN
    IF p_tipo_ids IS NULL OR p_uids IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_documento_lineage_sintesi', 'E_ERRORE_PARAMETRI',
            jsonb_build_object('detail', 'seme obbligatorio: p_tipo_ids e p_uids'),
            NULL::uuid,
            'seme non valido (NULL): la sintesi si chiede per le chiavi dei documenti');
    END IF;

    -- I percorsi partono dai nodi del seme (distinti).
    SELECT coalesce(jsonb_agg(jsonb_build_object(
               'o_t', q.t, 'o_u', q.u, 't', q.t, 'u', q.u,
               'v', jsonb_build_array(q.t::text || ':' || q.u))), '[]'::jsonb)
      INTO v_stati
      FROM (SELECT DISTINCT s.t, s.u
              FROM unnest(p_tipo_ids, p_uids) AS s(t, u)
             WHERE s.t IS NOT NULL AND s.u IS NOT NULL) q;

    WHILE v_livello < 10 AND jsonb_array_length(v_stati) > 0 LOOP
        v_livello := v_livello + 1;

        SELECT array_agg(q.t), array_agg(q.u)
          INTO v_tipi, v_uids
          FROM (SELECT DISTINCT (s->>'t')::bigint AS t, s->>'u' AS u
                  FROM jsonb_array_elements(v_stati) s) q;

        -- ⭐ rev 2026-10-13 (D-15 di Tid): un arco col LEGAME RITIRATO non e'
        --    una destinazione e non e' una sorgente (vendite.fn_documento_
        --    lineage_legami). Il filtro sta qui, alla lettura degli archi del
        --    livello, quindi vale per tutto cio' che ne discende: cammino,
        --    frontiera, discendenti, transitato, sorgenti e radice. Un arco non
        --    censito (NULL) resta, come prima. Il pannello «Passaggi»
        --    (fn_documento_lineage) lo mostra ancora, come storia.
        WITH a AS MATERIALIZED (
            SELECT * FROM vendite.fn_documento_lineage_archi(v_tipi, v_uids)
        ), ag AS (
            -- UNA SELECT: le cinque aggregazioni vedono le righe nello stesso ordine.
            SELECT array_agg(a.arco) AS x, array_agg(a.from_tipo_id) AS ft,
                   array_agg(a.from_uid) AS fu, array_agg(a.to_tipo_id) AS tt,
                   array_agg(a.to_uid) AS tu
              FROM a
        ), lg AS MATERIALIZED (
            SELECT g.* FROM ag, vendite.fn_documento_lineage_legami(ag.x, ag.ft, ag.fu, ag.tt, ag.tu) g
        )
        SELECT coalesce(jsonb_agg(jsonb_build_object(
                   'from_t', a.from_tipo_id, 'from_u', a.from_uid,
                   'to_t', a.to_tipo_id, 'to_u', a.to_uid,
                   'ruolo', a.ruolo, 'inv', a.is_ramo_inverso, 'rango', a.rango_origine)), '[]'::jsonb)
          INTO v_archi
          FROM a
          LEFT JOIN lg ON lg.arco = a.arco
                      AND lg.from_tipo_id = a.from_tipo_id AND lg.from_uid = a.from_uid
                      AND lg.to_tipo_id   = a.to_tipo_id   AND lg.to_uid   = a.to_uid
         WHERE lg.is_legame_ritirato IS NOT TRUE;

        -- Al primo livello il seme e' esattamente l'insieme dei nodi chiesti:
        -- gli archi ENTRANTI non di ritorno sono le loro sorgenti.
        IF v_livello = 1 THEN
            SELECT coalesce(jsonb_agg(e), '[]'::jsonb)
              INTO v_inc
              FROM jsonb_array_elements(v_archi) e
             WHERE NOT (e->>'inv')::boolean
               AND EXISTS (SELECT 1 FROM unnest(v_tipi, v_uids) AS s(t, u)
                            WHERE s.t = (e->>'to_t')::bigint AND s.u = e->>'to_u');
        END IF;

        WITH stati AS (
            SELECT (s->>'o_t')::bigint AS o_t, s->>'o_u' AS o_u,
                   (s->>'t')::bigint AS t, s->>'u' AS u, s->'v' AS v
              FROM jsonb_array_elements(v_stati) s
        ), passi AS (
            SELECT st.o_t, st.o_u, st.v,
                   (e->>'to_t')::bigint AS d_t, e->>'to_u' AS d_u
              FROM stati st
              JOIN jsonb_array_elements(v_archi) e
                ON (e->>'from_t')::bigint = st.t AND e->>'from_u' = st.u
             WHERE NOT (e->>'inv')::boolean
        )
        SELECT coalesce(jsonb_agg(jsonb_build_object(
                   'o_t', p.o_t, 'o_u', p.o_u, 'd_t', p.d_t, 'd_u', p.d_u, 'v', p.v)), '[]'::jsonb)
          INTO v_nuovi
          FROM passi p
         WHERE v_livello = 1
            OR NOT (to_jsonb(p.d_t::text || ':' || p.d_u) <@ p.v);

        v_walk := v_walk || (SELECT coalesce(jsonb_agg(jsonb_build_object(
                                 'o_t', n->'o_t', 'o_u', n->'o_u', 'd_t', n->'d_t', 'd_u', n->'d_u',
                                 'l', v_livello)), '[]'::jsonb)
                               FROM jsonb_array_elements(v_nuovi) n);
        SELECT coalesce(jsonb_agg(jsonb_build_object(
                   'o_t', n->'o_t', 'o_u', n->'o_u', 't', n->'d_t', 'u', n->'d_u',
                   'v', (n->'v') || to_jsonb((n->>'d_t') || ':' || (n->>'d_u')))), '[]'::jsonb)
          INTO v_stati
          FROM jsonb_array_elements(v_nuovi) n;
    END LOOP;

    -- La decorazione, una volta: i nodi del seme, quelli raggiunti e le
    -- sorgenti.
    SELECT array_agg(k.t), array_agg(k.u)
      INTO v_tipi, v_uids
      FROM (SELECT s.t, s.u FROM unnest(p_tipo_ids, p_uids) AS s(t, u)
             WHERE s.t IS NOT NULL AND s.u IS NOT NULL
            UNION
            SELECT (w->>'d_t')::bigint, w->>'d_u' FROM jsonb_array_elements(v_walk) w
            UNION
            SELECT (e->>'from_t')::bigint, e->>'from_u' FROM jsonb_array_elements(coalesce(v_inc, '[]'::jsonb)) e) k;

    RETURN QUERY
    WITH nodi AS MATERIALIZED (
        SELECT * FROM vendite.fn_documento_lineage_nodi(v_tipi, v_uids)
    ), seme AS (
        SELECT DISTINCT s.t, s.u FROM unnest(p_tipo_ids, p_uids) AS s(t, u)
    ), walk AS (
        SELECT (w->>'o_t')::bigint AS o_tipo, w->>'o_u' AS o_uid,
               (w->>'d_t')::bigint AS d_tipo, w->>'d_u' AS d_uid,
               (w->>'l')::integer AS lvl
          FROM jsonb_array_elements(v_walk) w
    ), cand AS (
        -- Il nodo stesso (livello 0) e ogni nodo raggiunto. Stato e fase del
        -- raggiunto vengono dal nodo (la vista li prende dalla decorazione
        -- dell'arco, che e' la stessa riga dei nodi: NULL se non si vede).
        SELECT n.tipo_id AS o_tipo, n.uid AS o_uid, n.tipo_id AS d_tipo, n.uid AS d_uid, 0 AS lvl
          FROM nodi n JOIN seme s ON s.t = n.tipo_id AND s.u = n.uid
        UNION ALL
        SELECT w.o_tipo, w.o_uid, w.d_tipo, w.d_uid, w.lvl FROM walk w
    ), frontiera AS (
        SELECT c.o_tipo, c.o_uid, c.d_tipo, c.d_uid,
               nd.codice AS d_codice, nd.stato_codice_interno AS d_stato, nd.fase AS d_fase,
               nd.natura_doc_codice_interno AS d_natura, nd.tipo_codice_interno AS d_tipo_codice_interno,
               row_number() OVER (PARTITION BY c.o_tipo, c.o_uid ORDER BY
                   CASE WHEN nd.fase::text <> 'CHIUSO' AND NOT coalesce(nd.is_abortito, false)
                        THEN 0 ELSE 1 END,
                   c.lvl DESC, coalesce(nd.pipeline_rank::integer, 0) DESC, c.d_tipo, c.d_uid) AS rn
          FROM cand c
          LEFT JOIN nodi nd ON nd.tipo_id = c.d_tipo AND nd.uid = c.d_uid
    ), disc AS (
        SELECT w.o_tipo, w.o_uid,
               count(DISTINCT w.d_tipo::text || ':' || w.d_uid) AS n_diretti,
               count(DISTINCT w.d_tipo::text || ':' || w.d_uid)
                   FILTER (WHERE nd.fase::text <> 'CHIUSO' AND NOT coalesce(nd.is_abortito, false)) AS n_attivi
          FROM walk w
          LEFT JOIN nodi nd ON nd.tipo_id = w.d_tipo AND nd.uid = w.d_uid
         WHERE w.lvl = 1
         GROUP BY w.o_tipo, w.o_uid
    ), inc AS (
        SELECT (e->>'to_t')::bigint AS tipo, e->>'to_u' AS uid,
               count(*) AS n_sorgenti,
               (array_agg((e->>'from_t')::bigint ORDER BY (e->>'ruolo') = 'ROOT' DESC NULLS LAST,
                           (e->>'rango')::smallint, e->>'from_u'))[1] AS root_tipo,
               (array_agg(e->>'from_u' ORDER BY (e->>'ruolo') = 'ROOT' DESC NULLS LAST,
                           (e->>'rango')::smallint, e->>'from_u'))[1] AS root_uid,
               (array_agg(nf.codice ORDER BY (e->>'ruolo') = 'ROOT' DESC NULLS LAST,
                           (e->>'rango')::smallint, e->>'from_u'))[1] AS root_codice
          FROM jsonb_array_elements(coalesce(v_inc, '[]'::jsonb)) e
          LEFT JOIN nodi nf ON nf.tipo_id = (e->>'from_t')::bigint AND nf.uid = e->>'from_u'
         GROUP BY 1, 2
    ), prat AS (
        -- La pratica del documento: una sede sola, pratiche.fn_pratica_del_documento
        -- (rev 20261011-96), la stessa che leggono le viste di lista.
        SELECT s.t AS tipo, s.u AS uid, pd.n_pratiche, pd.pratica_id, pd.pratica_numero
          FROM seme s
          CROSS JOIN LATERAL pratiche.fn_pratica_del_documento(s.t, s.u) pd
    )
    SELECT n.tipo_id, n.uid, n.codice::varchar,
           n.stato_codice_interno::varchar, n.stato_codice::varchar, n.stato_descrizione::varchar,
           n.fase::varchar, n.is_abortito,
           pr.pratica_id, pr.pratica_numero::text, coalesce(pr.n_pratiche, 0::bigint),
           fr.d_tipo, fr.d_uid, fr.d_codice::varchar, fr.d_stato::varchar, fr.d_fase::varchar,
           coalesce(dc.n_diretti, 0::bigint), coalesce(dc.n_attivi, 0::bigint),
           coalesce(dc.n_diretti, 0::bigint) > 0,
           coalesce(ic.n_sorgenti, 0::bigint), ic.root_tipo, ic.root_uid, ic.root_codice::varchar,
           n.natura_doc_codice_interno, n.natura_doc_descrizione,
           fr.d_natura, n.tipo_codice_interno, fr.d_tipo_codice_interno
      FROM nodi n
      JOIN seme s        ON s.t = n.tipo_id AND s.u = n.uid
      LEFT JOIN prat pr  ON pr.tipo = n.tipo_id AND pr.uid = n.uid
      LEFT JOIN frontiera fr ON fr.o_tipo = n.tipo_id AND fr.o_uid = n.uid AND fr.rn = 1
      LEFT JOIN disc dc  ON dc.o_tipo = n.tipo_id AND dc.o_uid = n.uid
      LEFT JOIN inc ic   ON ic.tipo = n.tipo_id AND ic.uid = n.uid;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_lineage_sintesi(p_tipo_ids bigint[], p_uids text[])
IS '⭐ rev 2026-10-13 (20261013-71, D-15 di Tid): un arco col LEGAME RITIRATO (vendite.fn_documento_lineage_legami) non e'' una destinazione ne'' una sorgente: si scarta alla lettura degli archi di ogni livello, quindi non conta per cammino, frontiera, discendenti, transitato, sorgenti e radice. Un arco non censito (NULL) resta. Il pannello «Passaggi» lo mostra ancora, come storia. La SINTESI della lineage — pratica, frontiera, discendenti diretti e attivi, sorgenti e radice, natura — per i soli documenti del seme (la pagina di una lista, il drawer di un documento), con le colonne e l''ordine che erano di vw_documento_lineage. Seme = chiave del nodo (tipo_id, uid::text) in due array paralleli, OBBLIGATORIO (NULL solleva E_ERRORE_PARAMETRI). Costruita un livello alla volta da vendite.fn_documento_lineage_archi e decorata una volta da vendite.fn_documento_lineage_nodi: il costo segue il seme, non il grafo. Cammino in avanti senza rami di ritorno, per percorsi, 10 livelli; frontiera = attivo, poi livello, poi pipeline_rank; sorgenti dagli archi entranti, radice per ROOT, rango, uid; pratica da pratiche.fn_pratica_del_documento. Sede UNICA della regola: la vista vw_documento_lineage e'' ritirata (20261011-98). STABLE, INVOKER: la RLS resta di chi legge.';
```

</div>

---
{% include-markdown "signature-core.md" %}
