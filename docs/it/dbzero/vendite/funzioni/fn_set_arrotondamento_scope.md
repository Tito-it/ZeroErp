{% include-markdown "it/dbzero/vendite/manual/fn_set_arrotondamento_scope.md" %}
# ⚙️ Funzione `fn_set_arrotondamento_scope`

```sql
CREATE FUNCTION fn_set_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id bigint, p_saldo numeric)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_set_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id bigint, p_saldo numeric)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_saldo vendite.fatture_arrotondamenti_scope.saldo_arrotondamento%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Imposta il saldo tecnico arrotondamenti per scope.
  --   Crea la riga se assente (upsert).
  -- =========================================================

  IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_set_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','billing_account_id obbligatorio'),
      NULL::uuid,
      'billing_account_id non valido'
    );
  END IF;

  IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_set_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','utility_id obbligatorio'),
      NULL::uuid,
      'utility_id non valido'
    );
  END IF;

  IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_set_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','tipo_doc_fiscale_id obbligatorio'),
      NULL::uuid,
      'tipo_doc_fiscale_id non valido'
    );
  END IF;

  IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_set_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','emittente_soggetto_ruolo_id obbligatorio'),
      NULL::uuid,
      'emittente_soggetto_ruolo_id non valido'
    );
  END IF;

  IF p_valuta_id IS NULL OR p_valuta_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_set_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','valuta_id obbligatorio'),
      NULL::uuid,
      'valuta_id non valido'
    );
  END IF;

  IF p_saldo IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_set_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','saldo_arrotondamento obbligatorio'),
      NULL::uuid,
      'saldo_arrotondamento non puo'' essere NULL'
    );
  END IF;

  INSERT INTO vendite.fatture_arrotondamenti_scope (
    billing_account_id,
    utility_id,
    tipo_doc_fiscale_id,
    emittente_soggetto_ruolo_id,
    valuta_id,
    saldo_arrotondamento,
    data_insert,
    user_insert,
    data_update,
    user_update
  )
  VALUES (
    p_billing_account_id,
    p_utility_id,
    p_tipo_doc_fiscale_id,
    p_emittente_soggetto_ruolo_id,
    p_valuta_id,
    p_saldo,
    now(),
    current_user,
    now(),
    current_user
  )
  ON CONFLICT (
    billing_account_id,
    utility_id,
    tipo_doc_fiscale_id,
    emittente_soggetto_ruolo_id,
    valuta_id
  ) DO UPDATE
  SET saldo_arrotondamento = EXCLUDED.saldo_arrotondamento,
      data_update = now(),
      user_update = current_user
  RETURNING saldo_arrotondamento
  INTO v_saldo;

  RETURN v_saldo;
END;
$function$

COMMENT ON FUNCTION vendite.fn_set_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id bigint, p_saldo numeric)
IS 'Imposta (upsert) il saldo tecnico arrotondamenti per scope.';
```

---
{% include-markdown "signature-core.md" %}
