{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_default_bootstrap.md" %}
# ⚙️ Funzione `trgfn_emittenti_fiscali_default_bootstrap`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_default_bootstrap()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_bootstrap()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN

  
  IF NOT EXISTS (
    SELECT 1
      FROM anagrafiche.emittenti_fiscali_billing_account
     WHERE is_default = true
  ) THEN
    INSERT INTO anagrafiche.emittenti_fiscali_billing_account (
      billing_account_id,
      emittente_soggetto_ruolo_id,
      is_default,
      meta
    )
    VALUES (
      NULL,
      NEW.soggetto_ruolo_id,
      true,
      '{}'::jsonb
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_bootstrap()
IS 'Crea automaticamente il default emittente fiscale al primo inserimento';
```

</div>

---
{% include-markdown "signature-core.md" %}
