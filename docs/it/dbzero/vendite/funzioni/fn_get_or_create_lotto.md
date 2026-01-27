{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_lotto.md" %}
# ⚙️ Funzione `fn_get_or_create_lotto`

```sql
CREATE FUNCTION fn_get_or_create_lotto(p_lotto_id bigint, p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_billing_account_id bigint, p_lock_batch_id uuid, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_lotto(p_lotto_id bigint DEFAULT NULL::bigint, p_competenza_mese date DEFAULT NULL::date, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_billing_account_id bigint DEFAULT NULL::bigint, p_lock_batch_id uuid DEFAULT NULL::uuid, p_meta jsonb DEFAULT NULL::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_lotto_id vendite.fatturazione_lotti.id%TYPE;
  v_competenza vendite.fatturazione_lotti.competenza_mese%TYPE;
  v_utility_id config.utilities.id%TYPE;
  v_tipo_doc_id config.tipi_doc_fiscale.id%TYPE;
  v_billing_account_id anagrafiche.billing_account.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Recupera un lotto esistente o lo crea se assente.
  --
  -- Regole:
  --   - se p_lotto_id presente, valida coerenza parametri
  --   - se p_lock_batch_id presente, riusa lotto se esistente
  -- =========================================================

  IF p_lotto_id IS NOT NULL THEN
    SELECT competenza_mese, utility_id, tipo_doc_fiscale_id, billing_account_id
      INTO v_competenza, v_utility_id, v_tipo_doc_id, v_billing_account_id
      FROM vendite.fatturazione_lotti
     WHERE id = p_lotto_id;

    IF v_competenza IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('detail','Lotto non trovato', 'lotto_id', p_lotto_id),
        NULL::uuid, 
        concat('Lotto non trovato', ' lotto_id: ', p_lotto_id::text)
      );
    END IF;

    IF p_competenza_mese IS NOT NULL
      AND date_trunc('month', p_competenza_mese)::date <> v_competenza THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('detail','Competenza non coerente', 'lotto_id', p_lotto_id),
        NULL::uuid, 
        concat('Competenza non coerente', ' lotto_id: ', p_lotto_id::text)
      );
    END IF;

    IF p_utility_id IS NOT NULL AND p_utility_id <> v_utility_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('detail','Utility non coerente', 'lotto_id', p_lotto_id),
        NULL::uuid, concat('Utility non coerente', ' lotto_id: ', p_lotto_id::text) 
      );
    END IF;

    IF p_tipo_doc_fiscale_id IS NOT NULL AND p_tipo_doc_fiscale_id <> v_tipo_doc_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('detail','Tipo documento non coerente', 'lotto_id', p_lotto_id),
        NULL::uuid, 
        concat('Tipo documento non coerente', ' lotto_id: ', p_lotto_id::text)
      );
    END IF;

    IF p_billing_account_id IS NOT NULL AND p_billing_account_id <> v_billing_account_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('detail','Billing account non coerente', 'lotto_id', p_lotto_id),
        NULL::uuid, concat('Billing account non coerente', ' lotto_id: ', p_lotto_id::text)
      );
    END IF;

    RETURN p_lotto_id;
  END IF;

  IF p_lock_batch_id IS NOT NULL THEN
    SELECT id
      INTO v_lotto_id
      FROM vendite.fatturazione_lotti
     WHERE lock_batch_id = p_lock_batch_id;

    IF v_lotto_id IS NOT NULL THEN
      RETURN v_lotto_id;
    END IF;
  END IF;

  RETURN vendite.fn_create_fatturazione_lotto(
    p_competenza_mese,
    p_tipo_doc_fiscale_id,
    p_utility_id,
    p_billing_account_id,
    p_lock_batch_id,
    p_meta
  );
END
$function$
```

---
{% include-markdown "signature-core.md" %}
