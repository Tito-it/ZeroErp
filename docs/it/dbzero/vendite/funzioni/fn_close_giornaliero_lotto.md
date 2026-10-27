{% include-markdown "it/dbzero/vendite/manual/fn_close_giornaliero_lotto.md" %}
# ⚙️ Funzione `fn_close_giornaliero_lotto`

```sql
CREATE FUNCTION fn_close_giornaliero_lotto(p_lotto_id bigint, p_inviata_stato_doc_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_close_giornaliero_lotto(p_lotto_id bigint, p_inviata_stato_doc_fiscale_id bigint)
 RETURNS TABLE(updated_lotti integer, updated_fatture integer)
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-27 (20261027-13, brief-modello-documento-vendita §15): lo
--   stato del lotto lo scrive il verbo di processo del lotto
--   (vendite.fn_lotto_proietta_stato_step), quello delle fatture il verbo
--   della fattura (vendite.fn_fattura_proietta_stato), una per una: la
--   porta non lascia passare gli UPDATE. I due conteggi restano quelli di
--   prima (il lotto chiuso; tutte le fatture del lotto).
DECLARE
    v_updated_lotti   INTEGER := 0;
    v_updated_fatture INTEGER := 0;
    v_tipo_lotto      vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_fattura_id      vendite.fatture.id%TYPE;
BEGIN
    -- Guard: parametri obbligatori
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_close_giornaliero_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0'
        );
    END IF;

    IF p_inviata_stato_doc_fiscale_id IS NULL OR p_inviata_stato_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_close_giornaliero_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_inviata_stato_doc_fiscale_id', 'valore', p_inviata_stato_doc_fiscale_id),
            NULL::uuid, 'p_inviata_stato_doc_fiscale_id obbligatorio e > 0'
        );
    END IF;

    -- Recupera tipo lotto
    SELECT fl.tipo_lotto
      INTO v_tipo_lotto
      FROM vendite.fatturazione_lotti fl
     WHERE fl.id = p_lotto_id;

    IF v_tipo_lotto IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_close_giornaliero_lotto', 'E_VALORE_MANCANTE',
            jsonb_build_object('lotto_id', p_lotto_id),
            NULL::uuid, concat('lotto_id ', p_lotto_id)
        );
    END IF;

    -- Guard: solo lotti giornalieri
    IF v_tipo_lotto <> 'GIORNALIERO' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_close_giornaliero_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'tipo_lotto',
                'valore', v_tipo_lotto,
                'lotto_id', p_lotto_id
            ),
            NULL::uuid,
            concat('Lotto ', p_lotto_id, ' tipo=', v_tipo_lotto, ' (richiesto GIORNALIERO)')
        );
    END IF;

    -- Chiudi lotto: lo stato operativo qui, lo stato fiscale dal verbo di
    -- processo del lotto (INVIATA e' uno step della pipeline giornaliera).
    UPDATE vendite.fatturazione_lotti
       SET stato_operativo = 'CHIUSO',
           data_update = now(),
           user_update = current_user
     WHERE id = p_lotto_id;

    GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

    PERFORM vendite.fn_lotto_proietta_stato_step(p_lotto_id, p_inviata_stato_doc_fiscale_id);

    -- Allinea stato fatture, dal verbo della fattura (no-op su chi c'e' gia').
    FOR v_fattura_id IN
        SELECT lf.fattura_id
          FROM vendite.fatturazione_lotti_fatture lf
         WHERE lf.lotto_id = p_lotto_id
         ORDER BY lf.fattura_id
    LOOP
        PERFORM vendite.fn_fattura_proietta_stato(v_fattura_id, p_inviata_stato_doc_fiscale_id);
        v_updated_fatture := v_updated_fatture + 1;
    END LOOP;

    RETURN QUERY SELECT v_updated_lotti, v_updated_fatture;
END;
$function$

COMMENT ON FUNCTION vendite.fn_close_giornaliero_lotto(p_lotto_id bigint, p_inviata_stato_doc_fiscale_id bigint)
IS 'Chiude lotto giornaliero e allinea stato doc fiscale su tutte le fatture collegate. rev 2026-10-27 (20261027-13, brief-modello-documento-vendita §15): lo stato fiscale del lotto lo scrive il verbo di processo del lotto (vendite.fn_lotto_proietta_stato_step: INVIATA e'' uno step della pipeline giornaliera), quello di ogni fattura del lotto il verbo della fattura (vendite.fn_fattura_proietta_stato, no-op su chi e'' gia'' nello stato): le porte non lasciano passare gli UPDATE. Lo stato operativo CHIUSO resta un UPDATE. updated_lotti e updated_fatture contano come prima (il lotto; tutte le fatture del lotto).';
```

</div>

---
{% include-markdown "signature-core.md" %}
