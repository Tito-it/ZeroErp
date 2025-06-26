# ⚙️ Funzione `fn_get_tipo_contatto_id`

```sql
CREATE FUNCTION fn_get_tipo_contatto_id(p_cod_int_tipo_contatto character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_tipo_contatto_id(p_cod_int_tipo_contatto character varying)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_id INTEGER;
BEGIN
--  Funzione per recuperare l'ID del tipo contatto DEFAULT
--  Funzione generica per recuperare l'ID di un tipo di contatto dato il codice interno
  SELECT id INTO v_id
    FROM config.tipi_contatti
   WHERE cod_int_tipo_contatto = p_cod_int_tipo_contatto;
  IF v_id IS NULL THEN
    RAISE EXCEPTION '%', config.fn_get_messaggio('E_DEFAULT_CONTATTO_MISSING');
  END IF;
  RETURN v_id;
END;
$function$
```