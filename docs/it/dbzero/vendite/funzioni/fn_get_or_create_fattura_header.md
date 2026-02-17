{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_fattura_header.md" %}
# ⚙️ Funzione `fn_get_or_create_fattura_header`

```sql
CREATE FUNCTION fn_get_or_create_fattura_header(p_lotto_id bigint, p_attivita_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_fattura_header(p_lotto_id bigint, p_attivita_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_key jsonb;
  v_fattura_id vendite.fatture.id%TYPE;
  v_stato_doc_id config.stati_doc_fiscale.id%TYPE;
  v_registro_id vendite.registri_fatturazione.id%TYPE;
  v_ba_id anagrafiche.billing_account.id%TYPE;
  v_tipo_doc_id config.tipi_doc_fiscale.id%TYPE;
  v_valuta_id config.valute.id%TYPE;
  v_emittente_id anagrafiche.soggetti_ruoli.id%TYPE;
  v_reseller_id anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Recupera o crea una fattura in bozza per il lotto,
  --   usando la chiave di aggregazione documento.
  --
  -- Regole:
  --   - chiave documento da fn_build_fattura_key(attivita)
  --   - stato iniziale: DRAFT
  --   - link lotto <-> fattura in fatturazione_lotti_fatture
  -- =========================================================

  IF p_lotto_id IS NULL OR p_lotto_id <= 0 OR p_attivita_id IS NULL OR p_attivita_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_or_create_fattura_header', 'E_GENERICO',
      jsonb_build_object(
        'scope','FATTURA',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object(
          'detail','lotto_id e attivita_id obbligatori',
          'lotto_id', p_lotto_id,
          'attivita_id', p_attivita_id
        )
      ),
      NULL::uuid, 'Parametri obbligatori mancanti'
    );
  END IF;

  v_key := vendite.fn_build_fattura_key(p_attivita_id);

  v_ba_id := (v_key->>'billing_account_id')::bigint;
  v_tipo_doc_id := (v_key->>'tipo_doc_fiscale_id')::bigint;
  v_valuta_id := (v_key->>'valuta_id')::integer;
  v_emittente_id := (v_key->>'emittente_soggetto_ruolo_id')::bigint;
  v_reseller_id := NULLIF(v_key->>'reseller_soggetto_ruolo_id','')::bigint;
  v_registro_id := (v_key->>'registro_id')::bigint;

  IF v_ba_id IS NULL OR v_tipo_doc_id IS NULL OR v_valuta_id IS NULL
     OR v_emittente_id IS NULL OR v_registro_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_or_create_fattura_header', 'E_GENERICO',
      jsonb_build_object(
        'scope','FATTURA',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail','chiave documento incompleta', 'attivita_id', p_attivita_id)
      ),
      NULL::uuid,
      concat('Chiave documento incompleta', ' attivita_id ', p_attivita_id::text)
    );
  END IF;

  SELECT id
    INTO v_stato_doc_id
    FROM config.stati_doc_fiscale
   WHERE codice_interno = 'DRAFT'
     AND attivo IS TRUE
   ORDER BY id
   LIMIT 1;

  IF v_stato_doc_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_or_create_fattura_header', 'E_GENERICO',
      jsonb_build_object(
        'scope','FATTURA',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail','stato DRAFT non trovato')
      ),
      NULL::uuid, 'Stato DRAFT non trovato'
    );
  END IF;

  -- Cerca fattura gia` presente nel lotto con stessa chiave documento
  SELECT f.id
    INTO v_fattura_id
    FROM vendite.fatturazione_lotti_fatture lf
    JOIN vendite.fatture f
      ON f.id = lf.fattura_id
   WHERE lf.lotto_id = p_lotto_id
     AND f.billing_account_id = v_ba_id
     AND f.tipo_doc_fiscale_id = v_tipo_doc_id
     AND f.valuta_id = v_valuta_id
     AND f.emittente_soggetto_ruolo_id = v_emittente_id
     AND COALESCE(f.reseller_soggetto_ruolo_id, 0) = COALESCE(v_reseller_id, 0)
     AND f.registro_id = v_registro_id
   ORDER BY f.id
   LIMIT 1;

  IF v_fattura_id IS NOT NULL THEN
    RETURN v_fattura_id;
  END IF;

  INSERT INTO vendite.fatture (
    registro_id,
    data,
    tipo_doc_fiscale_id,
    stato_doc_fiscale_id,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    reseller_soggetto_ruolo_id,
    valuta_id,
    tasso_cambio,
    meta
  )
  VALUES (
    v_registro_id,
    current_date,
    v_tipo_doc_id,
    v_stato_doc_id,
    v_emittente_id,
    v_ba_id,
    v_reseller_id,
    v_valuta_id,
    1,
    jsonb_build_object('lotto_id', p_lotto_id)
  )
  RETURNING id INTO v_fattura_id;

  INSERT INTO vendite.fatturazione_lotti_fatture (
    lotto_id,
    fattura_id,
    esclusa,
    meta
  )
  VALUES (
    p_lotto_id,
    v_fattura_id,
    false,
    jsonb_build_object('origine', 'bozza')
  );

  RETURN v_fattura_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_or_create_fattura_header(p_lotto_id bigint, p_attivita_id bigint)
IS 'Recupera o crea la testata fattura DRAFT per il lotto in base alla chiave documento derivata dall''attivita.';
```

---
{% include-markdown "signature-core.md" %}
