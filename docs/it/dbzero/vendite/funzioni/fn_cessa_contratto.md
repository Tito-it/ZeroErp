{% include-markdown "it/dbzero/vendite/manual/fn_cessa_contratto.md" %}
# ⚙️ Funzione `fn_cessa_contratto`

```sql
CREATE FUNCTION fn_cessa_contratto(p_contratto_id bigint, p_valido_al date)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cessa_contratto(p_contratto_id bigint, p_valido_al date)
 RETURNS TABLE(contratto_id bigint, stato_precedente character varying, stato_nuovo character varying, programmata boolean)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente      config.user_override_azioni.auth_user_id%TYPE;
    v_stato_da    config.stati_doc_contratti.codice_interno%TYPE;
    v_stato_da_id vendite.contratti.stato_doc_contratto_id%TYPE;
    v_cessato     config.stati_doc_contratti.codice_interno%TYPE;
    v_cessato_id  config.stati_doc_contratti.id%TYPE;
    v_oggi        vendite.contratti.valido_al%TYPE;
BEGIN
    -- ==========================================================
    -- Scopo: cessare un contratto alla data p_valido_al. Oggi:
    --   data e stato; futura: solo la data (la chiude il job).
    --   Vedi l'intestazione del changeSet.
    --   rev 2026-10-31 (20261031-11, brief-modello-documento-vendita §17): la destinazione
    --   e' lo stato di cessazione del vocabolario, non 'CESSATO'.
    -- Ritorna: contratto_id, stato_precedente, stato_nuovo
    --   (codice_interno), programmata (lo stato non e' cambiato).
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_contratto_id IS NULL OR p_contratto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cessa_contratto',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_contratto_id', p_contratto_id),
            NULL::uuid, 'vendite.fn_cessa_contratto',
            'p_contratto_id (obbligatorio, maggiore di zero)');
    END IF;

    IF p_valido_al IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cessa_contratto',
            'E_CONTRATTO_CESSAZIONE_SENZA_DATA',
            jsonb_build_object('contratto_id', p_contratto_id, 'campo', 'valido_al'),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT c.stato_doc_contratto_id, s.codice_interno
      INTO v_stato_da_id, v_stato_da
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
     WHERE c.id = p_contratto_id
       AND script.fn_scope_ef_whitelist_via_contratto(v_utente, c.id)
       FOR UPDATE OF c;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cessa_contratto',
            'E_CONTRATTO_NON_TROVATO', jsonb_build_object('id', p_contratto_id), NULL::uuid,
            p_contratto_id::text);
    END IF;

    -- 3. La destinazione del passaggio: lo stato di cessazione, dal
    --    vocabolario; il suo codice per i messaggi e la risposta.
    v_cessato_id := script.fn_stato_cessazione_id('vendite.contratti'::regclass);
    IF v_cessato_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cessa_contratto',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_doc_contratti.cessazione'),
            NULL::uuid, 'stato di cessazione (config.stati_doc_contratti.cessazione)');
    END IF;
    v_cessato := script.fn_doc_stato_codice('vendite.contratti'::regclass, v_cessato_id);

    -- 4. Prima riga comune: lo stato che ha gia', azione.
    PERFORM script.fn_guard_passaggio(v_utente, 'vendite.contratti'::regclass,
                                      v_stato_da_id, v_cessato_id);

    -- 5. La strada, dalla matrice: la cessazione programmata non
    --    scrive lo stato, e il guard di transizione non la vede.
    IF NOT EXISTS (SELECT 1
                     FROM script.fn_doc_passaggio('vendite.contratti'::regclass,
                                                  v_stato_da_id, v_cessato_id)) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cessa_contratto',
            'E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA',
            jsonb_build_object('contratto_id', p_contratto_id,
                               'stato_da', v_stato_da, 'stato_a', v_cessato,
                               'valido_al', p_valido_al),
            NULL::uuid,
            p_contratto_id::text, v_stato_da, v_cessato, p_valido_al::text);
    END IF;

    -- 6. Niente riscrittura storica: la data non e' nel passato.
    v_oggi := script.fn_data_operativa();
    IF p_valido_al < v_oggi THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cessa_contratto',
            'E_CONTRATTO_VALIDO_AL_RETROATTIVO',
            jsonb_build_object('contratto_id', p_contratto_id,
                               'valido_al',    p_valido_al,
                               'today',        v_oggi,
                               'campo',        'valido_al'),
            NULL::uuid,
            p_valido_al::text, v_oggi::text);
    END IF;

    -- 7. La data. I guard della testata la giudicano (le date di
    --    validita', il lucchetto fuori bozza).
    UPDATE vendite.contratti c
       SET valido_al = p_valido_al
     WHERE c.id = p_contratto_id
       AND c.valido_al IS DISTINCT FROM p_valido_al;

    -- 8. Oggi: lo stato, attraverso la porta. Futura: e' programmata.
    IF p_valido_al = v_oggi THEN
        PERFORM script.fn_doc_scrivi_stato('vendite.contratti'::regclass,
                                           p_contratto_id, v_cessato_id);
        RETURN QUERY SELECT p_contratto_id, v_stato_da, v_cessato, false;
    ELSE
        RETURN QUERY SELECT p_contratto_id, v_stato_da, v_stato_da, true;
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cessa_contratto(p_contratto_id bigint, p_valido_al date)
IS 'VERBO della cessazione manuale di un contratto, con la sua data (brief-modello-documento-vendita §11, Y-2 e Y-3 di Tid 2026-10-26). Data mancante: E_CONTRATTO_CESSAZIONE_SENZA_DATA. Testata FOR UPDATE col predicato della policy (script.fn_scope_ef_whitelist_via_contratto; fuori perimetro E_CONTRATTO_NON_TROVATO). La destinazione e'' lo stato di cessazione del vocabolario (script.fn_stato_cessazione_id, dal 2026-10-31, §17; oggi CESSATO). Prima riga comune verso la cessazione (script.fn_guard_passaggio: emetti_contratto; lo stato che ha gia'': E_DOC_GIA_NELLO_STATO). La strada dalla matrice (script.fn_doc_passaggio): nessun passaggio dallo stato di oggi a CESSATO, E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA (serve qui: la cessazione programmata non scrive lo stato). Data passata: E_CONTRATTO_VALIDO_AL_RETROATTIVO (era nel guard di transizione, col ramo della GUC app.cessazione_automatica, ritirata). Poi scrive valido_al; con la data di oggi scrive anche lo stato CESSATO dalla scrittura comune (script.fn_doc_scrivi_stato, il guard di transizione giudica matrice e data arrivata); con una data futura la cessazione e'' programmata, e lo stato lo scrive il job quando scade (vendite.fn_cessa_contratti_scaduti). Ritorna contratto_id, stato_precedente, stato_nuovo (codice_interno), programmata. Prende il posto della scelta programmata/immediata di contratti_service.cambia_stato (backend). EXECUTE solo all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
