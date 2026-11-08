{% include-markdown "it/dbzero/script/manual/fn_check_ordine_confermabile.md" %}
# ⚙️ Funzione `fn_check_ordine_confermabile`

```sql
CREATE FUNCTION fn_check_ordine_confermabile(p_ordine_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ordine_confermabile(p_ordine_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono la CONFERMA di un
--   ordine. Funzione PURA (fn_check_*): non solleva, non scrive.
--   Consumatori: vendite.trgfn_ordini_guard_transizione (che
--   solleva il codice del primo motivo) e
--   script.fn_available_actions_ordine (che spegne il bottone ed
--   espone la reason). Gemella di fn_check_ordine_annullabile.
--   Brief: brief-db-be-iva-risolutore-e-regime-cliente, I9 / §R-3.
-- Ritorna: [] se confermabile; altrimenti array ORDINATO di
--   {codice, reason, reason_key, dettaglio}.
-- rev 2026-11-03 (20261103-26, brief-db-addebito-trasporto-ordine
--   §8.4 K-2): MOTIVO 1 nuovo, un ordine di soli oneri non si
--   conferma; il motivo dell'aliquota diventa il 2.
DECLARE
    v_motivi  jsonb := '[]'::jsonb;
    v_uid     vendite.ordini.uid%TYPE;
    v_numero  vendite.ordini.numero%TYPE;
    v_riga_id vendite.ordini_righe.id%TYPE;
    v_riga_nr vendite.ordini_righe.riga_nr%TYPE;
    -- Nudi: un CONTEGGIO e un flag calcolato, nessuna colonna ne e' il riflesso.
    v_righe_attive integer;
    v_ha_merce     boolean;
BEGIN
    IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_ordine_confermabile', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'ordine_id', 'valore', p_ordine_id),
            NULL::uuid, 'ordine_id obbligatorio (>0)');
    END IF;

    -- ⭐ `o.numero` sulla SELECT che c'era gia': serve a COMPORRE la frase
    --   («Ordine %s: la riga %s ...»), non a decidere. Nota sul trigger
    --   BEFORE: vedi fn_check_commessa_annullabile.
    SELECT o.uid, o.numero INTO v_uid, v_numero
      FROM vendite.ordini o
     WHERE o.id = p_ordine_id;

    IF v_uid IS NULL THEN
        RETURN v_motivi;   -- ordine inesistente: decide il chiamante
    END IF;

    -- MOTIVO 1 (rev 2026-11-03, K-2) — SOLI ONERI: l'ordine ha righe
    --   attive ma nessuna e' merce. Non si evaderebbe mai (l'onere non
    --   si evade): un addebito senza merce si scrive in commessa.
    --
    -- ⛔ Il documento VUOTO non e' questo motivo: zero righe attive lo
    --   dice la precondizione della matrice (meta.requires_righe, Regola
    --   2 del guard, E_ORDINE_CONFERMA_SENZA_RIGHE). Qui solo «righe si',
    --   merce no», altrimenti l'ordine vuoto direbbe «solo oneri».
    -- ⭐ «E' merce» e' script.fn_natura_e_merce sulla natura CONGELATA
    --   della riga; su ordine «non merce» = onere (l'ammissione lascia
    --   entrare solo merce e articoli-onere).
    SELECT count(*)::integer,
           bool_or(script.fn_natura_e_merce(r.natura_vendita_id))
      INTO v_righe_attive, v_ha_merce
      FROM vendite.ordini_righe r
     WHERE r.ordine_id = p_ordine_id
       AND r.attivo IS TRUE;

    IF v_righe_attive > 0 AND v_ha_merce IS NOT TRUE THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ORDINE_CONFERMA_SOLO_ONERI',
            'reason',     'ORDINE_SOLO_ONERI',
            'reason_key', 'vendite.ordini.azione_reason.solo_oneri',
            'dettaglio',  jsonb_build_object('righe_attive', v_righe_attive),
            -- «L'ordine %s ha solo oneri e nessuna merce: ...»
            'valori',     jsonb_build_array(COALESCE(v_numero, p_ordine_id::text)));
    END IF;

    -- MOTIVO 2 — VALORE DELLA RIGA: una riga che porta un PREZZO
    --   porta anche l'ALIQUOTA. Senza, la riga entra comunque in
    --   vendite.vw_ordini_righe_iva_base (che filtra solo attivo e
    --   quantita > 0) e vw_ordini_riepilogo_iva_dettaglio la somma
    --   con COALESCE(aliquota, 0): imponibile pieno, imposta zero,
    --   su un documento confermato e stampato.
    --
    -- ⚠️ `prezzo_unitario IS NOT NULL` e' oggi sempre vero — la
    --   colonna e' NOT NULL — quindi di fatto la regola vale su
    --   OGNI riga attiva. Si scrive comunque perche' e' la forma
    --   vera della regola, ed e' gia' successo che una colonna
    --   prezzo diventasse facoltativa (20260819-13 su
    --   vendite.ddt_righe_componenti).
    --
    -- ⚠️ ORDER BY prima del LIMIT: senza, quale riga esca dipende
    --   dal piano del planner e il messaggio nominerebbe una riga
    --   diversa a ogni corsa.
    --
    -- ⚠️ Nel dettaglio vanno l'id (per chi diagnostica) E il
    --   numero di riga (per la frase che legge una persona): sono
    --   due destinatari diversi.
    SELECT r.id, r.riga_nr
      INTO v_riga_id, v_riga_nr
      FROM vendite.ordini_righe r
     WHERE r.ordine_id = p_ordine_id
       AND r.attivo IS TRUE
       AND r.prezzo_unitario IS NOT NULL
       AND r.iva_id IS NULL
     ORDER BY r.riga_nr, r.id
     LIMIT 1;

    IF v_riga_id IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ORDINE_RIGA_IVA_MANCANTE',
            'reason',     'RIGA_SENZA_ALIQUOTA',
            'reason_key', 'vendite.ordini.azione_reason.iva_mancante',
            'dettaglio',  jsonb_build_object('riga_id', v_riga_id,
                                             'riga_nr', v_riga_nr),
            -- «Ordine %s: la riga %s ha un prezzo ma nessuna aliquota IVA.»
            'valori',     jsonb_build_array(COALESCE(v_numero, p_ordine_id::text),
                                            COALESCE(v_riga_nr::text, '?')));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_ordine_confermabile(p_ordine_id bigint)
IS 'Single source dei motivi che impediscono la CONFERMA di un ordine. Ritorna [] se confermabile, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. PURA: non solleva e non scrive. Consumatori: vendite.trgfn_ordini_guard_transizione (solleva il codice del primo motivo, su ogni ingresso in CONFERMATO) e script.fn_available_actions_ordine (spegne il bottone ed espone la reason) — la stessa funzione da entrambi i lati, cosi'' bottone e guard non divergono. ⭐ Due motivi, in quest''ordine. 1 (rev 2026-11-03, 20261103-26, brief-db-addebito-trasporto-ordine §8.4 K-2): E_ORDINE_CONFERMA_SOLO_ONERI, reason ORDINE_SOLO_ONERI, reason_key vendite.ordini.azione_reason.solo_oneri — l''ordine ha righe attive ma nessuna merce (script.fn_natura_e_merce sulla natura congelata): non si evaderebbe mai, e un addebito senza merce si scrive in commessa. Primo perche'' e'' la ragione di fondo. Sul rientro automatico in CONFERMATO non scatta: il rientro presuppone un legame su una riga merce attiva. 2: E_ORDINE_RIGA_IVA_MANCANTE, una riga attiva che porta un prezzo senza aliquota IVA. Chiude un difetto silenzioso gemello di quello sanato sul DDT il 2026-08-28: vw_ordini_righe_iva_base filtra solo attivo e quantita > 0 — non guarda ne'' prezzo ne'' iva_id — e vw_ordini_riepilogo_iva_dettaglio aggrega con COALESCE(aliquota, 0), producendo imponibile pieno e imposta zero su un ordine confermato e stampato. ⛔ NON contiene il motivo «documento senza righe»: quello non e'' una regola della conferma ma una precondizione generica guidata dalla matrice (config.transizioni_stati_ordini, meta.requires_righe), e portarlo qui trasformerebbe un meccanismo data-driven in codice cablato sulla base del seed di oggi. Per lo stesso motivo il motivo 1 scatta solo con righe attive presenti: l''ordine vuoto dice E_ORDINE_CONFERMA_SENZA_RIGHE. ⚠️ La condizione prezzo_unitario IS NOT NULL e'' oggi sempre vera (colonna NOT NULL): si scrive perche'' e'' la forma vera della regola e perche'' in questo progetto una colonna prezzo e'' gia'' diventata facoltativa una volta (20260819-13). Piano: brief-db-be-iva-risolutore-e-regime-cliente, I9.';
```

</div>

---
{% include-markdown "signature-core.md" %}
