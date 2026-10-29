{% include-markdown "it/dbzero/script/manual/fn_check_versione_listino_eliminabile.md" %}
# ⚙️ Funzione `fn_check_versione_listino_eliminabile`

```sql
CREATE FUNCTION fn_check_versione_listino_eliminabile(p_versione_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_versione_listino_eliminabile(p_versione_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_versione vendite.listini_versioni%ROWTYPE;
    v_stato    config.stati_doc_listino_versioni.codice_interno%TYPE;
    -- Righe e componenti della versione: il verbo li cancella
    -- con lei, non trattengono.
    v_proprie  regclass[] := ARRAY['vendite.listini_righe'::regclass,
                                   'vendite.listini_righe_componenti'::regclass];
    -- Le tabelle che trattengono, `schema.tabella`.
    v_dove     text[];
BEGIN
    -- =========================================================
    -- Scopo: dire perche' una versione di listino NON si
    --   elimina. '[]' = si elimina. Non solleva: sollevare e'
    --   del guard per stato e del verbo, che la chiamano, come
    --   la superficie della lista (linee-guida-sql §12.5.2).
    --   Vedi l'intestazione del changeSet 20261028-36.
    -- =========================================================
    SELECT lv.* INTO v_versione
      FROM vendite.listini_versioni lv
     WHERE lv.id = p_versione_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_array();
    END IF;

    SELECT s.codice_interno INTO v_stato
      FROM config.stati_doc_listino_versioni s
     WHERE s.id = v_versione.stato_doc_listino_versione_id;

    -- 1. Fuori dalla bozza: e' stata visibile ai prezzi.
    IF v_stato IS DISTINCT FROM 'BOZZA' THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_LISTINO_VERSIONE_NON_ELIMINABILE',
            'reason',     'VERSIONE_NON_IN_BOZZA',
            'reason_key', 'vendite.listini.azione_reason.versione_non_in_bozza',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione.id,
                                             'listino_id', v_versione.listino_id,
                                             'stato', v_stato),
            'valori',     jsonb_build_array(v_versione.codice_versione,
                                            COALESCE(v_stato, 'NULL'))));
    END IF;

    -- 2. Un documento la tiene: la versione, o una sua riga o
    --    un suo componente.
    SELECT array_agg(DISTINCT d.tabella ORDER BY d.tabella) INTO v_dove
      FROM (
        SELECT unnest(script.fn_tabelle_che_trattengono(
                   'vendite.listini_versioni'::regclass,
                   ARRAY[v_versione.id]::bigint[], v_proprie))
        UNION ALL
        SELECT unnest(script.fn_tabelle_che_trattengono(
                   'vendite.listini_righe'::regclass,
                   ARRAY(SELECT r.id FROM vendite.listini_righe r
                          WHERE r.listino_versione_id = v_versione.id)::bigint[],
                   v_proprie))
        UNION ALL
        SELECT unnest(script.fn_tabelle_che_trattengono(
                   'vendite.listini_righe_componenti'::regclass,
                   ARRAY(SELECT c.id FROM vendite.listini_righe_componenti c
                          WHERE c.listino_versione_id = v_versione.id)::bigint[],
                   v_proprie))
      ) AS d(tabella);

    IF cardinality(v_dove) > 0 THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_LISTINO_VERSIONE_CITATA',
            'reason',     'VERSIONE_CITATA',
            'reason_key', 'vendite.listini.azione_reason.versione_citata',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione.id,
                                             'listino_id', v_versione.listino_id,
                                             'dove', to_jsonb(v_dove)),
            'valori',     jsonb_build_array(v_versione.codice_versione,
                                            array_to_string(v_dove, ', '))));
    END IF;

    RETURN jsonb_build_array();
END;
$function$

COMMENT ON FUNCTION script.fn_check_versione_listino_eliminabile(p_versione_id bigint)
IS 'Perche'' una versione di listino NON si elimina: jsonb array di motivi (codice, reason, reason_key, dettaglio, valori), il primo e'' quello che si solleva; ''[]'' = si elimina. Motivi: 1. E_LISTINO_VERSIONE_NON_ELIMINABILE (VERSIONE_NON_IN_BOZZA: ATTIVA o CHIUSA, e'' stata visibile ai prezzi; decisione O2 di sviluppo-listini-v2); 2. E_LISTINO_VERSIONE_CITATA (VERSIONE_CITATA: una BOZZA che un documento tiene con una FK RESTRICT o NO ACTION, la versione o una sua riga o un suo componente; le tabelle da script.fn_tabelle_che_trattengono, dettaglio.dove; righe e componenti della versione non contano, il verbo li cancella con lei). Con il motivo 1 esce. Versione inesistente o fuori perimetro: ''[]''. Non solleva. La chiamano il guard vendite.trgfn_listini_versioni_guard_per_stato (ramo DELETE), il verbo vendite.fn_elimina_versione_listino (prima di cancellare) e la superficie vendite.vw_listini_versioni_azioni (registro config.azioni_riga, ELIMINA_VERSIONE_LISTINO). SECURITY INVOKER, STABLE. Brief: brief-modello-documento-vendita §16.11 (E-1, E-2, E-3, Tid 2026-10-28).';
```

</div>

---
{% include-markdown "signature-core.md" %}
