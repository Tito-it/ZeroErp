{% include-markdown "it/dbzero/script/manual/fn_check_listino_riga_rettificabile.md" %}
# ⚙️ Funzione `fn_check_listino_riga_rettificabile`

```sql
CREATE FUNCTION fn_check_listino_riga_rettificabile(p_listino_riga_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_listino_riga_rettificabile(p_listino_riga_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_versione_id vendite.listini_righe.listino_versione_id%TYPE;
    v_listino_id  vendite.listini_versioni.listino_id%TYPE;
    v_codice      vendite.listini_versioni.codice_versione%TYPE;
    v_stato       config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_iniziale    config.stati_doc_listino_versioni.iniziale%TYPE;
    v_propagata   boolean;
BEGIN
    -- =========================================================
    -- Scopo: dire perche' il prezzo di una riga di listino NON si
    --   rettifica. La rettifica corregge il prezzo di una riga del
    --   listino in uso, col motivo: e' l'unica scrittura di una riga
    --   fuori dalla bozza, e passa dal verbo
    --   vendite.fn_rettifica_riga_listino. '[]' = si rettifica.
    --   Non solleva: lo fanno il verbo e il guard delle righe dentro la
    --   sua porta; la superficie la mostra. L'ordine dei motivi e' il
    --   contratto.
    -- =========================================================
    SELECT lr.listino_versione_id, lv.listino_id, lv.codice_versione,
           s.codice_interno, s.iniziale
      INTO v_versione_id, v_listino_id, v_codice, v_stato, v_iniziale
      FROM vendite.listini_righe lr
      JOIN vendite.listini_versioni lv ON lv.id = lr.listino_versione_id
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lr.id = p_listino_riga_id;

    -- 0. Una riga che non si legge non si giudica: il verbo la cerca
    --    nel perimetro, e non trovata risponde lui.
    IF NOT FOUND THEN
        RETURN jsonb_build_array();
    END IF;

    -- 1. In bozza la riga si modifica: la rettifica e' per il listino
    --    in uso.
    IF v_iniziale THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_RIGA_LISTINO_RETTIFICA_IN_BOZZA',
            'reason',     'VERSIONE_IN_BOZZA',
            'reason_key', 'vendite.listini.azione_reason.versione_in_bozza',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione_id,
                                             'listino_riga_id', p_listino_riga_id,
                                             'stato', v_stato),
            'valori',     jsonb_build_array(v_codice::text)));
    END IF;

    -- 2. Una versione CHIUSA e' la storia dei prezzi. CHIUSA e' la
    --    destinazione della chiusura, e si nomina col codice.
    IF v_stato = 'CHIUSA' THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_RIGA_LISTINO_VERSIONE_CHIUSA',
            'reason',     'VERSIONE_CHIUSA',
            'reason_key', 'vendite.listini.azione_reason.versione_chiusa',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione_id,
                                             'listino_riga_id', p_listino_riga_id,
                                             'stato', v_stato,
                                             'operazione', 'UPDATE'),
            'valori',     jsonb_build_array('UPDATE', p_listino_riga_id::text, v_stato)));
    END IF;

    -- 3. Si rettifica il listino IN USO: la versione in vigore alla data
    --    operativa (la sede della regola e' vendite.fn_listino_versione_in_vigore).
    --    Una versione che non e' ancora iniziata, o e' gia' finita, si clona.
    IF vendite.fn_listino_versione_in_vigore(v_listino_id, script.fn_data_operativa())
       IS DISTINCT FROM v_versione_id THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_RIGA_LISTINO_RETTIFICA_NON_IN_VIGORE',
            'reason',     'NON_IN_VIGORE',
            'reason_key', 'vendite.listini.azione_reason.non_in_vigore',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione_id,
                                             'listino_riga_id', p_listino_riga_id,
                                             'stato', v_stato,
                                             'data', script.fn_data_operativa()),
            'valori',     jsonb_build_array(v_codice::text)));
    END IF;

    -- 4. Il prezzo non si rettifica se e' stato USATO: la riga la cita
    --    (listino_riga_id) una riga di commessa, un'attivita' fatturabile,
    --    o una riga (o un componente) di preventivo, ordine, contratto,
    --    DDT, offerta, anche da una bozza. Ogni colonna listino_riga_id ha
    --    il suo indice parziale. Per aggiungere nuove tabelle: UNION ALL
    --    qui sotto.
    SELECT EXISTS(
        SELECT 1 FROM vendite.commesse_attivita
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.attivita_fatturabili
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.preventivi_righe
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.preventivi_righe_componenti
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.ordini_righe
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.ordini_righe_componenti
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.contratti_righe
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.contratti_righe_componenti
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.ddt_righe
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.ddt_righe_componenti
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.offerte_commerciali_eccezioni
         WHERE listino_riga_id = p_listino_riga_id
        UNION ALL
        SELECT 1 FROM vendite.offerte_commerciali_eccezioni_componenti
         WHERE listino_riga_id = p_listino_riga_id
    )
    INTO v_propagata;

    IF v_propagata THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_RIGA_LISTINO_PROPAGATA',
            'reason',     'RIGA_PROPAGATA',
            'reason_key', 'vendite.listini.azione_reason.riga_propagata',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione_id,
                                             'listino_riga_id', p_listino_riga_id,
                                             'stato', v_stato,
                                             'operazione', 'UPDATE'),
            'valori',     jsonb_build_array(p_listino_riga_id::text)));
    END IF;

    RETURN jsonb_build_array();
END;
$function$

COMMENT ON FUNCTION script.fn_check_listino_riga_rettificabile(p_listino_riga_id bigint)
IS 'Perche'' il prezzo di una riga di listino NON si rettifica: jsonb array di motivi (codice, reason, reason_key, dettaglio, valori), il primo e'' quello che si solleva; ''[]'' = si rettifica. La rettifica corregge col motivo il prezzo di una riga del listino in uso, ed e'' l''unica scrittura di una riga fuori dalla bozza (vendite.fn_rettifica_riga_listino). Motivi, in ordine: 1. E_RIGA_LISTINO_RETTIFICA_IN_BOZZA (VERSIONE_IN_BOZZA, reason_key vendite.listini.azione_reason.versione_in_bozza: in bozza, lo stato iniziale del vocabolario config.stati_doc_listino_versioni, la riga si modifica); 2. E_RIGA_LISTINO_VERSIONE_CHIUSA (VERSIONE_CHIUSA, reason_key vendite.listini.azione_reason.versione_chiusa); 3. E_RIGA_LISTINO_RETTIFICA_NON_IN_VIGORE (NON_IN_VIGORE, reason_key vendite.listini.azione_reason.non_in_vigore: la versione non e'' quella in vigore alla data operativa, vendite.fn_listino_versione_in_vigore con script.fn_data_operativa; non ancora iniziata o gia'' finita, si clona); 4. E_RIGA_LISTINO_PROPAGATA (RIGA_PROPAGATA, reason_key vendite.listini.azione_reason.riga_propagata: la riga e'' citata da una riga di commessa, un''attivita'' fatturabile, o una riga principale o un componente di preventivo, ordine, contratto, DDT od offerta, anche in bozza; per cambiarne il prezzo si fa una versione nuova del listino). Una riga che non si legge non si giudica (''[]''). Non solleva. La chiamano il verbo vendite.fn_rettifica_riga_listino, il guard vendite.trgfn_listini_righe_guard_stato dentro la porta del verbo, e la superficie vendite.vw_listini_righe_azioni (rettifica_blocco_*), registro config.azioni_riga (RETTIFICA_RIGA_LISTINO). SECURITY INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
