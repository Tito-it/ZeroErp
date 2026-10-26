{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_soggetto_contatti.md" %}
# ⚙️ Funzione `trgfn_soggetti_guard_soggetto_contatti`

```sql
CREATE FUNCTION trgfn_soggetti_guard_soggetto_contatti()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_soggetto_contatti()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_count INTEGER;
    
  BEGIN
    
    -- ====================================================================
    -- Verifica che il soggetto abbia almeno:
    --   • un contatto di default (is_default = TRUE), oppure
    --   • un contatto con almeno un canale non nullo 
    -- ====================================================================
    SELECT COUNT(*) INTO v_count
      FROM anagrafiche.contatti c
    WHERE c.soggetto_id = NEW.id
      AND (
        c.is_default
        OR c.email      IS NOT NULL
        OR c.telefono   IS NOT NULL
        OR c.cellulare  IS NOT NULL
        OR c.pec        IS NOT NULL
      );

    IF v_count = 0 THEN
      -- Logga e solleva errore usando il wrapper centralizzato
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,                               -- nome del trigger
        'E_SOGGETTO_NO_CONTATTI',              -- codice messaggio
        jsonb_build_object('soggetto_id', NEW.id),  -- contesto JSON
        NULL::uuid,                                    
        VARIADIC ARRAY[]::text[]                -- argomenti variabili
      );
      -- fn_log_and_raise_error darà RAISE EXCEPTION internamente
    END IF;

    RETURN NEW;
  END;
  $function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_soggetto_contatti()
IS 'Trigger che verifica al commit che un soggetto abbia almeno un contatto valido;utilizza fn_log_and_raise_error per log e exception.';
```

</div>

---
{% include-markdown "signature-core.md" %}
