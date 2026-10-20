{% include-markdown "it/dbzero/vendite/manual/fn_set_documento_canale_stato.md" %}
# ⚙️ Funzione `fn_set_documento_canale_stato`

```sql
CREATE FUNCTION fn_set_documento_canale_stato(p_sorgente_tipo_id bigint, p_sorgente_uid text, p_canale_codice character varying, p_stato_canale character varying, p_target_sorgente_tipo_id bigint, p_target_sorgente_uid text, p_motivo_blocco text, p_meta jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_set_documento_canale_stato(p_sorgente_tipo_id bigint, p_sorgente_uid text, p_canale_codice character varying, p_stato_canale character varying, p_target_sorgente_tipo_id bigint DEFAULT NULL::bigint, p_target_sorgente_uid text DEFAULT NULL::text, p_motivo_blocco text DEFAULT NULL::text, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_id vendite.documenti_fatturazione_canali.id%TYPE;
  v_canale vendite.documenti_fatturazione_canali.canale_codice%TYPE;
  v_stato vendite.documenti_fatturazione_canali.stato_canale%TYPE;
  v_uid vendite.documenti_fatturazione_canali.sorgente_uid%TYPE;
  v_target_uid vendite.documenti_fatturazione_canali.target_sorgente_uid%TYPE;
  v_canale_source_id config.sorgenti.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Impostare lo stato canale fatturabile di una sorgente
  --   documento in modo idempotente e uniforme.
  --
  -- Regole:
  --   - APERTO blocca automaticamente altri canali APERTO
  --   - BLOCCATO richiede motivo_blocco
  --   - target_sorgente_* deve essere valorizzato a coppia
  --
  -- NOTE codice_interno (rev 2026-06-28, analisi-hardcoded-codice §3a #14):
  --   il canale (v_canale) e' risolto in config.sorgenti per
  --   codice_interno (immutabile), non per codice. 'DIRETTO' = sentinel.
  -- =========================================================
  IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_set_documento_canale_stato','E_GENERICO',
      jsonb_build_object('scope','CANALI_FATTURAZIONE','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','sorgente_tipo_id obbligatorio','sorgente_tipo_id',p_sorgente_tipo_id)),
      NULL::uuid,
      'sorgente_tipo_id obbligatorio'
    );
  END IF;

  v_uid := NULLIF(btrim(p_sorgente_uid), '');
  IF v_uid IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_set_documento_canale_stato','E_GENERICO',
      jsonb_build_object('scope','CANALI_FATTURAZIONE','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','sorgente_uid obbligatoria')),
      NULL::uuid,
      'sorgente_uid obbligatoria'
    );
  END IF;

  v_canale := upper(COALESCE(NULLIF(btrim(p_canale_codice), ''), ''));
  IF v_canale = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_set_documento_canale_stato','E_GENERICO',
      jsonb_build_object('scope','CANALI_FATTURAZIONE','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','canale_codice non valido','canale_codice',v_canale)),
      NULL::uuid,
      'canale_codice non valido'
    );
  END IF;

  -- Canale = codice_interno sorgente configurata (attiva) o eccezione DIRETTO.
  IF v_canale <> 'DIRETTO' THEN
    SELECT s.id
    INTO v_canale_source_id
    FROM config.sorgenti s
    WHERE s.codice_interno = v_canale
      AND s.attivo IS TRUE
    LIMIT 1;

    IF v_canale_source_id IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite','fn_set_documento_canale_stato','E_GENERICO',
        jsonb_build_object(
          'scope','CANALI_FATTURAZIONE','severity','C','code','E_GENERICO',
          'lotto_id',NULL,'fattura_id',NULL,
          'context',jsonb_build_object(
            'detail','canale_codice non censito in config.sorgenti attive',
            'canale_codice',v_canale
          )
        ),
        NULL::uuid,
        concat('canale_codice non censito in config.sorgenti attive: ', v_canale)
      );
    END IF;
  END IF;

  v_stato := upper(COALESCE(NULLIF(btrim(p_stato_canale), ''), ''));
  IF v_stato NOT IN ('APERTO', 'CONSUMATO', 'BLOCCATO') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_set_documento_canale_stato','E_GENERICO',
      jsonb_build_object('scope','CANALI_FATTURAZIONE','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','stato_canale non valido','stato_canale',v_stato)),
      NULL::uuid,
      'stato_canale non valido'
    );
  END IF;

  IF v_stato = 'BLOCCATO' AND (p_motivo_blocco IS NULL OR btrim(p_motivo_blocco) = '') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_set_documento_canale_stato','E_GENERICO',
      jsonb_build_object('scope','CANALI_FATTURAZIONE','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','motivo_blocco obbligatorio per stato BLOCCATO')),
      NULL::uuid,
      'motivo_blocco obbligatorio per stato BLOCCATO'
    );
  END IF;

  IF p_target_sorgente_tipo_id IS NOT NULL AND p_target_sorgente_tipo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_set_documento_canale_stato','E_GENERICO',
      jsonb_build_object('scope','CANALI_FATTURAZIONE','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','target_sorgente_tipo_id non valido','target_sorgente_tipo_id',p_target_sorgente_tipo_id)),
      NULL::uuid,
      'target_sorgente_tipo_id non valido'
    );
  END IF;

  v_target_uid := NULLIF(btrim(p_target_sorgente_uid), '');
  IF (p_target_sorgente_tipo_id IS NULL AND v_target_uid IS NOT NULL)
     OR (p_target_sorgente_tipo_id IS NOT NULL AND v_target_uid IS NULL) THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_set_documento_canale_stato','E_GENERICO',
      jsonb_build_object('scope','CANALI_FATTURAZIONE','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','target_sorgente_* deve essere valorizzato a coppia')),
      NULL::uuid,
      'target_sorgente_* deve essere valorizzato a coppia'
    );
  END IF;

  -- Se apro un canale, chiudo/blocco eventuale altro canale aperto.
  IF v_stato = 'APERTO' THEN
    UPDATE vendite.documenti_fatturazione_canali c
    SET stato_canale = 'BLOCCATO',
        motivo_blocco = concat('AUTO_BLOCCO_APERTURA_', v_canale),
        data_update = now(),
        user_update = current_user
    WHERE c.sorgente_tipo_id = p_sorgente_tipo_id
      AND c.sorgente_uid = v_uid
      AND c.canale_codice <> v_canale
      AND c.stato_canale = 'APERTO';
  END IF;

  INSERT INTO vendite.documenti_fatturazione_canali (
    sorgente_tipo_id,
    sorgente_uid,
    canale_codice,
    stato_canale,
    target_sorgente_tipo_id,
    target_sorgente_uid,
    motivo_blocco,
    meta
  )
  VALUES (
    p_sorgente_tipo_id,
    v_uid,
    v_canale,
    v_stato,
    p_target_sorgente_tipo_id,
    v_target_uid,
    NULLIF(btrim(p_motivo_blocco), ''),
    COALESCE(p_meta, '{}'::jsonb)
  )
  ON CONFLICT (sorgente_tipo_id, sorgente_uid, canale_codice) DO UPDATE
  SET stato_canale = EXCLUDED.stato_canale,
      target_sorgente_tipo_id = EXCLUDED.target_sorgente_tipo_id,
      target_sorgente_uid = EXCLUDED.target_sorgente_uid,
      motivo_blocco = EXCLUDED.motivo_blocco,
      meta = COALESCE(vendite.documenti_fatturazione_canali.meta, '{}'::jsonb) || COALESCE(EXCLUDED.meta, '{}'::jsonb),
      data_update = now(),
      user_update = current_user
  RETURNING id INTO v_id;

  RETURN v_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_set_documento_canale_stato(p_sorgente_tipo_id bigint, p_sorgente_uid text, p_canale_codice character varying, p_stato_canale character varying, p_target_sorgente_tipo_id bigint, p_target_sorgente_uid text, p_motivo_blocco text, p_meta jsonb)
IS 'Imposta stato canale (APERTO/CONSUMATO/BLOCCATO) per sorgente documento con upsert idempotente; APERTO blocca altri canali aperti. rev 2026-06-28: canale risolto per codice_interno (analisi-hardcoded-codice §3a #14).';
```

</div>

---
{% include-markdown "signature-core.md" %}
