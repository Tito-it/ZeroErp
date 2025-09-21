# ⚙️ Funzione `trgfn_fatture_indirizzi_only_allowed_tipi`

```sql
CREATE FUNCTION trgfn_fatture_indirizzi_only_allowed_tipi()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_indirizzi_only_allowed_tipi()
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

  IF v_codice IS NULL OR v_codice NOT IN ('FATT','SPED','FORNITURA','RES') THEN
   
     PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_TIPO_INDIRIZZO',
        jsonb_build_object('table', 'vendite.fatture_indirizzi',
        'fattura_id', NEW.fattura_id,
        'tipo_indirizzo_id', NEW.tipo_indirizzo_id,
        'codice_interno', v_codice),
        NULL::uuid,  NEW.tipo_indirizzo_id::text, v_codice, 'Fatture' , 'FATT, SPED, FORNITURA, RES.'
      );
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
