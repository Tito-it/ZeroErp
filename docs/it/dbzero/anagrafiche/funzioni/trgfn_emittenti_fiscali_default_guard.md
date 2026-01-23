{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_default_guard.md" %}
# ⚙️ Funzione `trgfn_emittenti_fiscali_default_guard`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_default_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_count int;
  v_emittenti int;
  v_area text := TG_TABLE_SCHEMA;
BEGIN
  SELECT count(*)
    INTO v_emittenti
    FROM anagrafiche.emittenti_fiscali;

  SELECT count(*)
    INTO v_count
    FROM anagrafiche.emittenti_fiscali_billing_account
   WHERE is_default = true;

  IF v_emittenti = 0 AND v_count = 0 THEN
    RETURN NULL;
  END IF;

  IF v_count <> 1 THEN
    PERFORM script.fn_log_and_raise_error(
      v_area,
      TG_NAME,
      'E_GENERICO',
      jsonb_build_object(
        'detail', 'Deve esistere un solo emittente fiscale di default',
        'found', v_count,
        'emittenti_fiscali', v_emittenti
      ),
      NULL::uuid,
      'Deve esistere un solo emittente fiscale di default'
      
    );
  END IF;

  RETURN NULL;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
