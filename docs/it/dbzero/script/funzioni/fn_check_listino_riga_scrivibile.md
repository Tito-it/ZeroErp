{% include-markdown "it/dbzero/script/manual/fn_check_listino_riga_scrivibile.md" %}
# ⚙️ Funzione `fn_check_listino_riga_scrivibile`

```sql
CREATE FUNCTION fn_check_listino_riga_scrivibile(p_listino_versione_id bigint, p_listino_riga_id bigint, p_operazione text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_listino_riga_scrivibile(p_listino_versione_id bigint, p_listino_riga_id bigint DEFAULT NULL::bigint, p_operazione text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_stato      config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_iniziale   config.stati_doc_listino_versioni.iniziale%TYPE;
    v_codice     vendite.listini_versioni.codice_versione%TYPE;
    -- Tipo esplicito: l'operazione, nessuna colonna di cui sia il riflesso.
    v_operazione text := COALESCE(p_operazione,
                                  CASE WHEN p_listino_riga_id IS NULL THEN 'INSERT' ELSE 'UPDATE' END);
BEGIN
    -- =========================================================
    -- Scopo: dire perche' NON si scrive nelle righe di una versione di
    --   listino: le righe (vendite.listini_righe), i prezzi dei
    --   componenti (vendite.listini_righe_componenti) e la periodicita'
    --   dei kit (vendite.listini_kit). Si scrive solo in bozza.
    --   p_listino_riga_id e' la riga che c'e' (NULL = una riga nuova),
    --   della tabella del guard che chiama: entra nel dettaglio e nei
    --   valori, non nella regola. '[]' = si scrive. Non solleva: lo
    --   fanno i tre guard, che la chiamano, come le superfici
    --   (linee-guida-sql §12.5.2). L'ordine dei motivi e' il contratto.
    --   Il prezzo di una riga della versione in vigore si corregge da
    --   un'altra porta, la rettifica (script.fn_check_listino_riga_rettificabile).
    -- =========================================================
    SELECT s.codice_interno, s.iniziale, lv.codice_versione
      INTO v_stato, v_iniziale, v_codice
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = p_listino_versione_id;

    -- 0. Una versione che non si legge non si giudica: parlano la FK
    --    e la policy della tabella che si scrive.
    IF NOT FOUND THEN
        RETURN jsonb_build_array();
    END IF;

    -- 1. In bozza (lo stato iniziale del vocabolario) si scrive tutto.
    IF v_iniziale THEN
        RETURN jsonb_build_array();
    END IF;

    -- 2. Una versione CHIUSA e' la storia dei prezzi. CHIUSA e' la
    --    destinazione della chiusura, e si nomina col codice.
    IF v_stato = 'CHIUSA' THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_RIGA_LISTINO_VERSIONE_CHIUSA',
            'reason',     'VERSIONE_CHIUSA',
            'reason_key', 'vendite.listini.azione_reason.versione_chiusa',
            'dettaglio',  jsonb_build_object('listino_versione_id', p_listino_versione_id,
                                             'listino_riga_id', p_listino_riga_id,
                                             'stato', v_stato,
                                             'operazione', v_operazione),
            'valori',     jsonb_build_array(v_operazione,
                                            COALESCE(p_listino_riga_id::text, 'nuova'),
                                            v_stato)));
    END IF;

    -- 3. Fuori dalla bozza non si aggiunge, non si modifica e non si
    --    elimina niente: la versione e' il listino in uso, o lo sara'.
    --    La reason_key e' sua: versione_non_in_bozza e' dell'eliminazione
    --    della versione (script.fn_check_versione_listino_eliminabile).
    RETURN jsonb_build_array(jsonb_build_object(
        'codice',     'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA',
        'reason',     'VERSIONE_NON_IN_BOZZA',
        'reason_key', 'vendite.listini.azione_reason.righe_non_in_bozza',
        'dettaglio',  jsonb_build_object('listino_versione_id', p_listino_versione_id,
                                         'listino_riga_id', p_listino_riga_id,
                                         'stato', v_stato,
                                         'operazione', v_operazione),
        'valori',     jsonb_build_array(v_codice::text)));
END;
$function$

COMMENT ON FUNCTION script.fn_check_listino_riga_scrivibile(p_listino_versione_id bigint, p_listino_riga_id bigint, p_operazione text)
IS 'Perche'' non si scrive nelle righe di una versione di listino (le righe vendite.listini_righe, i prezzi dei componenti vendite.listini_righe_componenti, la periodicita'' dei kit vendite.listini_kit): jsonb array di motivi (codice, reason, reason_key, dettaglio, valori), il primo e'' quello che si solleva; ''[]'' = si scrive. Si scrive solo in bozza, lo stato iniziale del vocabolario config.stati_doc_listino_versioni. p_listino_riga_id e'' la riga che c''e'' (NULL = una riga nuova), della tabella del guard che chiama, e p_operazione l''operazione (default: INSERT senza riga, UPDATE con): entrano nel dettaglio e nei valori, non nella regola. Una versione che non si legge non si giudica (''[]'': parlano la FK e la policy). Motivi, in ordine: 1. E_RIGA_LISTINO_VERSIONE_CHIUSA (VERSIONE_CHIUSA, reason_key vendite.listini.azione_reason.versione_chiusa: la versione e'' CHIUSA, la storia dei prezzi); 2. E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA (VERSIONE_NON_IN_BOZZA, reason_key vendite.listini.azione_reason.righe_non_in_bozza: la versione e'' il listino in uso, o lo sara''). Il prezzo di una riga della versione in vigore si corregge con la rettifica, il verbo vendite.fn_rettifica_riga_listino (script.fn_check_listino_riga_rettificabile). Non solleva. La chiamano i guard vendite.trgfn_listini_righe_guard_stato, vendite.trgfn_listini_righe_comp_guard_immutabilita_v5 e vendite.trgfn_listini_kit_guard, il verbo vendite.fn_varia_prezzi_versione_listino (senza riga: la variazione percentuale e'' un gesto della versione, e la giudica anche a righe zero), e le superfici vendite.vw_listini_versioni_azioni (aggiunta_riga_blocco_*, variazione_blocco_*, prezzi_bundle_blocco_*, periodicita_kit_blocco_*) e vendite.vw_listini_righe_azioni (modifica_blocco_*), registro config.azioni_riga. SECURITY INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
