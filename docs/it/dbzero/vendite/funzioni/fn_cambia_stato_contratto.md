{% include-markdown "it/dbzero/vendite/manual/fn_cambia_stato_contratto.md" %}
# ⚙️ Funzione `fn_cambia_stato_contratto`

```sql
CREATE FUNCTION fn_cambia_stato_contratto(p_contratto_id bigint, p_stato character varying)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cambia_stato_contratto(p_contratto_id bigint, p_stato character varying)
 RETURNS TABLE(contratto_id bigint, stato_precedente character varying, stato_nuovo character varying)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente      config.user_override_azioni.auth_user_id%TYPE;
    v_stato_da    config.stati_doc_contratti.codice_interno%TYPE;
    v_stato_da_id vendite.contratti.stato_doc_contratto_id%TYPE;
    v_stato_a_id  config.stati_doc_contratti.id%TYPE;
BEGIN
    -- ==========================================================
    -- Scopo: il verbo di ogni cambio di stato manuale di un
    --   contratto (modello del documento: prima riga comune,
    --   scrittura comune). Matrice e condizioni dei passaggi le
    --   giudica il guard di transizione, all'UPDATE.
    -- Ritorna: contratto_id, stato_precedente, stato_nuovo
    --   (codice_interno).
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_contratto_id IS NULL OR p_contratto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_contratto',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_contratto_id', p_contratto_id),
            NULL::uuid, 'vendite.fn_cambia_stato_contratto',
            'p_contratto_id (obbligatorio, maggiore di zero)');
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
            'vendite', 'vendite.fn_cambia_stato_contratto',
            'E_CONTRATTO_NON_TROVATO', jsonb_build_object('id', p_contratto_id), NULL::uuid,
            p_contratto_id::text);
    END IF;

    -- 3. Lo stato chiesto: il codice di uno stato attivo.
    v_stato_a_id := script.fn_doc_stato_id('vendite.contratti'::regclass, p_stato);
    IF v_stato_a_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_contratto',
            'E_STATO_WORKFLOW_NON_TROVATO',
            jsonb_build_object('codice', p_stato),
            NULL::uuid,
            COALESCE(p_stato, 'NULL'));
    END IF;

    -- 4. Prima riga comune: lo stato che ha gia', passaggio di
    --    processo, azione.
    PERFORM script.fn_guard_passaggio(v_utente, 'vendite.contratti'::regclass,
                                      v_stato_da_id, v_stato_a_id);

    -- 5. Lo stato, attraverso la porta. Il guard di transizione
    --    giudica matrice, prezzi, indirizzi, righe, sovrapposto
    --    all'attivazione e la data arrivata della cessazione.
    PERFORM script.fn_doc_scrivi_stato('vendite.contratti'::regclass,
                                       p_contratto_id, v_stato_a_id);

    RETURN QUERY SELECT p_contratto_id, v_stato_da, p_stato;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cambia_stato_contratto(p_contratto_id bigint, p_stato character varying)
IS 'VERBO di ogni cambio di stato manuale di un contratto (modello del documento, brief-modello-documento-vendita §11). Permesso: dalla riga del passaggio (config.transizioni_stati_contratti.azione_processo_codename: emetti_contratto su DRAFT -> ATTIVO e ATTIVO -> CESSATO) con script.fn_guard_passaggio, prima di ogni scrittura (lo stato che il contratto ha gia'': E_DOC_GIA_NELLO_STATO); l''annullo della bozza al permesso sul documento, che controlla il backend. SECURITY DEFINER con search_path bloccato: la testata si prende FOR UPDATE col predicato della policy nella WHERE (script.fn_scope_ef_whitelist_via_contratto; fuori perimetro E_CONTRATTO_NON_TROVATO, no-leak). Lo stato chiesto per codice_interno (script.fn_doc_stato_id; nessuno stato attivo: E_STATO_WORKFLOW_NON_TROVATO). Lo stato lo scrive script.fn_doc_scrivi_stato attraverso la porta (script.trgfn_doc_stato_solo_dal_verbo), e il guard di transizione (vendite.trgfn_contratti_guard_transizione_stato) giudica matrice (E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA) e condizioni: prezzi, indirizzi, righe e sovrapposto all''attivazione; alla cessazione la data di fine valorizzata e arrivata. La cessazione con la data passa da vendite.fn_cessa_contratto, l''annullo con legami da vendite.fn_annulla_contratto: tutti e due finiscono qui o nella scrittura comune. Ritorna contratto_id, stato_precedente, stato_nuovo (codice_interno). EXECUTE solo all''applicazione. Brief: brief-modello-documento-vendita §11 (Y-1, Tid 2026-10-26).';
```

</div>

---
{% include-markdown "signature-core.md" %}
