# ⚙️ Funzione `trgfn_ordini_indirizzi_only_allowed_tipi`

```sql
CREATE FUNCTION trgfn_ordini_indirizzi_only_allowed_tipi()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_indirizzi_only_allowed_tipi()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_codice text;
BEGIN
  
  SELECT t.codice_interno
    INTO v_codice
    FROM config.tipi_indirizzi t
   WHERE t.id = NEW.tipo_indirizzo_id;

  IF v_codice IS NULL OR v_codice NOT IN ('CON','FATT') THEN
   
     PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_TIPO_INDIRIZZO',
        jsonb_build_object('table', 'vendite.ordini_indirizzi',
        'ordine_id', NEW.ordine_id,
        'tipo_indirizzo_id', NEW.tipo_indirizzo_id,
        'codice_interno', v_codice),
        NULL::uuid,  NEW.tipo_indirizzo_id::text, v_codice, 'ordini' , 'CON, FATT'
      );
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
