{% include-markdown "it/dbzero/vendite/manual/fn_documento_lineage.md" %}
# ⚙️ Funzione `fn_documento_lineage`

```sql
CREATE FUNCTION fn_documento_lineage(p_tipo_id bigint, p_uid text, p_direzione text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_lineage(p_tipo_id bigint, p_uid text, p_direzione text DEFAULT 'avanti'::text)
 RETURNS TABLE(livello integer, ordine integer, arco text, ruolo character varying, from_tipo_id bigint, from_uid text, from_codice text, to_tipo_id bigint, to_uid text, to_codice text, to_stato_codice_interno character varying, to_fase character varying, to_is_abortito boolean, is_ramo_inverso boolean, from_natura_doc_codice_interno character varying, to_natura_doc_codice_interno character varying, is_legame_ritirato boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la catena di UN documento per il pannello «Passaggi», risalendo il
--   grafo UN LIVELLO ALLA VOLTA dalle funzioni per chiave (rev 2026-10-11,
--   brief-db-lineage-seminata-per-chiave, giro A). Prima leggeva la vista degli
--   archi, cioe' l'intero grafo decorato di tutti i documenti del sistema.
-- Lo stato del traversal e' un insieme di PERCORSI: {t, u} il nodo corrente,
--   {v} i nodi gia' visitati SU QUEL PERCORSO. E' la semantica di prima,
--   identica: un nodo raggiunto per due strade compare due volte, ciascuna col
--   suo livello; la guardia dei cicli e' sul percorso, non globale.
-- A ogni livello: UNA chiamata a fn_documento_lineage_archi col seme = i nodi
--   correnti (distinti) di tutti i percorsi; poi ogni percorso prende gli archi
--   che partono dal suo nodo (avanti: from; indietro: to). Al massimo 10 livelli
--   (prima: livello < 10 nel termine ricorsivo).
-- ⚠️ Al livello 1 il controllo dei visitati non c'e', come prima: la ricorsione
--   lo applicava solo dal livello 2 (un cappio dal nodo di partenza non esiste
--   per costruzione — N esclude rr = fr — ma l'equivalenza non lo da' per scontato).
-- La decorazione (codice, stato, fase, natura) si legge UNA volta alla fine, da
--   fn_documento_lineage_nodi, per i soli nodi toccati: e' la stessa LEFT JOIN
--   della vista degli archi, quindi un nodo che chi legge non vede esce con le
--   colonne NULL, come prima.
DECLARE
    v_avanti  boolean := (p_direzione = 'avanti');
    v_stati   jsonb;                 -- [{t, u, v:[...]}] i percorsi aperti
    v_archi   jsonb := '[]'::jsonb;  -- [{l, from_t, from_u, to_t, to_u, arco, ruolo, inv}]
    v_livello integer := 0;
    v_tipi    bigint[];
    v_uids    text[];
    v_nuovi   jsonb;
BEGIN
    IF p_tipo_id IS NULL OR p_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_documento_lineage', 'E_ERRORE_PARAMETRI',
            jsonb_build_object('detail', 'p_tipo_id obbligatorio e > 0',
                               'p_tipo_id', p_tipo_id),
            NULL::uuid,
            concat('p_tipo_id non valido: ', COALESCE(p_tipo_id::text, 'NULL')));
    END IF;

    IF p_uid IS NULL OR btrim(p_uid) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_documento_lineage', 'E_ERRORE_PARAMETRI',
            jsonb_build_object('detail', 'p_uid obbligatorio (chiave nodo)'),
            NULL::uuid,
            'p_uid non valido (NULL o vuoto)');
    END IF;

    IF p_direzione IS NULL OR p_direzione NOT IN ('avanti', 'indietro') THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_documento_lineage', 'E_ERRORE_PARAMETRI',
            jsonb_build_object('detail', 'p_direzione deve essere avanti|indietro',
                               'p_direzione', p_direzione),
            NULL::uuid,
            concat('p_direzione non valido: ', COALESCE(p_direzione, 'NULL')));
    END IF;

    v_stati := jsonb_build_array(jsonb_build_object(
                   't', p_tipo_id, 'u', p_uid,
                   'v', jsonb_build_array(p_tipo_id::text || ':' || p_uid)));

    WHILE v_livello < 10 AND jsonb_array_length(v_stati) > 0 LOOP
        v_livello := v_livello + 1;

        -- Il seme del livello: i nodi correnti, distinti.
        SELECT array_agg(q.t), array_agg(q.u)
          INTO v_tipi, v_uids
          FROM (SELECT DISTINCT (s->>'t')::bigint AS t, s->>'u' AS u
                  FROM jsonb_array_elements(v_stati) s) q;

        -- Ogni percorso prende gli archi che partono dal suo nodo; il nodo
        -- successivo non deve stare fra i visitati del percorso (dal livello 2).
        WITH stati AS (
            SELECT (s->>'t')::bigint AS t, s->>'u' AS u, s->'v' AS v
              FROM jsonb_array_elements(v_stati) s
        ), passi AS (
            SELECT a.*, st.v,
                   CASE WHEN v_avanti THEN a.to_tipo_id ELSE a.from_tipo_id END AS nt,
                   CASE WHEN v_avanti THEN a.to_uid     ELSE a.from_uid     END AS nu
              FROM stati st
              JOIN vendite.fn_documento_lineage_archi(v_tipi, v_uids) a
                ON (    v_avanti AND a.from_tipo_id = st.t AND a.from_uid = st.u)
                OR (NOT v_avanti AND a.to_tipo_id   = st.t AND a.to_uid   = st.u)
        )
        SELECT coalesce(jsonb_agg(jsonb_build_object(
                   'l', v_livello,
                   'from_t', p.from_tipo_id, 'from_u', p.from_uid,
                   'to_t', p.to_tipo_id, 'to_u', p.to_uid,
                   'arco', p.arco, 'ruolo', p.ruolo, 'inv', p.is_ramo_inverso,
                   'nt', p.nt, 'nu', p.nu, 'v', p.v)), '[]'::jsonb)
          INTO v_nuovi
          FROM passi p
         WHERE v_livello = 1
            OR NOT (to_jsonb(p.nt::text || ':' || p.nu) <@ p.v);

        v_archi := v_archi || v_nuovi;
        SELECT coalesce(jsonb_agg(jsonb_build_object(
                   't', n->'nt', 'u', n->'nu',
                   'v', (n->'v') || to_jsonb((n->>'nt') || ':' || (n->>'nu')))), '[]'::jsonb)
          INTO v_stati
          FROM jsonb_array_elements(v_nuovi) n;
    END LOOP;

    -- La decorazione, una volta: i nodi toccati dagli archi trovati.
    SELECT array_agg(k.t), array_agg(k.u)
      INTO v_tipi, v_uids
      FROM (SELECT (e->>'from_t')::bigint AS t, e->>'from_u' AS u FROM jsonb_array_elements(v_archi) e
            UNION
            SELECT (e->>'to_t')::bigint, e->>'to_u' FROM jsonb_array_elements(v_archi) e) k;

    RETURN QUERY
    WITH t AS (
        SELECT (e->>'l')::integer        AS livello,
               e->>'arco'                AS arco,
               e->>'ruolo'               AS ruolo,
               (e->>'from_t')::bigint    AS from_tipo_id,
               e->>'from_u'              AS from_uid,
               (e->>'to_t')::bigint      AS to_tipo_id,
               e->>'to_u'                AS to_uid,
               (e->>'inv')::boolean      AS is_ramo_inverso
          FROM jsonb_array_elements(v_archi) e
    ), nodi AS MATERIALIZED (
        SELECT n.tipo_id, n.uid, n.codice, n.stato_codice_interno, n.fase,
               n.is_abortito, n.natura_doc_codice_interno
          FROM vendite.fn_documento_lineage_nodi(v_tipi, v_uids) n
    ), ag AS (
        -- Gli archi come array paralleli: UNA SELECT, quindi le cinque
        -- aggregazioni vedono le righe nello stesso ordine.
        SELECT array_agg(t.arco) AS a, array_agg(t.from_tipo_id) AS ft,
               array_agg(t.from_uid) AS fu, array_agg(t.to_tipo_id) AS tt,
               array_agg(t.to_uid) AS tu
          FROM t
    ), legami AS MATERIALIZED (
        -- ⭐ rev 2026-10-13 (R-17): il legame, decorato una volta come i nodi.
        SELECT g.arco, g.from_tipo_id, g.from_uid, g.to_tipo_id, g.to_uid,
               g.is_legame_ritirato
          FROM ag, vendite.fn_documento_lineage_legami(ag.a, ag.ft, ag.fu, ag.tt, ag.tu) g
    )
    SELECT t.livello::integer,
           (ROW_NUMBER() OVER (ORDER BY t.livello,
                                        t.from_tipo_id, t.from_uid,
                                        t.to_tipo_id, t.to_uid))::integer AS ordine,
           t.arco::text, t.ruolo::varchar,
           t.from_tipo_id, t.from_uid::text, nf.codice::text,
           t.to_tipo_id, t.to_uid::text, nt.codice::text,
           nt.stato_codice_interno::varchar, nt.fase::varchar, nt.is_abortito,
           t.is_ramo_inverso,
           nf.natura_doc_codice_interno::varchar, nt.natura_doc_codice_interno::varchar,
           lg.is_legame_ritirato
      FROM t
      LEFT JOIN nodi nf ON nf.tipo_id = t.from_tipo_id AND nf.uid = t.from_uid
      LEFT JOIN nodi nt ON nt.tipo_id = t.to_tipo_id   AND nt.uid = t.to_uid
      LEFT JOIN legami lg ON lg.arco = t.arco
                         AND lg.from_tipo_id = t.from_tipo_id AND lg.from_uid = t.from_uid
                         AND lg.to_tipo_id   = t.to_tipo_id   AND lg.to_uid   = t.to_uid
     ORDER BY ordine;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_lineage(p_tipo_id bigint, p_uid text, p_direzione text)
IS 'La catena di un documento per il pannello «Passaggi»: dal nodo di partenza (p_tipo_id = config.sorgenti.id; p_uid = la chiave del documento in testo secondo il key_selector, l''uid per preventivo e offerta, l''id per gli altri) gli archi attraversati nella direzione p_direzione: ''avanti'' (il default, verso le destinazioni) o ''indietro'' (verso le sorgenti). Si risale un livello alla volta: a ogni livello una chiamata a vendite.fn_documento_lineage_archi col seme dei nodi correnti di tutti i percorsi aperti; alla fine, una volta, la decorazione dei soli nodi toccati da vendite.fn_documento_lineage_nodi (codice, stato, fase, abortito, natura fiscale) e il legame di ogni arco da vendite.fn_documento_lineage_legami. Il costo segue la catena, non il grafo intero. Il traversal e'' un insieme di percorsi: un nodo raggiunto per due strade compare due volte, ciascuna col suo livello; la guardia dei cicli e'' sul percorso, dal livello 2; al massimo 10 livelli. livello e'' la distanza dal nodo di partenza (1 = adiacente); ordine una sequenza stabile per livello e chiavi degli estremi. is_ramo_inverso arriva dalla grammatica degli archi e non si ricalcola qui. is_legame_ritirato e'' dell''arco e vale nei due versi: true se il legame e'' ritirato con i due nodi vivi, NULL su un arco che il decoratore non censisce. Un nodo che chi legge non vede esce con la decorazione NULL, e l''arco resta. Parametri non validi (tipo assente o non positivo, chiave assente o vuota, direzione diversa da avanti e indietro): E_ERRORE_PARAMETRI. STABLE, SECURITY INVOKER: la RLS di chi chiama vale a ogni passo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
