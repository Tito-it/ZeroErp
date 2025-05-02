CREATE OR REPLACE FUNCTION config.trgfn_tipi_contatti_upd_lock_cod_interno()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    RAISE EXCEPTION 'cod_int_contatto non può essere modificato';
END;
$function$
