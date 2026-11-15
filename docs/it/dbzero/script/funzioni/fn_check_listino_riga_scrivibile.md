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
    -- Tipo esplicito: l'operazione, nessuna colonna di cui sia il riflesso.
    v_operazione text := COALESCE(p_operazione,
                                  CASE WHEN p_listino_riga_id IS NULL THEN 'INSERT' ELSE 'UPDATE' END);
    v_propagata  boolean;
BEGIN
    -- =========================================================
    -- Scopo: dire perche' una riga di listino NON si scrive. Senza
    --   p_listino_riga_id la domanda e' la riga NUOVA della versione
    --   (INSERT); con, la riga che c'e' (UPDATE, DELETE). '[]' = si
    --   scrive. Non solleva: lo fa il guard di stato delle righe, che
    --   la chiama, come le due superfici (linee-guida-sql §12.5.2).
    --   L'ordine dei motivi e' il contratto: il guard solleva il primo.
    -- =========================================================
    SELECT s.codice_interno, s.iniziale INTO v_stato, v_iniziale
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = p_listino_versione_id;

    -- 1. In bozza (lo stato iniziale del vocabolario) si scrive tutto.
    IF v_iniziale THEN
        RETURN jsonb_build_array();
    END IF;

    -- 2. Una versione CHIUSA e' la storia dei prezzi: non si scrive
    --    niente, nemmeno una riga nuova. CHIUSA e' la destinazione
    --    della chiusura, e si nomina col codice.
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

    -- 3. Fuori dalla bozza una riga nuova e' una rettifica: si scrive.
    IF p_listino_riga_id IS NULL THEN
        RETURN jsonb_build_array();
    END IF;

    -- 4. Una riga che c'e' si cambia finche' il suo prezzo non e' stato
    --    USATO: la cita (listino_riga_id) una riga di commessa,
    --    un'attivita' fatturabile, o una riga (o un componente) di
    --    preventivo, ordine, contratto, DDT, offerta, anche da una bozza.
    --    Ogni colonna listino_riga_id ha il suo indice parziale. Per
    --    aggiungere nuove tabelle: UNION ALL qui sotto.
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
            'dettaglio',  jsonb_build_object('listino_versione_id', p_listino_versione_id,
                                             'listino_riga_id', p_listino_riga_id,
                                             'stato', v_stato,
                                             'operazione', v_operazione),
            'valori',     jsonb_build_array(p_listino_riga_id::text)));
    END IF;

    RETURN jsonb_build_array();
END;
$function$

COMMENT ON FUNCTION script.fn_check_listino_riga_scrivibile(p_listino_versione_id bigint, p_listino_riga_id bigint, p_operazione text)
IS 'Perche'' una riga di listino NON si scrive: jsonb array di motivi (codice, reason, reason_key, dettaglio, valori), il primo e'' quello che si solleva; ''[]'' = si scrive. Senza p_listino_riga_id la domanda e'' una riga nuova della versione (INSERT), con p_listino_riga_id la riga che c''e'' (UPDATE, DELETE); p_operazione entra nei valori del messaggio (default: INSERT senza riga, UPDATE con). In bozza, lo stato iniziale del vocabolario config.stati_doc_listino_versioni, si scrive tutto. Motivi, in ordine: 1. E_RIGA_LISTINO_VERSIONE_CHIUSA (VERSIONE_CHIUSA, reason_key vendite.listini.azione_reason.versione_chiusa: la versione e'' CHIUSA, la storia dei prezzi, e non si scrive niente, nemmeno una riga nuova); 2. E_RIGA_LISTINO_PROPAGATA (RIGA_PROPAGATA, reason_key vendite.listini.azione_reason.riga_propagata: fuori dalla bozza, la riga e'' citata da una riga di commessa, un''attivita'' fatturabile, o una riga principale o un componente di preventivo, ordine, contratto, DDT od offerta, anche in bozza; per cambiarne il prezzo si fa una versione nuova del listino). Fuori dalla bozza una riga nuova e'' una rettifica, e si scrive. Non solleva. La chiamano il guard vendite.trgfn_listini_righe_guard_stato (INSERT, UPDATE e DELETE delle righe) e le due superfici: vendite.vw_listini_versioni_azioni (aggiunta_riga_blocco_*, la riga nuova) e vendite.vw_listini_righe_azioni (modifica_blocco_*, la riga che c''e''), registro config.azioni_riga (AGGIUNGI_RIGA_LISTINO, MODIFICA_RIGA_LISTINO). SECURITY INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
