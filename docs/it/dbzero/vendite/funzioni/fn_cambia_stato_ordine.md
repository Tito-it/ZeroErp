{% include-markdown "it/dbzero/vendite/manual/fn_cambia_stato_ordine.md" %}
# ⚙️ Funzione `fn_cambia_stato_ordine`

```sql
CREATE FUNCTION fn_cambia_stato_ordine(p_ordine_id bigint, p_stato character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cambia_stato_ordine(p_ordine_id bigint, p_stato character varying)
 RETURNS TABLE(ordine_id bigint, stato_precedente character varying, stato_nuovo character varying)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente      config.user_override_azioni.auth_user_id%TYPE;
    v_stato_da    config.stati_doc_ordini.codice_interno%TYPE;
    v_stato_da_id vendite.ordini.stato_doc_ordine_id%TYPE;
    v_stato_a_id  config.stati_doc_ordini.id%TYPE;
BEGIN
    -- ==========================================================
    -- Scopo: il verbo di ogni cambio di stato manuale di un
    --   ordine (modello del documento: prima riga comune,
    --   scrittura comune). Matrice, righe, aliquote, prezzi e
    --   annullabilita' li giudica il guard di transizione,
    --   all'UPDATE.
    -- Ritorna: ordine_id, stato_precedente, stato_nuovo
    --   (codice_interno).
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_ordine',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('param', 'p_ordine_id', 'value', p_ordine_id),
            NULL::uuid,
            'p_ordine_id = ' || COALESCE(p_ordine_id::text, 'NULL'));
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT o.stato_doc_ordine_id, s.codice_interno
      INTO v_stato_da_id, v_stato_da
      FROM vendite.ordini o
      JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
     WHERE o.id = p_ordine_id
       AND script.fn_scope_ef_whitelist_via_ordine(v_utente, o.id)
       FOR UPDATE OF o;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_ordine',
            'E_ORD_NOT_FOUND', jsonb_build_object('id', p_ordine_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 3. Lo stato chiesto: il codice di uno stato attivo.
    v_stato_a_id := script.fn_doc_stato_id('vendite.ordini'::regclass, p_stato);
    IF v_stato_a_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_ordine',
            'E_STATO_WORKFLOW_NON_TROVATO',
            jsonb_build_object('codice', p_stato),
            NULL::uuid,
            COALESCE(p_stato, 'NULL'));
    END IF;

    -- 4. Prima riga comune: passaggio di processo, azione.
    PERFORM script.fn_guard_passaggio(v_utente, 'vendite.ordini'::regclass,
                                      v_stato_da_id, v_stato_a_id);

    -- 5. Lo stato, attraverso la porta. Il guard di transizione
    --    giudica matrice, righe attive alla conferma, aliquote,
    --    prezzi autorizzati e annullabilita'.
    PERFORM script.fn_doc_scrivi_stato('vendite.ordini'::regclass,
                                       p_ordine_id, v_stato_a_id);

    RETURN QUERY SELECT p_ordine_id, v_stato_da, p_stato;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cambia_stato_ordine(p_ordine_id bigint, p_stato character varying)
IS 'VERBO di ogni cambio di stato manuale di un ordine (modello del documento, brief-modello-documento-vendita §9). Permesso: dalla riga del passaggio (config.transizioni_stati_ordini.azione_processo_codename: emetti_ordine su DRAFT -> CONFERMATO e CONFERMATO -> ANNULLATO) con script.fn_guard_passaggio, prima di ogni scrittura; un passaggio di processo (l''evasione, CONFERMATO <-> PARZIALMENTE_EVASO <-> EVASO, che scrive vendite.fn_ordine_proietta_stato_evasione) chiesto qui: E_DOC_PASSAGGIO_DI_PROCESSO; gli altri passaggi (l''annullo della bozza) al permesso sul documento, che controlla il backend. SECURITY DEFINER con search_path bloccato: la testata si prende FOR UPDATE col predicato della policy nella WHERE (script.fn_scope_ef_whitelist_via_ordine; fuori perimetro E_ORD_NOT_FOUND, no-leak). Lo stato chiesto per codice_interno (script.fn_doc_stato_id; nessuno stato attivo: E_STATO_WORKFLOW_NON_TROVATO). Lo stato lo scrive script.fn_doc_scrivi_stato attraverso la porta (script.trgfn_doc_stato_solo_dal_verbo), e il guard di transizione (vendite.trgfn_ordini_guard_transizione) giudica matrice (E_ORDINE_TRANSIZIONE_NON_AMMESSA), righe attive alla conferma, aliquote, prezzi autorizzati e annullabilita''. L''annullo con legami passa da vendite.fn_annulla_ordine, che ritira i legami e poi chiama questo verbo. Ritorna ordine_id, stato_precedente, stato_nuovo (codice_interno). EXECUTE solo all''applicazione. Brief: brief-modello-documento-vendita §9 (Z-1, Tid 2026-10-25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
