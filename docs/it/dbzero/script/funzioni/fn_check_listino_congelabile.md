# ⚙️ Funzione `fn_check_listino_congelabile`

```sql
CREATE FUNCTION fn_check_listino_congelabile(p_documento character varying, p_listino_id bigint, p_listino_versione_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_listino_congelabile(p_documento character varying, p_listino_id bigint, p_listino_versione_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

-- ⚠️ p_documento e' il codice della sorgente (OFFERTA_COMMERCIALE |
--   CONTRATTO), ancorato a config.sorgenti.codice_interno (grammatica
--   unica dei tipi di documento, lotto 1).
DECLARE
    v_versione vendite.listini_versioni.id%TYPE;
    v_stato    vendite.listini_versioni.stato%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire perche' un documento NON puo' congelare la sua versione
    --   di listino: l'offerta all'emissione, il contratto
    --   all'attivazione. '[]' = puo'. Non solleva: sollevare e'
    --   mestiere dei guard di transizione, che la CHIAMANO, come le
    --   capability che spengono il pulsante (linee-guida-sql §12.5.2).
    --
    --   La versione giudicata e' quella che verrebbe congelata:
    --   vendite.fn_listino_versione_operativa (la fissata, altrimenti
    --   quella in vigore oggi).
    --
    -- Motivi (il primo e' quello che il guard solleva):
    --   1. nessuna versione in vigore oggi (OFFERTA_COMMERCIALE, CONTRATTO);
    --   2. la versione fissata non e' ATTIVA (solo OFFERTA_COMMERCIALE: il
    --      contratto tiene la versione che l'offerta accettata gli ha
    --      portato, anche se nel frattempo si e' chiusa).
    --   Senza listino (negoziato puro del contratto): nessun motivo,
    --   lo giudica il guard del negoziato puro.
    -- =========================================================

    IF p_documento IS NULL OR p_documento NOT IN ('OFFERTA_COMMERCIALE', 'CONTRATTO') THEN
        -- Errore di CHIAMANTE, non di dato: lo stesso codice del
        -- risolutore delle righe.
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'script.fn_check_listino_congelabile',
            'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('documento', p_documento),
            NULL::uuid,
            COALESCE(p_documento, '<null>'));
    END IF;

    IF p_listino_id IS NULL THEN
        RETURN jsonb_build_array();
    END IF;

    v_versione := vendite.fn_listino_versione_operativa(p_listino_id, p_listino_versione_id);

    -- 1. Nessuna versione in vigore oggi: offerta.
    IF v_versione IS NULL AND p_documento = 'OFFERTA_COMMERCIALE' THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO',
            'reason',     'LISTINO_SENZA_VERSIONE_IN_VIGORE',
            'reason_key', 'vendite.offerte.azione_reason.listino_senza_versione_in_vigore',
            'dettaglio',  jsonb_build_object('listino_id', p_listino_id, 'data', (SELECT script.fn_data_operativa())),
            -- Frase chiusa: niente da infilare nei segnaposto.
            'valori',     jsonb_build_array()));
    END IF;

    -- 1. Nessuna versione in vigore oggi: contratto.
    IF v_versione IS NULL AND p_documento = 'CONTRATTO' THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO',
            'reason',     'LISTINO_SENZA_VERSIONE_IN_VIGORE',
            'reason_key', 'vendite.contratti.azione_reason.listino_senza_versione_in_vigore',
            'dettaglio',  jsonb_build_object('listino_id', p_listino_id, 'data', (SELECT script.fn_data_operativa())),
            'valori',     jsonb_build_array()));
    END IF;

    IF p_documento = 'CONTRATTO' THEN
        RETURN jsonb_build_array();
    END IF;

    -- 2. Offerta: la versione che congelerebbe dev'essere ATTIVA.
    --    Quella in vigore oggi lo e' per costruzione (una CHIUSA ha
    --    valido_al passato); qui risponde la versione FISSATA prima
    --    dell'emissione.
    SELECT lv.stato
      INTO v_stato
      FROM vendite.listini_versioni lv
     WHERE lv.id = v_versione;
    IF v_stato IS DISTINCT FROM 'ATTIVA' THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA',
            'reason',     'LISTINO_VERSIONE_NON_ATTIVA',
            'reason_key', 'vendite.offerte.azione_reason.listino_versione_non_attiva',
            'dettaglio',  jsonb_build_object('listino_id', p_listino_id,
                                             'listino_versione_id', v_versione,
                                             'stato_versione', v_stato),
            'valori',     jsonb_build_array()));
    END IF;

    RETURN jsonb_build_array();
END;
$function$

COMMENT ON FUNCTION script.fn_check_listino_congelabile(p_documento character varying, p_listino_id bigint, p_listino_versione_id bigint)
IS 'Check pura: i motivi per cui un documento con eccezioni non può congelare la sua versione di listino — l''offerta all''emissione (p_documento = OFFERTA), il contratto all''attivazione (CONTRATTO). ''[]'' = può. Giudica la versione che verrebbe congelata, vendite.fn_listino_versione_operativa (la fissata, altrimenti quella in vigore oggi), sui valori della testata: la chiamano anche i guard BEFORE ROW. Motivi in ordine: 1) nessuna versione in vigore oggi — E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO / E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO, reason LISTINO_SENZA_VERSIONE_IN_VIGORE, reason_key vendite.offerte.azione_reason.listino_senza_versione_in_vigore / vendite.contratti.azione_reason.listino_senza_versione_in_vigore; 2) solo OFFERTA, la versione fissata non è ATTIVA — E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA, reason LISTINO_VERSIONE_NON_ATTIVA, reason_key vendite.offerte.azione_reason.listino_versione_non_attiva. Il contratto tiene la versione che l''offerta gli ha portato anche se nel frattempo si è chiusa. Senza listino nessun motivo (negoziato puro, lo giudica trgfn_contratti_freeze_listino_versione). Altro p_documento: E_DOC_TIPO_NON_GESTITO. Lettori: vendite.trgfn_offerte_commerciali_guard_transizione e vendite.trgfn_contratti_freeze_listino_versione (sollevano il primo motivo), script.fn_available_actions_offerta e script.fn_available_actions_contratto (spengono «Emetti» e «Attiva» col motivo): pulsanti e guard non possono dissentire. Nasce il 2026-10-07, brief-db-offerta-emissione-ed-erogazione §C.1.3 (decisioni A-D2, A-D3 di Tid). ⭐ rev 2026-10-19 (20261019-22, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato). I codici dei motivi (E_OFFERTA_*) non cambiano.';
```

---
{% include-markdown "signature-core.md" %}
