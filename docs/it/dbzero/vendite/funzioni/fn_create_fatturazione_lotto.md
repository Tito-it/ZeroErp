{% include-markdown "it/dbzero/vendite/manual/fn_create_fatturazione_lotto.md" %}
# ⚙️ Funzione `fn_create_fatturazione_lotto`

```sql
CREATE FUNCTION fn_create_fatturazione_lotto(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_billing_account_id bigint, p_lock_batch_id uuid, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_create_fatturazione_lotto(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer DEFAULT NULL::integer, p_billing_account_id bigint DEFAULT NULL::bigint, p_lock_batch_id uuid DEFAULT NULL::uuid, p_meta jsonb DEFAULT NULL::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_competenza vendite.fatturazione_lotti.competenza_mese%TYPE;
  v_utility_id config.utilities.id%TYPE;
  v_lock_batch_id vendite.fatturazione_lotti.lock_batch_id%TYPE;
  v_lotto_id vendite.fatturazione_lotti.id%TYPE;
  v_stato_doc_id config.stati_doc_fiscale.id%TYPE;
  v_map_exists boolean;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Crea un lotto di fatturazione con parametri coerenti
  --   (competenza, utility, tipo_doc_fiscale, BA) e stato iniziale.
  --
  -- Regole:
  --   - competenza_mese normalizzata al primo del mese
  --   - utility_id derivata da BA se presente
  --   - tipo_doc_fiscale obbligatorio e attivo
  --   - mapping tipo_doc_fiscale -> registro presente
  --   - stato_doc_fiscale iniziale = DRAFT (applica_lotto)
  -- =========================================================

  IF p_competenza_mese IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_create_fatturazione_lotto', 'E_GENERICO',
      jsonb_build_object('detail','competenza_mese obbligatoria'),
      NULL::uuid, 'competenza_mese obbligatoria'
    );
  END IF;

  IF p_tipo_doc_fiscale_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_create_fatturazione_lotto', 'E_GENERICO',
      jsonb_build_object('detail','tipo_doc_fiscale_id obbligatorio'),
      NULL::uuid, 
      'tipo_doc_fiscale_id obbligatorio'
    );
  END IF;

  v_competenza := date_trunc('month', p_competenza_mese)::date;

  v_utility_id := p_utility_id;
  IF p_billing_account_id IS NOT NULL THEN
    SELECT ba.utility_id
      INTO v_utility_id
      FROM anagrafiche.billing_account ba
    WHERE ba.id = p_billing_account_id;

    IF v_utility_id IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_create_fatturazione_lotto', 'E_GENERICO',
        jsonb_build_object(
          'detail','Utility non risolta da billing_account',
          'billing_account_id', p_billing_account_id
        ),
        NULL::uuid, 
        concat('Utility non risolta da billing_account', 
        ' billing_account_id: ', p_billing_account_id::text)
      );
    END IF;

    IF p_utility_id IS NOT NULL AND p_utility_id <> v_utility_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_create_fatturazione_lotto', 'E_GENERICO',
        jsonb_build_object(
          'detail','Utility non coerente con billing_account',
          'billing_account_id', p_billing_account_id,
          'utility_id', p_utility_id
        ),
        NULL::uuid,
        concat('Utility non coerente con billing_account', 
          ' billing_account_id: ', p_billing_account_id::text,
          ' utility_id: ', p_utility_id::text)
      );
    END IF;
  END IF;

  IF v_utility_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_create_fatturazione_lotto', 'E_GENERICO',
      jsonb_build_object('detail','utility_id obbligatoria'),
      NULL::uuid, 'utility_id obbligatoria'
    );
  END IF;

  SELECT EXISTS (
    SELECT 1
      FROM config.tipi_doc_fiscale t
    WHERE t.id = p_tipo_doc_fiscale_id
      AND t.attivo IS TRUE
  )
  INTO v_map_exists;

  IF NOT v_map_exists THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_create_fatturazione_lotto', 'E_GENERICO',
      jsonb_build_object(
        'detail','Tipo documento fiscale non attivo o inesistente',
        'tipo_doc_fiscale_id', p_tipo_doc_fiscale_id
      ),
      NULL::uuid, 
      concat('Tipo documento fiscale non attivo o inesistente', ' tipo_doc_fiscale_id: ', p_tipo_doc_fiscale_id::text)
    );
  END IF;

  SELECT EXISTS (
    SELECT 1
      FROM vendite.tipi_doc_fiscale_registri m
    WHERE m.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
  )
  INTO v_map_exists;

  IF NOT v_map_exists THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_create_fatturazione_lotto', 'E_GENERICO',
      jsonb_build_object(
        'detail','Mapping tipo_doc_fiscale -> registro assente',
        'tipo_doc_fiscale_id', p_tipo_doc_fiscale_id
      ),
      NULL::uuid, 
      concat('Mapping tipo_doc_fiscale -> registro assente', ' tipo_doc_fiscale_id: ', p_tipo_doc_fiscale_id::text)
    );
  END IF;

  SELECT id
    INTO v_stato_doc_id
    FROM config.stati_doc_fiscale
  WHERE codice = 'DRAFT'
    AND applica_lotto IS TRUE
    AND attivo IS TRUE
  ORDER BY ordine
  LIMIT 1;

  IF v_stato_doc_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_create_fatturazione_lotto', 'E_GENERICO',
      jsonb_build_object('detail','Stato DRAFT non disponibile per lotto'),
      NULL::uuid, 'Stato DRAFT non disponibile per lotto'
    );
  END IF;

  v_lock_batch_id := COALESCE(p_lock_batch_id, uuidv7());

  INSERT INTO vendite.fatturazione_lotti (
    lock_batch_id,
    competenza_mese,
    utility_id,
    billing_account_id,
    tipo_doc_fiscale_id,
    stato_doc_fiscale_id,
    meta
  )
  VALUES (
    v_lock_batch_id,
    v_competenza,
    v_utility_id,
    p_billing_account_id,
    p_tipo_doc_fiscale_id,
    v_stato_doc_id,
    COALESCE(p_meta, '{}'::jsonb)
  )
  RETURNING id
    INTO v_lotto_id;

  RETURN v_lotto_id;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
