{% include-markdown "it/dbzero/vendite/manual/fn_get_valuta_id.md" %}
# ⚙️ Funzione `fn_get_valuta_id`

```sql
CREATE FUNCTION fn_get_valuta_id(p_billing_account_id bigint, p_utility_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_valuta_id(p_billing_account_id bigint, p_utility_id integer)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_valuta_id config.valute.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve la valuta con priorita' su:
  --   1) billing_account (se presente)
  --   2) utility (fallback)
  --   3) gestore (default di sistema)
  -- =========================================================

  IF p_billing_account_id IS NOT NULL THEN
    SELECT ba.valuta_id
      INTO v_valuta_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_billing_account_id;
  END IF;

  IF v_valuta_id IS NULL AND p_utility_id IS NOT NULL THEN
    SELECT u.valuta_id
      INTO v_valuta_id
      FROM config.utilities u
     WHERE u.id = p_utility_id;
  END IF;

  IF v_valuta_id IS NULL THEN
    SELECT g.valuta_id
      INTO v_valuta_id
      FROM anagrafiche.gestori g
     WHERE g.attivo IS TRUE
     ORDER BY g.id
     LIMIT 1;
  END IF;

  IF v_valuta_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_get_valuta_id',
      'E_GENERICO',
      jsonb_build_object(
        'detail','Valuta non risolta (BA/utility/gestore)',
        'billing_account_id', p_billing_account_id,
        'utility_id', p_utility_id
      ),
      NULL::uuid,
      concat('Valuta non risolta (BA/utility/gestore)', 
      ' billing_account_id ', p_billing_account_id::text,
        ', utility_id ', p_utility_id::text
       )
    );
  END IF;

  RETURN v_valuta_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_valuta_id(p_billing_account_id bigint, p_utility_id integer)
IS 'Risoluzione valuta_id: BA -> utility -> default gestore.';
```

---
{% include-markdown "signature-core.md" %}
