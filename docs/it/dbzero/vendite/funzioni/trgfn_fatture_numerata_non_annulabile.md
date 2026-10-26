{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_numerata_non_annulabile.md" %}
# ⚙️ Funzione `trgfn_fatture_numerata_non_annulabile`

```sql
CREATE FUNCTION trgfn_fatture_numerata_non_annulabile()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_numerata_non_annulabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_to_cancel  boolean := false;
  v_numbered   boolean := false;
  v_numero     bigint;
BEGIN
  
  IF NEW.stato_doc_fiscale_id IS DISTINCT FROM OLD.stato_doc_fiscale_id THEN
    
    SELECT (s.codice_interno = 'ANNULLATA')
      INTO v_to_cancel
      FROM config.stati_doc_fiscale s
     WHERE s.id = NEW.stato_doc_fiscale_id;

    
    v_numero := COALESCE(NEW.numero, OLD.numero);
    v_numbered := v_numero IS NOT NULL;

    IF v_to_cancel AND v_numbered THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_FATTURA_NON_ANNULLABILE',
        jsonb_build_object('fattura_id', OLD.id, 'numero', v_numero),
        NULL::uuid, OLD.id::text
      );
    END IF;
  END IF;

  RETURN NEW;
END$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
