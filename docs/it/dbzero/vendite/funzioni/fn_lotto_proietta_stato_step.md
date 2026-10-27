{% include-markdown "it/dbzero/vendite/manual/fn_lotto_proietta_stato_step.md" %}
# ⚙️ Funzione `fn_lotto_proietta_stato_step`

```sql
CREATE FUNCTION fn_lotto_proietta_stato_step(p_lotto_id bigint, p_stato_doc_fiscale_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_lotto_proietta_stato_step(p_lotto_id bigint, p_stato_doc_fiscale_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente     config.user_override_azioni.auth_user_id%TYPE;
    v_stato_da   vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
    v_tipo_lotto vendite.fatturazione_lotti.tipo_lotto%TYPE;
BEGIN
    -- ==========================================================
    -- Scopo: lo stato fiscale del lotto allo step del giro della
    --   pipeline (passaggio di processo, scrittura comune).
    -- rev 2026-10-27 (20261027-09, brief-modello-documento-
    --   vendita §15): nasce, al posto dell'UPDATE del runner.
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    IF p_lotto_id IS NULL OR p_lotto_id <= 0 OR p_stato_doc_fiscale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_lotto_proietta_stato_step',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_lotto_id', p_lotto_id,
                               'p_stato_doc_fiscale_id', p_stato_doc_fiscale_id),
            NULL::uuid, 'vendite.fn_lotto_proietta_stato_step',
            'p_lotto_id (maggiore di zero) e p_stato_doc_fiscale_id obbligatori');
    END IF;

    -- Il lotto FOR UPDATE, nel perimetro (predicato della policy).
    SELECT l.stato_doc_fiscale_id, l.tipo_lotto
      INTO v_stato_da, v_tipo_lotto
      FROM vendite.fatturazione_lotti l
     WHERE l.id = p_lotto_id
       AND script.fn_scope_ef_whitelist_via_lotto(v_utente, l.id)
       FOR UPDATE OF l;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_lotto_proietta_stato_step',
            'E_LOTTO_NON_TROVATO', jsonb_build_object('lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::text);
    END IF;

    -- Lo stato che ha gia': niente da scrivere.
    IF v_stato_da IS NOT DISTINCT FROM p_stato_doc_fiscale_id THEN
        RETURN;
    END IF;

    -- Lo stato di uno step della pipeline del suo tipo, e non
    -- l'iniziale (il ritorno in bozza e' un verbo).
    IF NOT EXISTS (
           SELECT 1 FROM vendite.fatturazione_pipeline p
            WHERE p.attivo IS TRUE
              AND p.stato_doc_fiscale_id = p_stato_doc_fiscale_id
              AND p.tipo_lotto = v_tipo_lotto)
       OR EXISTS (
           SELECT 1 FROM config.stati_doc_fiscale s
            WHERE s.id = p_stato_doc_fiscale_id
              AND s.iniziale IS TRUE) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_lotto_proietta_stato_step',
            'E_LOTTO_PARAMETRO_NON_COERENTE',
            jsonb_build_object('parametro', 'stato_step',
                               'lotto_id', p_lotto_id,
                               'tipo_lotto', v_tipo_lotto,
                               'stato_da_id', v_stato_da,
                               'stato_a_id', p_stato_doc_fiscale_id),
            NULL::uuid,
            concat('lo stato ', p_stato_doc_fiscale_id,
                   ' non e'' uno step della pipeline ', v_tipo_lotto,
                   ' (o e'' lo stato iniziale)'),
            p_lotto_id::text);
    END IF;

    -- La scrittura comune, attraverso la porta: il guard di
    -- transizione giudica la matrice e il fermo.
    PERFORM script.fn_doc_scrivi_stato('vendite.fatturazione_lotti'::regclass,
                                       p_lotto_id, p_stato_doc_fiscale_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_lotto_proietta_stato_step(p_lotto_id bigint, p_stato_doc_fiscale_id bigint)
IS 'Verbo di PROCESSO dello stato fiscale del lotto: il giro della pipeline porta il lotto nello stato del suo step (il runner del backend lo chiama negli stessi punti in cui faceva l''UPDATE, F-4). Passaggio di processo: lo scrive la causa, con la sola scrittura comune (script.fn_doc_scrivi_stato, attraverso la porta), senza la prima riga del verbo; il permesso di «numera» si chiede quando l''operatore preme (P-2). Regola: lo stato che il lotto ha gia'' = no-op; altrimenti deve essere lo stato di uno step attivo di vendite.fatturazione_pipeline per il tipo del lotto, e non lo stato iniziale del vocabolario (il ritorno in bozza e'' vendite.fn_riporta_lotto_a_draft), o E_LOTTO_PARAMETRO_NON_COERENTE (parametro stato_step). Matrice e fermo li giudica il guard di transizione vendite.trgfn_fatturazione_lotti_guard_stato. SECURITY DEFINER con search_path bloccato: il lotto FOR UPDATE col predicato della policy (script.fn_scope_ef_whitelist_via_lotto; fuori perimetro E_LOTTO_NON_TROVATO). Le fatture del lotto le allinea vendite.fn_sync_lotto_fatture_stato. EXECUTE solo all''applicazione. Brief: brief-modello-documento-vendita §15 (F-4, P-2, Tid 2026-10-27).';
```

</div>

---
{% include-markdown "signature-core.md" %}
