{% include-markdown "it/dbzero/vendite/manual/fn_cambia_stato_commessa.md" %}
# ⚙️ Funzione `fn_cambia_stato_commessa`

```sql
CREATE FUNCTION fn_cambia_stato_commessa(p_commessa_id bigint, p_stato character varying)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cambia_stato_commessa(p_commessa_id bigint, p_stato character varying)
 RETURNS TABLE(commessa_id bigint, stato_da character varying, stato_a character varying)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente      config.user_override_azioni.auth_user_id%TYPE;
    v_stato_da    vendite.stati_commessa.codice_interno%TYPE;
    v_stato_da_id vendite.commesse.stato_commessa_id%TYPE;
    v_stato_a_id  vendite.stati_commessa.id%TYPE;
BEGIN
    -- ==========================================================
    -- Scopo: il verbo di ogni cambio di stato manuale di una
    --   commessa (modello del documento: prima riga comune,
    --   scrittura comune). Matrice e condizioni dei passaggi le
    --   giudica il guard di transizione, all'UPDATE.
    -- Ritorna: commessa_id, stato_da, stato_a (codice_interno).
    -- rev 2026-10-26 (20261026-30, brief-modello-documento-
    --   vendita §14, C-4): sul verbo comune, DEFINER, senza p_user.
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_commessa',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_commessa_id', p_commessa_id),
            NULL::uuid, 'vendite.fn_cambia_stato_commessa',
            'p_commessa_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT c.stato_commessa_id, s.codice_interno
      INTO v_stato_da_id, v_stato_da
      FROM vendite.commesse c
      JOIN vendite.stati_commessa s ON s.id = c.stato_commessa_id
     WHERE c.id = p_commessa_id
       AND script.fn_scope_ef_whitelist_via_commessa(v_utente, c.id)
       FOR UPDATE OF c;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_commessa',
            'E_COMMESSA_NON_TROVATA', jsonb_build_object('p_commessa_id', p_commessa_id),
            NULL::uuid, p_commessa_id::text);
    END IF;

    -- 3. Lo stato chiesto: il codice di uno stato attivo.
    v_stato_a_id := script.fn_doc_stato_id('vendite.commesse'::regclass, p_stato);
    IF v_stato_a_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_commessa',
            'E_STATO_WORKFLOW_NON_TROVATO',
            jsonb_build_object('p_nuovo_stato', p_stato),
            NULL::uuid,
            COALESCE(p_stato, 'NULL'));
    END IF;

    -- 4. Prima riga comune: lo stato che ha gia', passaggio di
    --    processo, azione.
    PERFORM script.fn_guard_passaggio(v_utente, 'vendite.commesse'::regclass,
                                      v_stato_da_id, v_stato_a_id);

    -- 5. Lo stato, attraverso la porta. Il guard di transizione
    --    giudica matrice e condizioni; il guard dell'annullo i
    --    legami.
    PERFORM script.fn_doc_scrivi_stato('vendite.commesse'::regclass,
                                       p_commessa_id, v_stato_a_id);

    RETURN QUERY SELECT p_commessa_id, v_stato_da, p_stato;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cambia_stato_commessa(p_commessa_id bigint, p_stato character varying)
IS 'VERBO di ogni cambio di stato manuale di una commessa (modello del documento, brief-modello-documento-vendita §14). Permesso: dalla riga del passaggio (vendite.transizioni_stati_commessa.azione_processo_codename: cambia_stato_commessa su «rendi pronta», «riapri», «chiudi» e sull''annullo di una commessa non in bozza) con script.fn_guard_passaggio, prima di ogni scrittura (lo stato che la commessa ha gia'': E_DOC_GIA_NELLO_STATO; un passaggio di processo chiesto a mano: E_DOC_PASSAGGIO_DI_PROCESSO); l''annullo della bozza al permesso sul documento, che controlla il backend. SECURITY DEFINER con search_path bloccato: la testata si prende FOR UPDATE col predicato della policy nella WHERE (script.fn_scope_ef_whitelist_via_commessa; fuori perimetro E_COMMESSA_NON_TROVATA, no-leak). Lo stato chiesto per codice_interno (script.fn_doc_stato_id; nessuno stato attivo: E_STATO_WORKFLOW_NON_TROVATO). Lo stato lo scrive script.fn_doc_scrivi_stato attraverso la porta (script.trgfn_doc_stato_solo_dal_verbo), e il guard di transizione (vendite.trgfn_commesse_guard_transizione) giudica matrice (E_COMMESSA_STATO_TRANSIZIONE_INVALIDA) e condizioni. L''annullo con legami passa da vendite.fn_annulla_commessa, il passaggio a pronta della push da vendite.fn_commessa_proietta_stato_emittibile. Ritorna commessa_id, stato_da, stato_a (codice_interno). EXECUTE solo all''applicazione. rev 2026-10-26 (20261026-30): firma senza p_user (C-4): prima (bigint, varchar, text), INVOKER, con un UPDATE suo. Brief: brief-modello-documento-vendita §14 (C-1, C-4, Tid 2026-10-26).';
```

</div>

---
{% include-markdown "signature-core.md" %}
