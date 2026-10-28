{% include-markdown "it/dbzero/vendite/manual/fn_attiva_versione_listino.md" %}
# ⚙️ Funzione `fn_attiva_versione_listino`

```sql
CREATE FUNCTION fn_attiva_versione_listino(p_versione_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_attiva_versione_listino(p_versione_id bigint)
 RETURNS TABLE(versione_id bigint, stato_precedente character varying, stato_nuovo character varying, versioni_chiuse integer)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    c_attiva      CONSTANT config.stati_doc_listino_versioni.codice_interno%TYPE := 'ATTIVA';
    v_utente      config.user_override_azioni.auth_user_id%TYPE;
    v_stato_da    config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_stato_da_id vendite.listini_versioni.stato_doc_listino_versione_id%TYPE;
    v_stato_a_id  config.stati_doc_listino_versioni.id%TYPE;
    v_tx_id       vendite.listini_versioni.tx_id%TYPE;
    -- CONTEGGIO delle versioni chiuse.
    v_chiuse      integer;
BEGIN
    -- ==========================================================
    -- Scopo: attivare una versione di listino, chiudendo le
    --   precedenti. Vedi l'intestazione dei changeSet 20261028-12 e -32.
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametro e versione, nel perimetro.
    IF p_versione_id IS NULL OR p_versione_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_attiva_versione_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_versione_id', p_versione_id),
            NULL::uuid, 'vendite.fn_attiva_versione_listino',
            'p_versione_id (obbligatorio, maggiore di zero)');
    END IF;

    SELECT lv.stato_doc_listino_versione_id, s.codice_interno, lv.tx_id
      INTO v_stato_da_id, v_stato_da, v_tx_id
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = p_versione_id
       AND script.fn_scope_ef_whitelist_via_listino_versione(v_utente, lv.id)
       FOR UPDATE OF lv;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_attiva_versione_listino',
            'E_VENDITE_LISTINO_VERSIONE_NOT_FOUND',
            -- Frase chiusa: nessun segnaposto, il variadico vuoto e' esplicito.
            jsonb_build_object('id', p_versione_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Prima riga comune: lo stato che ha gia', l'azione.
    v_stato_a_id := script.fn_doc_stato_id('vendite.listini_versioni'::regclass, c_attiva);
    IF v_stato_a_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_attiva_versione_listino',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_doc_listino_versioni',
                               'codice', c_attiva),
            NULL::uuid, 'stato ATTIVA (config.stati_doc_listino_versioni)');
    END IF;
    PERFORM script.fn_guard_passaggio(v_utente, 'vendite.listini_versioni'::regclass,
                                      v_stato_da_id, v_stato_a_id);

    -- 3. Prima cio' che vieta, prima di toccare le altre versioni.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'vendite.fn_attiva_versione_listino',
        script.fn_check_versione_listino_attivabile(p_versione_id),
        NULL,
        v_tx_id,
        jsonb_build_object('versione_id', p_versione_id,
                           'stato_da', v_stato_da, 'stato_a', c_attiva));

    -- 4. Le precedenti che si sovrappongono si chiudono il giorno
    --    prima della decorrenza nuova: lo stesso lettore
    --    dell'anteprima.
    UPDATE vendite.listini_versioni lv
       SET valido_al = d.valido_al_dopo
      FROM vendite.fn_versioni_listino_da_chiudere(p_versione_id) d
     WHERE lv.id = d.versione_id;
    GET DIAGNOSTICS v_chiuse = ROW_COUNT;

    -- 5. Lo stato, attraverso la porta.
    PERFORM script.fn_doc_scrivi_stato('vendite.listini_versioni'::regclass,
                                       p_versione_id, v_stato_a_id);

    RETURN QUERY SELECT p_versione_id, v_stato_da, c_attiva, v_chiuse;
END;
$function$

COMMENT ON FUNCTION vendite.fn_attiva_versione_listino(p_versione_id bigint)
IS 'VERBO dell''attivazione di una versione di listino (BOZZA -> ATTIVA), in una transazione: la versione FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_listino_versione: DEFINER, la RLS non c''e''; fuori perimetro E_VENDITE_LISTINO_VERSIONE_NOT_FOUND); la prima riga comune (script.fn_guard_passaggio: E_DOC_GIA_NELLO_STATO, l''azione attiva_listino della riga del passaggio); prima cio'' che vieta (il primo motivo di script.fn_check_versione_listino_attivabile: spenta, senza prezzi); poi le versioni precedenti che si sovrappongono prendono valido_al = decorrenza - 1 (vendite.fn_versioni_listino_da_chiudere, lo stesso lettore dell''anteprima: decisione D3 di sviluppo-listini-v2); infine lo stato dalla scrittura comune (script.fn_doc_scrivi_stato, attraverso la porta). Ritorna versione, stati (codice_interno) e quante versioni ha chiuso. Prende il posto di listini_service.fn_change_versione_state (regole, chiusura delle precedenti e UPDATE dello stato nel backend). EXECUTE solo all''applicazione. Brief: brief-modello-documento-vendita §16 (L-3, L-4, Tid 2026-10-28).';
```

</div>

---
{% include-markdown "signature-core.md" %}
