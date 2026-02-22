{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_lotto_attivita.md" %}
# ⚙️ Funzione `fn_get_or_create_lotto_attivita`

```sql
CREATE FUNCTION fn_get_or_create_lotto_attivita(p_lotto_id bigint, p_competenza_mese date, p_utility_id integer, p_billing_account_id bigint, p_sorgente_tipo_id bigint, p_lock_batch_id uuid, p_meta jsonb, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_lotto_attivita(p_lotto_id bigint DEFAULT NULL::bigint, p_competenza_mese date DEFAULT NULL::date, p_utility_id integer DEFAULT NULL::integer, p_billing_account_id bigint DEFAULT NULL::bigint, p_sorgente_tipo_id bigint DEFAULT NULL::bigint, p_lock_batch_id uuid DEFAULT NULL::uuid, p_meta jsonb DEFAULT NULL::jsonb, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_lotto_id vendite.attivita_fatturabili_lotti.id%TYPE;
  v_competenza vendite.attivita_fatturabili_lotti.competenza_mese%TYPE;
  v_utility_id vendite.attivita_fatturabili_lotti.utility_id%TYPE;
  v_billing_account_id vendite.attivita_fatturabili_lotti.billing_account_id%TYPE;
  v_sorgente_tipo_id vendite.attivita_fatturabili_lotti.sorgente_tipo_id%TYPE;
  v_emittente_id vendite.attivita_fatturabili_lotti.emittente_soggetto_ruolo_id%TYPE;
  v_stato_lotto vendite.attivita_fatturabili_lotti.stato_lotto%TYPE;
  v_stato_operativo vendite.attivita_fatturabili_lotti.stato_operativo%TYPE;
  v_resolved_utility_id config.utilities.id%TYPE;
  v_resolved_emittente_id vendite.attivita_fatturabili_lotti.emittente_soggetto_ruolo_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Recupera un lotto attivita esistente o lo crea se assente.
  --
  -- Regole:
  --   - fallback emittente allineato a fatturazione
  --   - coerenza BA/utility/emittente anche su riuso lotto
  --   - blocco riuso lotto con IN_ESECUZIONE + CHIUSO
  -- =========================================================

  IF p_lotto_id = 0 THEN
    p_lotto_id := NULL;
  END IF;

  IF p_lotto_id IS NOT NULL AND p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto_id non valido')),
      NULL::uuid, 'lotto_id non valido'
    );
  END IF;

  IF p_sorgente_tipo_id IS NOT NULL AND p_sorgente_tipo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','sorgente_tipo_id non valido','sorgente_tipo_id',p_sorgente_tipo_id)),
      NULL::uuid, 'sorgente_tipo_id non valido'
    );
  END IF;

  SELECT r.resolved_utility_id, r.resolved_emittente_soggetto_ruolo_id
    INTO v_resolved_utility_id, v_resolved_emittente_id
    FROM vendite.fn_resolve_lotto_utility_emittente(
      p_billing_account_id => p_billing_account_id,
      p_utility_id => p_utility_id,
      p_emittente_soggetto_ruolo_id => p_emittente_soggetto_ruolo_id,
      p_scope => 'ATTIVITA_FATTURABILI',
      p_caller => 'fn_get_or_create_lotto_attivita',
      p_check_emittente_attivo => true
    ) r;

  IF p_lotto_id IS NOT NULL THEN
    SELECT competenza_mese, utility_id, billing_account_id, sorgente_tipo_id,
           emittente_soggetto_ruolo_id, stato_lotto, stato_operativo
      INTO v_competenza, v_utility_id, v_billing_account_id, v_sorgente_tipo_id,
           v_emittente_id, v_stato_lotto, v_stato_operativo
      FROM vendite.attivita_fatturabili_lotti
     WHERE id = p_lotto_id;

    IF v_competenza IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
        jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto non trovato')),
        NULL::uuid, 'lotto non trovato'
      );
    END IF;

    IF p_competenza_mese IS NOT NULL AND date_trunc('month', p_competenza_mese)::date <> v_competenza THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
        jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','competenza non coerente')),
        NULL::uuid, 'competenza non coerente'
      );
    END IF;

    IF v_resolved_utility_id IS NOT NULL AND v_resolved_utility_id <> v_utility_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
        jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','utility non coerente')),
        NULL::uuid, 'utility non coerente'
      );
    END IF;

    IF p_billing_account_id IS NOT NULL AND p_billing_account_id <> v_billing_account_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
        jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','billing_account non coerente')),
        NULL::uuid, 'billing_account non coerente'
      );
    END IF;

    IF p_sorgente_tipo_id IS NOT NULL AND p_sorgente_tipo_id <> v_sorgente_tipo_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
        jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','sorgente_tipo non coerente')),
        NULL::uuid, 'sorgente_tipo non coerente'
      );
    END IF;

    IF v_resolved_emittente_id IS NOT NULL AND v_resolved_emittente_id <> v_emittente_id THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
        jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','emittente non coerente')),
        NULL::uuid, 'emittente non coerente'
      );
    END IF;

    IF v_stato_lotto = 'IN_ESECUZIONE' AND v_stato_operativo = 'CHIUSO' THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
        jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto in esecuzione non riutilizzabile per stato_operativo','stato_operativo',v_stato_operativo)),
        NULL::uuid, 'lotto in esecuzione non riutilizzabile'
      );
    END IF;

    RETURN p_lotto_id;
  END IF;

  IF p_lock_batch_id IS NOT NULL THEN
    SELECT id, competenza_mese, utility_id, billing_account_id, sorgente_tipo_id,
           emittente_soggetto_ruolo_id, stato_lotto, stato_operativo
      INTO v_lotto_id, v_competenza, v_utility_id, v_billing_account_id, v_sorgente_tipo_id,
           v_emittente_id, v_stato_lotto, v_stato_operativo
      FROM vendite.attivita_fatturabili_lotti
     WHERE lock_batch_id = p_lock_batch_id
     ORDER BY id DESC
     LIMIT 1;

    IF v_lotto_id IS NOT NULL THEN
      IF p_competenza_mese IS NOT NULL AND date_trunc('month', p_competenza_mese)::date <> v_competenza THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
          jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','competenza non coerente')),
          NULL::uuid, 'competenza non coerente'
        );
      END IF;

      IF v_resolved_utility_id IS NOT NULL AND v_resolved_utility_id <> v_utility_id THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
          jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','utility non coerente')),
          NULL::uuid, 'utility non coerente'
        );
      END IF;

      IF p_billing_account_id IS NOT NULL AND p_billing_account_id <> v_billing_account_id THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
          jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','billing_account non coerente')),
          NULL::uuid, 'billing_account non coerente'
        );
      END IF;

      IF p_sorgente_tipo_id IS NOT NULL AND p_sorgente_tipo_id <> v_sorgente_tipo_id THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
          jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','sorgente_tipo non coerente')),
          NULL::uuid, 'sorgente_tipo non coerente'
        );
      END IF;

      IF v_resolved_emittente_id IS NOT NULL AND v_resolved_emittente_id <> v_emittente_id THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
          jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','emittente non coerente')),
          NULL::uuid, 'emittente non coerente'
        );
      END IF;

      IF v_stato_lotto = 'IN_ESECUZIONE' AND v_stato_operativo = 'CHIUSO' THEN
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
          jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',v_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto in esecuzione non riutilizzabile per stato_operativo','stato_operativo',v_stato_operativo)),
          NULL::uuid, 'lotto in esecuzione non riutilizzabile'
        );
      END IF;

      RETURN v_lotto_id;
    END IF;
  END IF;

  IF p_competenza_mese IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_or_create_lotto_attivita', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','competenza_mese obbligatoria in creazione lotto')),
      NULL::uuid, 'competenza_mese obbligatoria in creazione lotto'
    );
  END IF;

  INSERT INTO vendite.attivita_fatturabili_lotti (
    lock_batch_id,
    competenza_mese,
    utility_id,
    billing_account_id,
    sorgente_tipo_id,
    stato_lotto,
    stato_operativo,
    emittente_soggetto_ruolo_id,
    meta
  )
  VALUES (
    COALESCE(p_lock_batch_id, uuidv7()),
    date_trunc('month', p_competenza_mese)::date,
    COALESCE(v_resolved_utility_id, p_utility_id),
    p_billing_account_id,
    p_sorgente_tipo_id,
    'IN_ESECUZIONE',
    'APERTO',
    v_resolved_emittente_id,
    COALESCE(p_meta, '{}'::jsonb)
  )
  RETURNING id INTO v_lotto_id;

  RETURN v_lotto_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_or_create_lotto_attivita(p_lotto_id bigint, p_competenza_mese date, p_utility_id integer, p_billing_account_id bigint, p_sorgente_tipo_id bigint, p_lock_batch_id uuid, p_meta jsonb, p_emittente_soggetto_ruolo_id bigint)
IS 'Recupera o crea lotto attivita usando helper condiviso per coerenza utility/emittente fiscale.';
```

---
{% include-markdown "signature-core.md" %}
