# ⚙️ Funzione `trgfn_acq_ordini_protect_num`

```sql
CREATE FUNCTION trgfn_acq_ordini_protect_num()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION acquisti.trgfn_acq_ordini_protect_num()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_codice_stato text;
BEGIN
  -- legge il codice interno dello stato corrente
  SELECT s.codice_interno
    INTO v_codice_stato
    FROM config.stati_doc_ordini s
   WHERE s.id = OLD.stato_doc_ordine_id;

  IF v_codice_stato IN ('SENT','CONFIRMED','RECEIVED','INVOICED','CANCELLED') THEN
    IF NEW.numero IS DISTINCT FROM OLD.numero
       OR NEW.serie IS DISTINCT FROM OLD.serie
       OR NEW.anno  IS DISTINCT FROM OLD.anno
       OR NEW.data  IS DISTINCT FROM OLD.data THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_NUMERAZIONE_IMMUTABILE',
        jsonb_build_object('ordine_id', OLD.id, 'stato', v_codice_stato),
        NULL::uuid, 'acquisti.ordini', OLD.id::text
      );
    END IF;
  END IF;

  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
