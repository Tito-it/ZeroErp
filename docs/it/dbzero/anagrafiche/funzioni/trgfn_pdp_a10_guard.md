{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_pdp_a10_guard.md" %}
# ⚙️ Funzione `trgfn_pdp_a10_guard`

```sql
CREATE FUNCTION trgfn_pdp_a10_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_pdp_a10_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ------------------------------------------------------------
  -- Funzione: anagrafiche.trgfn_pdp_a10_guard()
  -- Impedisce la modifica di pdp e indirizzo_dettaglio_id
  -- dopo la prima valorizzazione.
  ------------------------------------------------------------
  IF TG_OP = 'UPDATE' THEN
    -- Blocca cambio codice PDP (se già valorizzato)
    IF OLD.pdp IS NOT NULL AND NEW.pdp IS DISTINCT FROM OLD.pdp THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
        jsonb_build_object('column','pdp','id',OLD.id),
        NULL::uuid, 
        concat('pdp: ' , OLD.pdp::text)
      );
    END IF;

    -- Blocca spostamento fisico del PDP
    IF OLD.indirizzo_dettaglio_id IS NOT NULL
       AND NEW.indirizzo_dettaglio_id IS DISTINCT FROM OLD.indirizzo_dettaglio_id THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
        jsonb_build_object('column','indirizzo_dettaglio_id','id',OLD.id),
        NULL::uuid, 
        concat('indirizzo_dettaglio_id: ' , OLD.indirizzo_dettaglio_id::text )
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_pdp_a10_guard()
IS 'Blocca modifiche a pdp e indirizzo_dettaglio_id (immutabili dopo prima valorizzazione).';
```

</div>

---
{% include-markdown "signature-core.md" %}
