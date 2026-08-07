{% include-markdown "it/dbzero/vendite/manual/fn_documento_lineage.md" %}
# ⚙️ Funzione `fn_documento_lineage`

```sql
CREATE FUNCTION fn_documento_lineage(p_tipo_id bigint, p_uid text, p_direzione text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_lineage(p_tipo_id bigint, p_uid text, p_direzione text DEFAULT 'avanti'::text)
 RETURNS TABLE(livello integer, ordine integer, arco text, ruolo character varying, from_tipo_id bigint, from_uid text, from_codice text, to_tipo_id bigint, to_uid text, to_codice text, to_stato_codice_interno character varying, to_fase character varying, to_is_abortito boolean, is_ramo_inverso boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Guard parametri (AGENTS: ID numerici NOT NULL e > 0).
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

    RETURN QUERY
    WITH RECURSIVE trav AS (
        -- Livello 1: archi adiacenti al nodo di partenza nella direzione scelta.
        SELECT a.from_tipo_id, a.from_uid, a.from_codice,
               a.to_tipo_id, a.to_uid, a.to_codice,
               a.to_stato_codice_interno, a.to_fase, a.to_is_abortito,
               a.ruolo, a.arco,
               1 AS livello,
               CASE WHEN p_direzione = 'avanti' THEN a.to_tipo_id ELSE a.from_tipo_id END AS cur_tipo,
               CASE WHEN p_direzione = 'avanti' THEN a.to_uid    ELSE a.from_uid    END AS cur_uid,
               ARRAY[
                   p_tipo_id::text || ':' || p_uid,
                   (CASE WHEN p_direzione = 'avanti' THEN a.to_tipo_id ELSE a.from_tipo_id END)::text
                       || ':' ||
                   (CASE WHEN p_direzione = 'avanti' THEN a.to_uid ELSE a.from_uid END)
               ] AS visited
          FROM vendite.vw_documento_lineage_archi a
         WHERE (p_direzione = 'avanti'   AND a.from_tipo_id = p_tipo_id AND a.from_uid = p_uid)
            OR (p_direzione = 'indietro' AND a.to_tipo_id   = p_tipo_id AND a.to_uid   = p_uid)
        UNION ALL
        -- Espansione: dal nodo corrente segui gli archi nella stessa direzione.
        SELECT a.from_tipo_id, a.from_uid, a.from_codice,
               a.to_tipo_id, a.to_uid, a.to_codice,
               a.to_stato_codice_interno, a.to_fase, a.to_is_abortito,
               a.ruolo, a.arco,
               t.livello + 1,
               CASE WHEN p_direzione = 'avanti' THEN a.to_tipo_id ELSE a.from_tipo_id END,
               CASE WHEN p_direzione = 'avanti' THEN a.to_uid    ELSE a.from_uid    END,
               t.visited || (
                   (CASE WHEN p_direzione = 'avanti' THEN a.to_tipo_id ELSE a.from_tipo_id END)::text
                       || ':' ||
                   (CASE WHEN p_direzione = 'avanti' THEN a.to_uid ELSE a.from_uid END)
               )
          FROM trav t
          JOIN vendite.vw_documento_lineage_archi a
            ON (p_direzione = 'avanti'   AND a.from_tipo_id = t.cur_tipo AND a.from_uid = t.cur_uid)
            OR (p_direzione = 'indietro' AND a.to_tipo_id   = t.cur_tipo AND a.to_uid   = t.cur_uid)
         WHERE t.livello < 10
           AND NOT (
               (CASE WHEN p_direzione = 'avanti' THEN a.to_tipo_id ELSE a.from_tipo_id END)::text
                   || ':' ||
               (CASE WHEN p_direzione = 'avanti' THEN a.to_uid ELSE a.from_uid END)
           ) = ANY (t.visited)
    )
    -- Cast espliciti al tipo dichiarato dalla RETURNS TABLE: la union di
    -- vw_documento_lineage_nodi.codice risolve a varchar, quindi from_codice/
    -- to_codice arrivano varchar mentre la firma li vuole text (PG e' rigido
    -- sul match esatto, SQLSTATE 42804).
    SELECT t.livello::integer,
           (ROW_NUMBER() OVER (ORDER BY t.livello,
                                        t.from_tipo_id, t.from_uid,
                                        t.to_tipo_id, t.to_uid))::integer AS ordine,
           t.arco::text, t.ruolo::varchar,
           t.from_tipo_id, t.from_uid::text, t.from_codice::text,
           t.to_tipo_id, t.to_uid::text, t.to_codice::text,
           t.to_stato_codice_interno::varchar, t.to_fase::varchar, t.to_is_abortito,
           (t.arco = 'R') AS is_ramo_inverso
      FROM trav t
     ORDER BY ordine;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_lineage(p_tipo_id bigint, p_uid text, p_direzione text)
IS 'Lineage documenti vendite (Step 4): traversal ricorsivo del grafo genealogia (vw_documento_lineage_archi) dal nodo (tipo,uid) in direzione avanti|indietro, per il pannello Passaggi. Ritorna gli archi con livello/ordine + stato/fase target; is_ramo_inverso marca l''arco R (DDT->Reso). SECURITY INVOKER (RLS emittente del chiamante).';
```

---
{% include-markdown "signature-core.md" %}
