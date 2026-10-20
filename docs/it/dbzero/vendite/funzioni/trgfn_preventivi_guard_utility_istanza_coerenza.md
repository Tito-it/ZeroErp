{% include-markdown "it/dbzero/vendite/manual/trgfn_preventivi_guard_utility_istanza_coerenza.md" %}
# ⚙️ Funzione `trgfn_preventivi_guard_utility_istanza_coerenza`

```sql
CREATE FUNCTION trgfn_preventivi_guard_utility_istanza_coerenza()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_guard_utility_istanza_coerenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Skip se istanza non valorizzata (post NOT NULL e' impossibile,
  -- ma safety net per il rollout iniziale e per evitare errori
  -- fuorvianti durante il backfill).
  IF NEW.istanza_utility_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Delega al pure check generico.
  IF NOT script.fn_check_utility_istanza_coerenza(
         NEW.istanza_utility_id,
         NEW.utility_id
     ) THEN
    -- Ultimo arg = valore per il %s del messaggio CSV
    -- (E_PREV_UTILITY_ISTANZA_INCOERENTE: %s = breve contesto).
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'trgfn_preventivi_guard_utility_istanza_coerenza',
      'E_PREV_UTILITY_ISTANZA_INCOERENTE',
      jsonb_build_object(
        'campo', 'utility_id',
        'detail', 'utility_id non coerente con istanza_utility_id (no BA/IDP/cliente matching)',
        'istanza_utility_id', NEW.istanza_utility_id,
        'utility_id', NEW.utility_id
      ),
      NULL::uuid,
      concat('istanza_utility_id=', NEW.istanza_utility_id::text,
             ', utility_id=', NEW.utility_id::text)
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_preventivi_guard_utility_istanza_coerenza()
IS 'Guard BEFORE INSERT/UPDATE su vendite.preventivi: verifica coerenza (istanza_utility_id, utility_id) via script.fn_check_utility_istanza_coerenza. Solleva E_PREV_UTILITY_ISTANZA_INCOERENTE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
