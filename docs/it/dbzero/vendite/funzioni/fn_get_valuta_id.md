{% include-markdown "it/dbzero/vendite/manual/fn_get_valuta_id.md" %}
# ⚙️ Funzione `fn_get_valuta_id`

```sql
CREATE FUNCTION fn_get_valuta_id(p_billing_account_id bigint, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_valuta_id(p_billing_account_id bigint, p_emittente_soggetto_ruolo_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_valuta_id config.valute.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve la valuta con priorita` su:
  --   1) billing_account (se presente e con valuta)
  --   2) emittente fiscale (se presente e con valuta)
  --   3) gestore (singleton, default di sistema, NOT NULL)
  -- =========================================================

  IF p_billing_account_id IS NOT NULL THEN
    SELECT ba.valuta_id
      INTO v_valuta_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_billing_account_id;
  END IF;

  IF v_valuta_id IS NULL AND p_emittente_soggetto_ruolo_id IS NOT NULL THEN
    SELECT ef.valuta_id
      INTO v_valuta_id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.soggetto_ruolo_id = p_emittente_soggetto_ruolo_id;
  END IF;

  IF v_valuta_id IS NULL THEN
    SELECT g.valuta_id
      INTO v_valuta_id
      FROM anagrafiche.gestori g
     ORDER BY g.id
     LIMIT 1;
  END IF;

  IF v_valuta_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_get_valuta_id',
      'E_GENERICO',
      jsonb_build_object(
        'detail', 'Valuta non risolta (BA/emittente/gestore)',
        'billing_account_id', p_billing_account_id,
        'emittente_soggetto_ruolo_id', p_emittente_soggetto_ruolo_id
      ),
      NULL::uuid,
      concat('Valuta non risolta (BA/emittente/gestore)',
        ' billing_account_id=', p_billing_account_id::text,
        ' emittente=', p_emittente_soggetto_ruolo_id::text)
    );
  END IF;

  RETURN v_valuta_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_valuta_id(p_billing_account_id bigint, p_emittente_soggetto_ruolo_id bigint)
IS 'Risoluzione valuta_id: BA -> emittente fiscale -> gestore (fallback).';
```

---
{% include-markdown "signature-core.md" %}
