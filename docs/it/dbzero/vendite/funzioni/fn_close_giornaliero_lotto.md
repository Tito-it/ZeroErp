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
DECLARE
    v_updated_lotti   INTEGER := 0;
    v_updated_fatture INTEGER := 0;
    v_tipo_lotto      vendite.fatturazione_lotti.tipo_lotto%TYPE;
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

    -- Chiudi lotto
    UPDATE vendite.fatturazione_lotti
       SET stato_operativo = 'CHIUSO',
           stato_doc_fiscale_id = p_inviata_stato_doc_fiscale_id,
           data_update = now(),
           user_update = current_user
     WHERE id = p_lotto_id;

    GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

    -- Allinea stato fatture
    UPDATE vendite.fatture f
       SET stato_doc_fiscale_id = p_inviata_stato_doc_fiscale_id,
           data_update = now(),
           user_update = current_user
      FROM vendite.fatturazione_lotti_fatture lf
     WHERE lf.lotto_id = p_lotto_id
       AND lf.fattura_id = f.id;

    GET DIAGNOSTICS v_updated_fatture = ROW_COUNT;

    RETURN QUERY SELECT v_updated_lotti, v_updated_fatture;
END;
$function$

COMMENT ON FUNCTION vendite.fn_close_giornaliero_lotto(p_lotto_id bigint, p_inviata_stato_doc_fiscale_id bigint)
IS 'Chiude lotto giornaliero e allinea stato doc fiscale su tutte le fatture collegate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
