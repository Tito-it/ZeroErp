{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_guard_pin_immutabile.md" %}
# ⚙️ Funzione `trgfn_pratiche_guard_pin_immutabile`

```sql
CREATE FUNCTION trgfn_pratiche_guard_pin_immutabile()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_pin_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il PIN dell'edizione di workflow e' definitivo. Una volta
--        valorizzato non cambia: le pratiche in volo non migrano di
--        edizione (V6). Ammessa solo la prima valorizzazione
--        (NULL -> valore), es. il backfill Fase 0.
BEGIN
  IF OLD.definizione_id IS NOT NULL
     AND NEW.definizione_id IS DISTINCT FROM OLD.definizione_id THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_pratiche_guard_pin_immutabile',
      'E_PRATICHE_PIN_IMMUTABILE',
      jsonb_build_object(
        'pratica_id',      NEW.id,
        'definizione_da',  OLD.definizione_id,
        'definizione_a',   NEW.definizione_id
      ),
      NEW.tx_id,
      NEW.id::text,
      OLD.definizione_id::text
    );
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_guard_pin_immutabile()
IS 'BEFORE UPDATE OF definizione_id su pratiche.pratiche: il pin dell''edizione di workflow e'' immutabile una volta valorizzato (PRATICHE_PIN_IMMUTABILE 513). Ammette solo NULL->valore (backfill Fase 0). Cuore di V6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
