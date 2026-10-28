{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_valida_cf_piva_dispatch.md" %}
# ⚙️ Funzione `trgfn_soggetti_valida_cf_piva_dispatch`

```sql
CREATE FUNCTION trgfn_soggetti_valida_cf_piva_dispatch()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
  DECLARE
    country TEXT;
  BEGIN
    SELECT codice_iso2 INTO country
      FROM config.stati
    WHERE id = NEW.stato_id
    LIMIT 1;

    IF country = 'IT' THEN
      PERFORM script.fn_validate_cf_piva_it(
        NEW.tipo_soggetto_dettaglio_id,
        NEW.partita_iva,
        NEW.piva_gruppo_acquisto,
        NEW.codice_fiscale
      );
    END IF;

    RETURN NEW;
  END;
  $function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()
IS 'Dispatcher per la validazione della partita IVA e del codice fiscale per i soggetti in base al paese.';
```

</div>

---
{% include-markdown "signature-core.md" %}
