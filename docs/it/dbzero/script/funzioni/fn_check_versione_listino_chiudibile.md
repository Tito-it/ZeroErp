{% include-markdown "it/dbzero/script/manual/fn_check_versione_listino_chiudibile.md" %}
# ⚙️ Funzione `fn_check_versione_listino_chiudibile`

```sql
CREATE FUNCTION fn_check_versione_listino_chiudibile(p_versione_id bigint, p_valido_al date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_versione_listino_chiudibile(p_versione_id bigint, p_valido_al date DEFAULT NULL::date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_versione vendite.listini_versioni%ROWTYPE;
    v_stato    config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_oggi     vendite.listini_versioni.valido_al%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: dire perche' una versione di listino NON si chiude
    --   alla data p_valido_al (NULL: se il pulsante si accende,
    --   o la rimozione della chiusura). '[]' = si chiude. Non
    --   solleva: sollevare e' del verbo, che la chiama, come la
    --   superficie della lista (linee-guida-sql §12.5.2).
    --   Vedi l'intestazione del changeSet 20261029-01.
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

    -- 1. Si chiude solo una ATTIVA.
    IF v_stato IS DISTINCT FROM 'ATTIVA' THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_LISTINO_VERSIONE_NON_CHIUDIBILE',
            'reason',     'VERSIONE_NON_ATTIVA',
            'reason_key', 'vendite.listini.azione_reason.versione_non_attiva',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione.id,
                                             'listino_id', v_versione.listino_id,
                                             'stato', v_stato),
            'valori',     jsonb_build_array(v_versione.codice_versione,
                                            COALESCE(v_stato, 'NULL'))));
    END IF;

    -- 2. La fine non sta nel passato: i documenti gia' datati
    --    dopo quella fine perderebbero il prezzo.
    v_oggi := script.fn_data_operativa();
    IF p_valido_al < v_oggi THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_LISTINO_VERSIONE_FINE_NEL_PASSATO',
            'reason',     'FINE_NEL_PASSATO',
            'reason_key', 'vendite.listini.azione_reason.fine_nel_passato',
            'dettaglio',  jsonb_build_object('listino_versione_id', v_versione.id,
                                             'listino_id', v_versione.listino_id,
                                             'valido_al', p_valido_al,
                                             'oggi', v_oggi),
            'valori',     jsonb_build_array(v_versione.codice_versione,
                                            to_char(p_valido_al, 'DD/MM/YYYY'),
                                            to_char(v_oggi, 'DD/MM/YYYY'))));
    END IF;

    RETURN jsonb_build_array();
END;
$function$

COMMENT ON FUNCTION script.fn_check_versione_listino_chiudibile(p_versione_id bigint, p_valido_al date)
IS 'Perche'' una versione di listino NON si chiude alla data p_valido_al: jsonb array di motivi (codice, reason, reason_key, dettaglio, valori), il primo e'' quello che si solleva; ''[]'' = si chiude. Motivi: 1. E_LISTINO_VERSIONE_NON_CHIUDIBILE (VERSIONE_NON_ATTIVA: in BOZZA la fine si decide con le altre date, una CHIUSA non cambia piu''; con questo motivo esce); 2. E_LISTINO_VERSIONE_FINE_NEL_PASSATO (FINE_NEL_PASSATO: p_valido_al precede la data operativa, script.fn_data_operativa; oggi e'' ammesso). p_valido_al NULL: niente motivo 2 (se il pulsante si accende; la rimozione della chiusura). Una fine prima dell''inizio la rifiuta il guard comune delle date, non questa. Versione inesistente o fuori perimetro: ''[]''. Non solleva. La chiamano il verbo vendite.fn_programma_chiusura_versione_listino e la superficie vendite.vw_listini_versioni_azioni (registro config.azioni_riga, CHIUDI_VERSIONE_LISTINO). Non sta nel guard per stato: l''attivazione chiude la precedente anche nel passato (D3 e D2 di sviluppo-listini-v2). Prima la regola stava solo nel frontend (min-date del dialogo). SECURITY INVOKER, STABLE. Brief: brief-modello-documento-vendita §16.14 (C-2 = a, Tid 2026-10-29).';
```

</div>

---
{% include-markdown "signature-core.md" %}
