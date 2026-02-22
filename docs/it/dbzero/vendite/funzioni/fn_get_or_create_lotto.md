{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_lotto.md" %}
# ⚙️ Funzione `fn_get_or_create_lotto`

```sql
CREATE FUNCTION fn_get_or_create_lotto(p_lotto_id bigint, p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_billing_account_id bigint, p_lock_batch_id uuid, p_meta jsonb, p_tipo_lotto text, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_lotto(p_lotto_id bigint DEFAULT NULL::bigint, p_competenza_mese date DEFAULT NULL::date, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_billing_account_id bigint DEFAULT NULL::bigint, p_lock_batch_id uuid DEFAULT NULL::uuid, p_meta jsonb DEFAULT NULL::jsonb, p_tipo_lotto text DEFAULT 'MASSIVO'::text, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_lotto_id vendite.fatturazione_lotti.id%TYPE;
  v_competenza vendite.fatturazione_lotti.competenza_mese%TYPE;
  v_utility_id config.utilities.id%TYPE;
  v_tipo_doc_id config.tipi_doc_fiscale.id%TYPE;
  v_billing_account_id anagrafiche.billing_account.id%TYPE;
  v_emittente_id vendite.fatturazione_lotti.emittente_soggetto_ruolo_id%TYPE;
  v_tipo_lotto vendite.fatturazione_lotti.tipo_lotto%TYPE;
  v_stato_lotto vendite.fatturazione_lotti.stato_lotto%TYPE;
  v_stato_operativo vendite.fatturazione_lotti.stato_operativo%TYPE;
  v_tipo_lotto_input vendite.fatturazione_lotti.tipo_lotto%TYPE;
  v_resolved_utility_id config.utilities.id%TYPE;
  v_resolved_emittente_id vendite.fatturazione_lotti.emittente_soggetto_ruolo_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Recupera un lotto esistente o lo crea se assente.
  --
  -- Regole:
  --   - tipo_lotto obbligatorio (MASSIVO | GIORNALIERO)
  --   - validazioni coerenza complete su lotto esistente
  --   - blocco riuso solo con IN_ESECUZIONE + CHIUSO
  -- =========================================================

  IF p_lotto_id = 0 THEN
    p_lotto_id := NULL;
  END IF;

  v_tipo_lotto_input := upper(btrim(COALESCE(p_tipo_lotto, '')));
  IF v_tipo_lotto_input IS NULL OR v_tipo_lotto_input = '' OR v_tipo_lotto_input NOT IN ('MASSIVO','GIORNALIERO') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','tipo_lotto non valido','tipo_lotto',p_tipo_lotto)),
      NULL::uuid, 'tipo_lotto non valido'
    );
  END IF;

  IF p_lotto_id IS NOT NULL AND p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto_id non valido','lotto_id',p_lotto_id)),
      NULL::uuid, 'lotto_id non valido'
    );
  END IF;

  IF p_tipo_doc_fiscale_id IS NOT NULL AND p_tipo_doc_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','tipo_doc_fiscale_id non valido','tipo_doc_fiscale_id',p_tipo_doc_fiscale_id)),
      NULL::uuid, 'tipo_doc_fiscale_id non valido'
    );
  END IF;

  SELECT r.resolved_utility_id, r.resolved_emittente_soggetto_ruolo_id
    INTO v_resolved_utility_id, v_resolved_emittente_id
    FROM vendite.fn_resolve_lotto_utility_emittente(
      p_billing_account_id => p_billing_account_id,
      p_utility_id => p_utility_id,
      p_emittente_soggetto_ruolo_id => p_emittente_soggetto_ruolo_id,
      p_scope => 'LOTTO',
      p_caller => 'fn_get_or_create_lotto',
      p_check_emittente_attivo => true
    ) r;

  IF p_lotto_id IS NOT NULL THEN
    SELECT competenza_mese, utility_id, tipo_doc_fiscale_id, billing_account_id,
           emittente_soggetto_ruolo_id, tipo_lotto, stato_lotto, stato_operativo
      INTO v_competenza, v_utility_id, v_tipo_doc_id, v_billing_account_id,
           v_emittente_id, v_tipo_lotto, v_stato_lotto, v_stato_operativo
      FROM vendite.fatturazione_lotti
     WHERE id = p_lotto_id;

    IF v_competenza IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto non trovato')),
        NULL::uuid, concat('lotto non trovato lotto_id: ', p_lotto_id::text)
      );
    END IF;

    IF p_competenza_mese IS NOT NULL AND date_trunc('month', p_competenza_mese)::date <> v_competenza THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','competenza non coerente')),
        NULL::uuid, 'competenza non coerente'
      );
    END IF;

    IF v_resolved_utility_id IS NOT NULL AND v_resolved_utility_id <> v_utility_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','utility non coerente')),
        NULL::uuid, 'utility non coerente'
      );
    END IF;

    IF p_tipo_doc_fiscale_id IS NOT NULL AND p_tipo_doc_fiscale_id <> v_tipo_doc_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','tipo documento non coerente')),
        NULL::uuid, 'tipo documento non coerente'
      );
    END IF;

    IF p_billing_account_id IS NOT NULL AND p_billing_account_id <> v_billing_account_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','billing_account non coerente')),
        NULL::uuid, 'billing_account non coerente'
      );
    END IF;

    IF v_resolved_emittente_id IS NOT NULL AND v_resolved_emittente_id <> v_emittente_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','emittente fiscale non coerente')),
        NULL::uuid, 'emittente fiscale non coerente'
      );
    END IF;

    IF v_tipo_lotto IS NOT NULL AND v_tipo_lotto <> v_tipo_lotto_input THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','tipo lotto non coerente')),
        NULL::uuid, 'tipo lotto non coerente'
      );
    END IF;

    IF v_stato_lotto = 'IN_ESECUZIONE' AND v_stato_operativo = 'CHIUSO' THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
        jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto in esecuzione non riutilizzabile per stato_operativo','stato_operativo',v_stato_operativo)),
        NULL::uuid, 'lotto in esecuzione non riutilizzabile'
      );
    END IF;

    RETURN p_lotto_id;
  END IF;

  IF p_lock_batch_id IS NOT NULL THEN
    SELECT id, competenza_mese, utility_id, tipo_doc_fiscale_id, billing_account_id,
           emittente_soggetto_ruolo_id, tipo_lotto, stato_lotto, stato_operativo
      INTO v_lotto_id, v_competenza, v_utility_id, v_tipo_doc_id, v_billing_account_id,
           v_emittente_id, v_tipo_lotto, v_stato_lotto, v_stato_operativo
      FROM vendite.fatturazione_lotti
     WHERE lock_batch_id = p_lock_batch_id
     ORDER BY id DESC
     LIMIT 1;

    IF v_lotto_id IS NOT NULL THEN
      IF p_competenza_mese IS NOT NULL AND date_trunc('month', p_competenza_mese)::date <> v_competenza THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
          jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','competenza non coerente')),
          NULL::uuid, 'competenza non coerente'
        );
      END IF;

      IF v_resolved_utility_id IS NOT NULL AND v_resolved_utility_id <> v_utility_id THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
          jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','utility non coerente')),
          NULL::uuid, 'utility non coerente'
        );
      END IF;

      IF p_tipo_doc_fiscale_id IS NOT NULL AND p_tipo_doc_fiscale_id <> v_tipo_doc_id THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
          jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','tipo documento non coerente')),
          NULL::uuid, 'tipo documento non coerente'
        );
      END IF;

      IF p_billing_account_id IS NOT NULL AND p_billing_account_id <> v_billing_account_id THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
          jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','billing_account non coerente')),
          NULL::uuid, 'billing_account non coerente'
        );
      END IF;

      IF v_resolved_emittente_id IS NOT NULL AND v_resolved_emittente_id <> v_emittente_id THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
          jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','emittente fiscale non coerente')),
          NULL::uuid, 'emittente fiscale non coerente'
        );
      END IF;

      IF v_tipo_lotto IS NOT NULL AND v_tipo_lotto <> v_tipo_lotto_input THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
          jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','tipo lotto non coerente')),
          NULL::uuid, 'tipo lotto non coerente'
        );
      END IF;

      IF v_stato_lotto = 'IN_ESECUZIONE' AND v_stato_operativo = 'CHIUSO' THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto', 'E_GENERICO',
          jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto in esecuzione non riutilizzabile per stato_operativo','stato_operativo',v_stato_operativo)),
          NULL::uuid, 'lotto in esecuzione non riutilizzabile'
        );
      END IF;

      RETURN v_lotto_id;
    END IF;
  END IF;

  v_lotto_id := vendite.fn_create_fatturazione_lotto(
    p_competenza_mese => p_competenza_mese,
    p_tipo_doc_fiscale_id => p_tipo_doc_fiscale_id,
    p_utility_id => COALESCE(v_resolved_utility_id, p_utility_id),
    p_billing_account_id => p_billing_account_id,
    p_lock_batch_id => p_lock_batch_id,
    p_meta => p_meta,
    p_emittente_soggetto_ruolo_id => v_resolved_emittente_id
  );

  UPDATE vendite.fatturazione_lotti
     SET tipo_lotto = v_tipo_lotto_input,
         data_update = now(),
         user_update = current_user
   WHERE id = v_lotto_id;

  RETURN v_lotto_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_or_create_lotto(p_lotto_id bigint, p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_billing_account_id bigint, p_lock_batch_id uuid, p_meta jsonb, p_tipo_lotto text, p_emittente_soggetto_ruolo_id bigint)
IS 'Recupera o crea lotto usando helper condiviso per coerenza utility/emittente fiscale.';
```

---
{% include-markdown "signature-core.md" %}
