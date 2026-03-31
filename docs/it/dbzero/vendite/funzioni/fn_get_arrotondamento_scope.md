{% include-markdown "it/dbzero/vendite/manual/fn_get_arrotondamento_scope.md" %}
# ⚙️ Funzione `fn_get_arrotondamento_scope`

```sql
CREATE FUNCTION fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id bigint)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_saldo vendite.fatture_arrotondamenti_scope.saldo_arrotondamento%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce il saldo tecnico arrotondamenti per scope.
  --   Se lo scope non esiste, restituisce 0.
  -- =========================================================

  IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_get_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','billing_account_id obbligatorio'),
      NULL::uuid,
      'billing_account_id non valido'
    );
  END IF;

  IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_get_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','utility_id obbligatorio'),
      NULL::uuid,
      'utility_id non valido'
    );
  END IF;

  IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_get_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','tipo_doc_fiscale_id obbligatorio'),
      NULL::uuid,
      'tipo_doc_fiscale_id non valido'
    );
  END IF;

  IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_get_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','emittente_soggetto_ruolo_id obbligatorio'),
      NULL::uuid,
      'emittente_soggetto_ruolo_id non valido'
    );
  END IF;

  IF p_valuta_id IS NULL OR p_valuta_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_get_arrotondamento_scope', 'E_GENERICO',
      jsonb_build_object('detail','valuta_id obbligatorio'),
      NULL::uuid,
      'valuta_id non valido'
    );
  END IF;

  SELECT s.saldo_arrotondamento
    INTO v_saldo
    FROM vendite.fatture_arrotondamenti_scope s
   WHERE s.billing_account_id = p_billing_account_id
     AND s.utility_id = p_utility_id
     AND s.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
     AND s.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
     AND s.valuta_id = p_valuta_id;

  RETURN COALESCE(v_saldo, 0);
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id bigint)
IS 'Saldo tecnico arrotondamenti per scope (0 se assente).';
```

---
{% include-markdown "signature-core.md" %}
