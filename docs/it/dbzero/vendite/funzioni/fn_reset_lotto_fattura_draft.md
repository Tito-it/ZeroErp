{% include-markdown "it/dbzero/vendite/manual/fn_reset_lotto_fattura_draft.md" %}
# ⚙️ Funzione `fn_reset_lotto_fattura_draft`

```sql
CREATE FUNCTION fn_reset_lotto_fattura_draft(p_lotto_id bigint, p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_reset_lotto_fattura_draft(p_lotto_id bigint, p_fattura_id bigint)
 RETURNS TABLE(updated_attivita integer, deleted_fatture integer, deleted_righe integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_tipo_lotto vendite.fatturazione_lotti.tipo_lotto%TYPE;
  v_stato_doc_fiscale_id vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
  v_lock_batch_id vendite.fatturazione_lotti.lock_batch_id%TYPE;
  v_draft_id config.stati_doc_fiscale.id%TYPE;
  v_is_linked boolean := false;
  v_updated_attivita integer := 0;
  v_deleted_fatture integer := 0;
  v_deleted_righe integer := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Reset tecnico di una singola fattura in lotto MASSIVO
  --   DRAFT, senza annullare il lotto.
  --
  -- Regole:
  --   - lotto deve esistere, tipo_lotto = MASSIVO
  --   - stato_doc_fiscale lotto = DRAFT
  --   - fattura deve appartenere al lotto ed essere DRAFT
  -- =========================================================

  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_reset_lotto_fattura_draft', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', p_fattura_id,
        'context', jsonb_build_object('detail','p_lotto_id obbligatorio')
      ),
      NULL::uuid,
      'p_lotto_id non puo'' essere NULL o <= 0'
    );
  END IF;

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_reset_lotto_fattura_draft', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', p_fattura_id,
        'context', jsonb_build_object('detail','p_fattura_id obbligatorio')
      ),
      NULL::uuid,
      'p_fattura_id non puo'' essere NULL o <= 0'
    );
  END IF;

  SELECT fl.tipo_lotto,
         fl.stato_doc_fiscale_id,
         fl.lock_batch_id
    INTO v_tipo_lotto, v_stato_doc_fiscale_id, v_lock_batch_id
    FROM vendite.fatturazione_lotti fl
   WHERE fl.id = p_lotto_id;

  IF v_tipo_lotto IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_reset_lotto_fattura_draft', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', p_fattura_id,
        'context', jsonb_build_object('detail','lotto non trovato', 'lotto_id', p_lotto_id)
      ),
      NULL::uuid,
       concat('Lotto non trovato: ', p_lotto_id)
    );
  END IF;

  IF v_tipo_lotto <> 'MASSIVO' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_reset_lotto_fattura_draft', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', p_fattura_id,
        'context', jsonb_build_object('detail','tipo lotto non ammesso', 'tipo_lotto', v_tipo_lotto)
      ),
      NULL::uuid,
      concat('Reset consentito solo per lotti MASSIVO, tipo lotto: ', v_tipo_lotto)
    );
  END IF;

  SELECT s.id
    INTO v_draft_id
    FROM config.stati_doc_fiscale s
   WHERE s.codice_interno = 'DRAFT'
     AND s.attivo IS TRUE
   LIMIT 1;

  IF v_draft_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_reset_lotto_fattura_draft', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', p_fattura_id,
        'context', jsonb_build_object('detail','stato DRAFT non configurato')
      ),
      NULL::uuid,
      'Stato DRAFT non trovato in config.stati_doc_fiscale'
    );
  END IF;

  IF v_stato_doc_fiscale_id IS DISTINCT FROM v_draft_id THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_reset_lotto_fattura_draft', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', p_fattura_id,
        'context', jsonb_build_object(
          'detail','lotto non in DRAFT',
          'stato_doc_fiscale_id', v_stato_doc_fiscale_id
        )
      ),
      NULL::uuid,
      concat('Reset consentito solo se il lotto e'' in DRAFT, stato attuale: '
      , v_stato_doc_fiscale_id)
    );
  END IF;

  SELECT EXISTS (
    SELECT 1
      FROM vendite.fatturazione_lotti_fatture lf
      JOIN vendite.fatture f
        ON f.id = lf.fattura_id
     WHERE lf.lotto_id = p_lotto_id
       AND lf.fattura_id = p_fattura_id
       AND f.stato_doc_fiscale_id = v_draft_id
  )
  INTO v_is_linked;

  IF COALESCE(v_is_linked, false) = false THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_reset_lotto_fattura_draft', 'E_GENERICO',
      jsonb_build_object(
        'scope','LOTTO',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', p_fattura_id,
        'context', jsonb_build_object(
          'detail','fattura non collegata o non DRAFT',
          'lotto_id', p_lotto_id,
          'fattura_id', p_fattura_id
        )
      ),
      NULL::uuid,
      'Fattura non collegata al lotto o non in DRAFT'
    );
  END IF;

  SELECT c.deleted_fatture, c.deleted_righe, c.updated_attivita
    INTO v_deleted_fatture, v_deleted_righe, v_updated_attivita
    FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[p_fattura_id], v_lock_batch_id) AS c;

  RETURN QUERY
  SELECT v_updated_attivita, v_deleted_fatture, v_deleted_righe;
END;
$function$

COMMENT ON FUNCTION vendite.fn_reset_lotto_fattura_draft(p_lotto_id bigint, p_fattura_id bigint)
IS 'Reset tecnico della singola fattura DRAFT in lotto MASSIVO senza annullare il lotto.';
```

---
{% include-markdown "signature-core.md" %}
