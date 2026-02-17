{% include-markdown "it/dbzero/vendite/manual/fn_sync_lotto_fatture_stato.md" %}
# ⚙️ Funzione `fn_sync_lotto_fatture_stato`

```sql
CREATE FUNCTION fn_sync_lotto_fatture_stato(p_lotto_id bigint, p_target_stato_doc_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_lotto_fatture_stato(p_lotto_id bigint, p_target_stato_doc_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_tipo_lotto vendite.fatturazione_lotti.tipo_lotto%TYPE;
  v_stato_lotto config.stati_doc_fiscale.id%TYPE;
  v_target config.stati_doc_fiscale.id%TYPE;
  v_inviata_id config.stati_doc_fiscale.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Allinea lo stato delle fatture collegate al lotto.
  --
  -- Regole:
  --   - p_lotto_id obbligatorio
  --   - se p_target_stato_doc_fiscale_id NULL usa stato_doc_fiscale lotto
  --   - lotto giornaliero: a INVIATA -> chiude stato_operativo
  -- =========================================================

  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_sync_lotto_fatture_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto_id obbligatorio')),
      NULL::uuid, 'lotto_id obbligatorio'
    );
  END IF;

  IF p_target_stato_doc_fiscale_id IS NOT NULL AND p_target_stato_doc_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_sync_lotto_fatture_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','target stato_doc_fiscale non valido', 'stato_doc_fiscale_id', p_target_stato_doc_fiscale_id)),
      NULL::uuid, 'stato_doc_fiscale target non valido'
    );
  END IF;

  SELECT tipo_lotto, stato_doc_fiscale_id
    INTO v_tipo_lotto, v_stato_lotto
    FROM vendite.fatturazione_lotti
   WHERE id = p_lotto_id
   FOR UPDATE;

  IF v_stato_lotto IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_sync_lotto_fatture_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto non trovato', 'lotto_id', p_lotto_id)),
      NULL::uuid, concat('lotto non trovato: ', p_lotto_id)
    );
  END IF;

  v_target := COALESCE(p_target_stato_doc_fiscale_id, v_stato_lotto);

  IF v_target IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_sync_lotto_fatture_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','stato_doc_fiscale target obbligatorio')),
      NULL::uuid, 
      concat('stato_doc_fiscale target obbligatorio per lotto: ', p_lotto_id)
    );
  END IF;

  UPDATE vendite.fatture f
     SET stato_doc_fiscale_id = v_target,
         data_update = now(),
         user_update = current_user
    FROM vendite.fatturazione_lotti_fatture lf
   WHERE lf.lotto_id = p_lotto_id
     AND COALESCE(lf.esclusa, false) IS FALSE
     AND lf.fattura_id = f.id
     AND f.stato_doc_fiscale_id IS DISTINCT FROM v_target;

  IF v_tipo_lotto = 'GIORNALIERO' THEN
    SELECT id
      INTO v_inviata_id
      FROM config.stati_doc_fiscale
     WHERE codice_interno = 'INVIATA'
       AND attivo IS TRUE
     ORDER BY ordine
     LIMIT 1;

    IF v_inviata_id IS NOT NULL AND v_target = v_inviata_id THEN
      UPDATE vendite.fatturazione_lotti
         SET stato_operativo = 'CHIUSO',
             data_update = now(),
             user_update = current_user
       WHERE id = p_lotto_id;
    END IF;
  END IF;
END
$function$

COMMENT ON FUNCTION vendite.fn_sync_lotto_fatture_stato(p_lotto_id bigint, p_target_stato_doc_fiscale_id bigint)
IS 'Allinea stato fatture collegate al lotto (opzionale target).';
```

---
{% include-markdown "signature-core.md" %}
