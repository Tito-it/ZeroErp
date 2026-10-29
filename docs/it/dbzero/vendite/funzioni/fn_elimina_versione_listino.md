{% include-markdown "it/dbzero/vendite/manual/fn_elimina_versione_listino.md" %}
# ⚙️ Funzione `fn_elimina_versione_listino`

```sql
CREATE FUNCTION fn_elimina_versione_listino(p_versione_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_elimina_versione_listino(p_versione_id bigint)
 RETURNS TABLE(versione_id bigint, righe_eliminate integer, componenti_eliminati integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_listino_id vendite.listini_versioni.listino_id%TYPE;
    v_stato      config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_tx_id      vendite.listini_versioni.tx_id%TYPE;
    -- CONTEGGI delle righe cancellate.
    v_righe      integer;
    v_componenti integer;
BEGIN
    -- ==========================================================
    -- Scopo: eliminare una versione di listino in BOZZA con i
    --   suoi componenti e le sue righe, in una transazione.
    --   Vedi l'intestazione del changeSet 20261028-39.
    -- ==========================================================

    -- 1. Parametro e versione, nel perimetro (RLS).
    IF p_versione_id IS NULL OR p_versione_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_elimina_versione_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_versione_id', p_versione_id),
            NULL::uuid, 'vendite.fn_elimina_versione_listino',
            'p_versione_id (obbligatorio, maggiore di zero)');
    END IF;

    SELECT lv.listino_id, s.codice_interno, lv.tx_id
      INTO v_listino_id, v_stato, v_tx_id
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = p_versione_id
       FOR UPDATE OF lv;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_elimina_versione_listino',
            'E_VENDITE_LISTINO_VERSIONE_NOT_FOUND',
            -- Frase chiusa: nessun segnaposto, il variadico vuoto e' esplicito.
            jsonb_build_object('id', p_versione_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Prima cio' che vieta, prima di toccare righe e componenti.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'vendite.fn_elimina_versione_listino',
        script.fn_check_versione_listino_eliminabile(p_versione_id),
        NULL,
        v_tx_id,
        jsonb_build_object('versione_id', p_versione_id,
                           'listino_id', v_listino_id, 'stato', v_stato));

    -- 3. Componenti, righe, versione.
    DELETE FROM vendite.listini_righe_componenti c
     WHERE c.listino_versione_id = p_versione_id;
    GET DIAGNOSTICS v_componenti = ROW_COUNT;

    DELETE FROM vendite.listini_righe r
     WHERE r.listino_versione_id = p_versione_id;
    GET DIAGNOSTICS v_righe = ROW_COUNT;

    DELETE FROM vendite.listini_versioni lv
     WHERE lv.id = p_versione_id;

    RETURN QUERY SELECT p_versione_id, v_righe, v_componenti;
END;
$function$

COMMENT ON FUNCTION vendite.fn_elimina_versione_listino(p_versione_id bigint)
IS 'VERBO dell''eliminazione di una versione di listino, in una transazione: la versione FOR UPDATE nel perimetro (SECURITY INVOKER, la RLS delle tabelle del listino; non trovata E_VENDITE_LISTINO_VERSIONE_NOT_FOUND); prima cio'' che vieta (il primo motivo di script.fn_check_versione_listino_eliminabile: E_LISTINO_VERSIONE_NON_ELIMINABILE fuori dalla BOZZA, E_LISTINO_VERSIONE_CITATA se un documento la tiene); poi componenti, righe e versione. Ritorna la versione e quante righe e quanti componenti ha cancellato. Prende il posto dei tre DELETE del backend (listini_repository.delete_versione). Il permesso d''area resta al backend. EXECUTE solo all''applicazione. Brief: brief-modello-documento-vendita §16.11 (opzione a, E-1, E-2, E-3, Tid 2026-10-28).';
```

</div>

---
{% include-markdown "signature-core.md" %}
