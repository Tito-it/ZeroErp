# ⚙️ Funzione `trgfn_a10_fatture_protect_num`

```sql
CREATE FUNCTION trgfn_a10_fatture_protect_num()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_a10_fatture_protect_num()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_is_locked boolean := false;
  v_stato     text;
BEGIN
  
  SELECT s.codice_interno IN ('EMESSA','INVIATA','CONSEGNATA','SCARTATA','REGISTRATA','ANNULLATA'),
         s.codice_interno
    INTO v_is_locked, v_stato
    FROM config.stati_doc_fiscale s
   WHERE s.id = OLD.stato_doc_fiscale_id;

  IF COALESCE(v_is_locked, false) THEN
    IF NEW.numero                 IS DISTINCT FROM OLD.numero
       OR NEW.serie               IS DISTINCT FROM OLD.serie
       OR NEW.anno                IS DISTINCT FROM OLD.anno
       OR NEW.data                IS DISTINCT FROM OLD.data
       OR NEW.registro_id         IS DISTINCT FROM OLD.registro_id
       OR NEW.tipo_doc_fiscale_id IS DISTINCT FROM OLD.tipo_doc_fiscale_id
    THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_NUMERAZIONE_IMMUTABILE',
        jsonb_build_object('fattura_id', OLD.id, 'stato', v_stato),
        NULL::uuid, 'vendite.fatture' , OLD.id::text
      );
    END IF;
  END IF;

  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
