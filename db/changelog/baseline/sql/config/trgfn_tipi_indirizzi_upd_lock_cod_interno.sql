CREATE OR REPLACE FUNCTION config.trgfn_tipi_indirizzi_upd_lock_cod_interno()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF OLD.cod_int_tipo_indirizzo IS DISTINCT FROM NEW.cod_int_tipo_indirizzo THEN
    RAISE EXCEPTION 'Impossibile modificare il codice interno del tipo indirizzo';
  END IF;
  RETURN NEW;
END;
$function$
