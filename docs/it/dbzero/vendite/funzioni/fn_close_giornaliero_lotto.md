{% include-markdown "it/dbzero/vendite/manual/fn_close_giornaliero_lotto.md" %}
# ⚙️ Funzione `fn_close_giornaliero_lotto`

```sql
CREATE FUNCTION fn_close_giornaliero_lotto(p_lotto_id bigint, p_inviata_stato_doc_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_close_giornaliero_lotto(p_lotto_id bigint, p_inviata_stato_doc_fiscale_id bigint)
 RETURNS TABLE(updated_lotti integer, updated_fatture integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_updated_lotti integer := 0;
  v_updated_fatture integer := 0;
  v_tipo_lotto vendite.fatturazione_lotti.tipo_lotto%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Chiudere un lotto giornaliero e portare le fatture
  --   collegate allo stato documentale INVIATA.
  --
  -- Regole:
  --   - parametri obbligatori
  --   - lotto deve esistere ed essere di tipo GIORNALIERO
  --   - stato_operativo del lotto -> CHIUSO
  --   - stato_doc_fiscale su lotto e fatture -> valore passato
  -- =========================================================

  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_close_giornaliero_lotto', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail','p_lotto_id obbligatorio')
      ),
      NULL::uuid,
      'p_lotto_id non puo'' essere NULL'
    );
  END IF;

  IF p_inviata_stato_doc_fiscale_id IS NULL OR p_inviata_stato_doc_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_close_giornaliero_lotto', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail','p_inviata_stato_doc_fiscale_id obbligatorio')
      ),
      NULL::uuid,
      'p_inviata_stato_doc_fiscale_id non puo'' essere NULL'
    );
  END IF;

  SELECT fl.tipo_lotto
    INTO v_tipo_lotto
    FROM vendite.fatturazione_lotti fl
   WHERE fl.id = p_lotto_id;

  IF v_tipo_lotto IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_close_giornaliero_lotto', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail','Lotto non trovato', 'lotto_id', p_lotto_id)
      ),
      NULL::uuid,
      concat('Lotto non trovato: ', p_lotto_id::text)
    );
  END IF;

  IF v_tipo_lotto <> 'GIORNALIERO' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_close_giornaliero_lotto', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object(
          'detail','Lotto non giornaliero',
          'lotto_id', p_lotto_id,
          'tipo_lotto', v_tipo_lotto
        )
      ),
      NULL::uuid,
      concat('Lotto ', p_lotto_id::text, ' non e'' di tipo GIORNALIERO')
    );
  END IF;

  UPDATE vendite.fatturazione_lotti
     SET stato_operativo = 'CHIUSO',
         stato_doc_fiscale_id = p_inviata_stato_doc_fiscale_id,
         data_update = now(),
         user_update = current_user
   WHERE id = p_lotto_id;

  GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

  UPDATE vendite.fatture f
     SET stato_doc_fiscale_id = p_inviata_stato_doc_fiscale_id,
         data_update = now(),
         user_update = current_user
    FROM vendite.fatturazione_lotti_fatture lf
   WHERE lf.lotto_id = p_lotto_id
     AND lf.fattura_id = f.id;

  GET DIAGNOSTICS v_updated_fatture = ROW_COUNT;

  RETURN QUERY
  SELECT v_updated_lotti, v_updated_fatture;
END;
$function$

COMMENT ON FUNCTION vendite.fn_close_giornaliero_lotto(p_lotto_id bigint, p_inviata_stato_doc_fiscale_id bigint)
IS 'Chiude un lotto giornaliero e allinea allo stato target tutte le fatture collegate al lotto.';
```

---
{% include-markdown "signature-core.md" %}
