{% include-markdown "it/dbzero/vendite/manual/fn_programma_chiusura_versione_listino.md" %}
# ⚙️ Funzione `fn_programma_chiusura_versione_listino`

```sql
CREATE FUNCTION fn_programma_chiusura_versione_listino(p_versione_id bigint, p_valido_al date)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_programma_chiusura_versione_listino(p_versione_id bigint, p_valido_al date)
 RETURNS TABLE(versione_id bigint, valido_al_prima date, valido_al_dopo date)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente     config.user_override_azioni.auth_user_id%TYPE;
    v_listino_id vendite.listini_versioni.listino_id%TYPE;
    v_prima      vendite.listini_versioni.valido_al%TYPE;
    v_stato      config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_tx_id      vendite.listini_versioni.tx_id%TYPE;
BEGIN
    -- ==========================================================
    -- Scopo: fissare (o togliere, p_valido_al NULL) la fine
    --   della validita' di una versione di listino ATTIVA.
    --   Vedi l'intestazione dei changeSet 20261029-02 e -08.
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametro e versione, nel perimetro.
    IF p_versione_id IS NULL OR p_versione_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_programma_chiusura_versione_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_versione_id', p_versione_id),
            NULL::uuid, 'vendite.fn_programma_chiusura_versione_listino',
            'p_versione_id (obbligatorio, maggiore di zero)');
    END IF;

    SELECT lv.listino_id, lv.valido_al, s.codice_interno, lv.tx_id
      INTO v_listino_id, v_prima, v_stato, v_tx_id
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = p_versione_id
       AND script.fn_scope_ef_whitelist_via_listino_versione(v_utente, lv.id)
       FOR UPDATE OF lv;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_programma_chiusura_versione_listino',
            'E_VENDITE_LISTINO_VERSIONE_NOT_FOUND',
            -- Frase chiusa: nessun segnaposto, il variadico vuoto e' esplicito.
            jsonb_build_object('id', p_versione_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Prima cio' che vieta.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'vendite.fn_programma_chiusura_versione_listino',
        script.fn_check_versione_listino_chiudibile(p_versione_id, p_valido_al),
        'valido_al',
        v_tx_id,
        jsonb_build_object('versione_id', p_versione_id,
                           'listino_id', v_listino_id, 'stato', v_stato,
                           'valido_al_prima', v_prima, 'valido_al', p_valido_al));

    -- 3. La fine, con la porta aperta per questa versione. Lo
    --    stato non cambia: CHIUSA la scrive il job.
    IF p_valido_al IS DISTINCT FROM v_prima THEN
        PERFORM set_config('zeroerp.listino_versione_fine', p_versione_id::text, true);
        UPDATE vendite.listini_versioni lv
           SET valido_al = p_valido_al
         WHERE lv.id = p_versione_id;
        PERFORM set_config('zeroerp.listino_versione_fine', '', true);
    END IF;

    RETURN QUERY SELECT p_versione_id, v_prima, p_valido_al;
END;
$function$

COMMENT ON FUNCTION vendite.fn_programma_chiusura_versione_listino(p_versione_id bigint, p_valido_al date)
IS 'VERBO «Chiudi» di una versione di listino: fissa la fine della validita'' (la chiusura programmata) o la toglie (p_valido_al NULL). La versione FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_listino_versione: DEFINER, la RLS non c''e''; non trovata o fuori perimetro E_VENDITE_LISTINO_VERSIONE_NOT_FOUND); prima cio'' che vieta, sul campo valido_al (il primo motivo di script.fn_check_versione_listino_chiudibile: E_LISTINO_VERSIONE_NON_CHIUDIBILE se non e'' ATTIVA, E_LISTINO_VERSIONE_FINE_NEL_PASSATO se la fine precede la data operativa); poi valido_al, con la porta aperta (GUC transazionale zeroerp.listino_versione_fine = id della versione: la onora vendite.trgfn_listini_versioni_guard_per_stato insieme al proprietario della tabella; senza, E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO). Fine prima dell''inizio: il guard comune delle date (E_DATA_AL_MINORE_DAL); due ATTIVA sovrapposte: l''esclusione. Lo stato non cambia: CHIUSA la scrive vendite.fn_chiudi_versioni_listino_scadute. Ritorna la versione, la fine di prima e quella di adesso. Prende il posto del PATCH di valido_al del backend. Il permesso d''area resta al backend. SECURITY DEFINER con search_path bloccato; EXECUTE solo all''applicazione. Brief: brief-modello-documento-vendita §16.14 (C-2 = a, C-3) e §16.15 (C-4 = a, Tid 2026-10-29).';
```

</div>

---
{% include-markdown "signature-core.md" %}
