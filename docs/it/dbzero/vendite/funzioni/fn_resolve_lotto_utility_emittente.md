{% include-markdown "it/dbzero/vendite/manual/fn_resolve_lotto_utility_emittente.md" %}
# ⚙️ Funzione `fn_resolve_lotto_utility_emittente`

```sql
CREATE FUNCTION fn_resolve_lotto_utility_emittente(p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_scope text, p_caller text, p_check_emittente_attivo boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_lotto_utility_emittente(p_billing_account_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_scope text DEFAULT 'LOTTO'::text, p_caller text DEFAULT 'fn_resolve_lotto_utility_emittente'::text, p_check_emittente_attivo boolean DEFAULT true)
 RETURNS TABLE(resolved_utility_id integer, resolved_emittente_soggetto_ruolo_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_utility_from_ba anagrafiche.billing_account.utility_id%TYPE;
  v_emittente_from_ba anagrafiche.soggetti_ruoli.id%TYPE;
  v_emittente_attivo boolean;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolvere e validare utility/emittente per i lotti.
  --
  -- Regole:
  --   - utility da BA se BA presente
  --   - emittente da fn_get_emittente_fiscale_id(BA)
  --     (include fallback default globale)
  --   - se emittente passato e BA presente: deve coincidere
  -- =========================================================

  IF p_billing_account_id IS NOT NULL AND p_billing_account_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', p_caller, 'E_GENERICO',
      jsonb_build_object('scope',p_scope,'severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','billing_account_id non valido','billing_account_id',p_billing_account_id)),
      NULL::uuid, 'billing_account_id non valido'
    );
  END IF;

  IF p_utility_id IS NOT NULL AND p_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', p_caller, 'E_GENERICO',
      jsonb_build_object('scope',p_scope,'severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','utility_id non valido','utility_id',p_utility_id)),
      NULL::uuid, 'utility_id non valido'
    );
  END IF;

  IF p_emittente_soggetto_ruolo_id IS NOT NULL AND p_emittente_soggetto_ruolo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', p_caller, 'E_GENERICO',
      jsonb_build_object('scope',p_scope,'severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','emittente_soggetto_ruolo_id non valido','emittente_soggetto_ruolo_id',p_emittente_soggetto_ruolo_id)),
      NULL::uuid, 'emittente_soggetto_ruolo_id non valido'
    );
  END IF;

  resolved_utility_id := p_utility_id;

  IF p_billing_account_id IS NOT NULL THEN
    SELECT ba.utility_id
      INTO v_utility_from_ba
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_billing_account_id;

    IF v_utility_from_ba IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', p_caller, 'E_GENERICO',
        jsonb_build_object('scope',p_scope,'severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','utility non risolta da billing_account','billing_account_id',p_billing_account_id)),
        NULL::uuid, 'utility non risolta da billing_account'
      );
    END IF;

    IF resolved_utility_id IS NOT NULL AND resolved_utility_id <> v_utility_from_ba THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', p_caller, 'E_GENERICO',
        jsonb_build_object('scope',p_scope,'severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','utility non coerente con billing_account','billing_account_id',p_billing_account_id,'utility_id',resolved_utility_id,'utility_attesa',v_utility_from_ba)),
        NULL::uuid, 'utility non coerente con billing_account'
      );
    END IF;

    resolved_utility_id := COALESCE(resolved_utility_id, v_utility_from_ba);
  END IF;

  v_emittente_from_ba := anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id);

  IF p_emittente_soggetto_ruolo_id IS NOT NULL
     AND p_billing_account_id IS NOT NULL
     AND p_emittente_soggetto_ruolo_id <> v_emittente_from_ba THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', p_caller, 'E_GENERICO',
      jsonb_build_object('scope',p_scope,'severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','emittente non coerente con billing_account','billing_account_id',p_billing_account_id,'emittente_soggetto_ruolo_id',p_emittente_soggetto_ruolo_id,'emittente_atteso',v_emittente_from_ba)),
      NULL::uuid, 'emittente non coerente con billing_account'
    );
  END IF;

  resolved_emittente_soggetto_ruolo_id := COALESCE(p_emittente_soggetto_ruolo_id, v_emittente_from_ba);

  IF p_check_emittente_attivo THEN
    SELECT EXISTS (
      SELECT 1
        FROM anagrafiche.emittenti_fiscali ef
       WHERE ef.soggetto_ruolo_id = resolved_emittente_soggetto_ruolo_id
         AND ef.attivo IS TRUE
    )
    INTO v_emittente_attivo;

    IF COALESCE(v_emittente_attivo, false) IS FALSE THEN
      PERFORM script.fn_log_and_raise_error(
        'vendite', p_caller, 'E_GENERICO',
        jsonb_build_object('scope',p_scope,'severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','emittente fiscale non attivo/non valido','emittente_soggetto_ruolo_id',resolved_emittente_soggetto_ruolo_id)),
        NULL::uuid, 'emittente fiscale non attivo/non valido'
      );
    END IF;
  END IF;

  RETURN NEXT;
END
$function$

COMMENT ON FUNCTION vendite.fn_resolve_lotto_utility_emittente(p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_scope text, p_caller text, p_check_emittente_attivo boolean)
IS 'Helper condiviso: risolve e valida utility/emittente per i lotti (con fallback default emittente).';
```

---
{% include-markdown "signature-core.md" %}
