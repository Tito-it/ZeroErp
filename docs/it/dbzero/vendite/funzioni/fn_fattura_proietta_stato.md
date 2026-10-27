{% include-markdown "it/dbzero/vendite/manual/fn_fattura_proietta_stato.md" %}
# ⚙️ Funzione `fn_fattura_proietta_stato`

```sql
CREATE FUNCTION fn_fattura_proietta_stato(p_fattura_id bigint, p_stato_doc_fiscale_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_fattura_proietta_stato(p_fattura_id bigint, p_stato_doc_fiscale_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente   config.user_override_azioni.auth_user_id%TYPE;
    v_stato_da vendite.fatture.stato_doc_fiscale_id%TYPE;
    v_manuale  boolean;  -- la riga del passaggio e' manuale (script.fn_doc_passaggio)
BEGIN
    -- ==========================================================
    -- Scopo: lo stato fiscale di una fattura, scritto dalla
    --   pipeline che ne e' la causa (passaggio di processo,
    --   scrittura comune).
    -- rev 2026-10-27 (20261027-10, brief-modello-documento-
    --   vendita §15): nasce, al posto degli UPDATE della pipeline.
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    IF p_fattura_id IS NULL OR p_fattura_id <= 0 OR p_stato_doc_fiscale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_fattura_proietta_stato',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_fattura_id', p_fattura_id,
                               'p_stato_doc_fiscale_id', p_stato_doc_fiscale_id),
            NULL::uuid, 'vendite.fn_fattura_proietta_stato',
            'p_fattura_id (maggiore di zero) e p_stato_doc_fiscale_id obbligatori');
    END IF;

    -- La fattura FOR UPDATE, nel perimetro (predicato della policy).
    SELECT f.stato_doc_fiscale_id
      INTO v_stato_da
      FROM vendite.fatture f
     WHERE f.id = p_fattura_id
       AND script.fn_scope_ef_whitelist_via_fattura(v_utente, f.id)
       FOR UPDATE OF f;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_fattura_proietta_stato',
            'E_FATTURA_NON_TROVATA', jsonb_build_object('fattura_id', p_fattura_id),
            NULL::uuid, p_fattura_id::text);
    END IF;

    -- Lo stato che ha gia': niente da scrivere.
    IF v_stato_da IS NOT DISTINCT FROM p_stato_doc_fiscale_id THEN
        RETURN;
    END IF;

    -- Un passaggio manuale non e' di processo: non si scrive da qui.
    SELECT p.manuale INTO v_manuale
      FROM script.fn_doc_passaggio('vendite.fatture'::regclass,
                                   v_stato_da, p_stato_doc_fiscale_id) p;
    IF v_manuale IS TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_fattura_proietta_stato',
            'E_LOTTO_PARAMETRO_NON_COERENTE',
            jsonb_build_object('parametro', 'passaggio_manuale',
                               'fattura_id', p_fattura_id,
                               'stato_da_id', v_stato_da,
                               'stato_a_id', p_stato_doc_fiscale_id),
            NULL::uuid,
            concat('il passaggio ', v_stato_da, ' -> ', p_stato_doc_fiscale_id,
                   ' della fattura e'' manuale: non lo scrive la pipeline'),
            p_fattura_id::text);
    END IF;

    -- La scrittura comune, attraverso la porta: il guard di
    -- transizione della fattura giudica la matrice.
    PERFORM script.fn_doc_scrivi_stato('vendite.fatture'::regclass,
                                       p_fattura_id, p_stato_doc_fiscale_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_fattura_proietta_stato(p_fattura_id bigint, p_stato_doc_fiscale_id bigint)
IS 'Il verbo della FATTURA (F-1, Q-F3): lo stato fiscale di una fattura, scritto dalla pipeline che ne e'' la causa. Oggi le righe della fattura in config.stati_doc_fiscale_transizioni (solo_fattura) sono tutte di processo, quindi il verbo e'' di processo: la sola scrittura comune (script.fn_doc_scrivi_stato, attraverso la porta), senza la prima riga. Regola: lo stato che la fattura ha gia'' = no-op; un passaggio la cui riga e'' manuale (script.fn_doc_passaggio) non si scrive da qui (E_LOTTO_PARAMETRO_NON_COERENTE, parametro passaggio_manuale): e'' di un verbo con la prima riga, che arrivera'' con l''esito SDI; il resto lo giudica il guard di transizione vendite.trgfn_fatture_guard_stato. Chiamanti: vendite.fn_sync_lotto_fatture_stato (la fattura segue il lotto), vendite.fn_numera_fattura_opz_emessa, vendite.fn_close_giornaliero_lotto. SECURITY DEFINER con search_path bloccato: la fattura FOR UPDATE col predicato della policy (script.fn_scope_ef_whitelist_via_fattura; fuori perimetro E_FATTURA_NON_TROVATA). EXECUTE solo all''applicazione. Brief: brief-modello-documento-vendita §15 (F-1, Q-F3, Tid 2026-10-27).';
```

</div>

---
{% include-markdown "signature-core.md" %}
