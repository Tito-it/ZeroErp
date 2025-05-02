CREATE OR REPLACE FUNCTION config.trgfn_stati_cliente_upd_lock_codiceinterno()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF OLD.cod_int_stato_cliente IS DISTINCT FROM NEW.cod_int_stato_cliente THEN
    RAISE EXCEPTION 'Impossibile modificare il codice interno cod_int_stato_cliente';
  END IF;
  IF OLD.stato_cliente IS DISTINCT FROM NEW.stato_cliente THEN
    RAISE EXCEPTION 'Impossibile modificare il valore interno stato_cliente';
  END IF;
  RETURN NEW;
END;
$function$
