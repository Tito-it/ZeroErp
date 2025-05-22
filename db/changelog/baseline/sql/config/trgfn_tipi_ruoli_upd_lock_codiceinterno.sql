-- FUNCTION: config.trgfn_tipi_ruoli_upd_lock_codiceinterno()

-- DROP FUNCTION IF EXISTS config.trgfn_tipi_ruoli_upd_lock_codiceinterno();

CREATE OR REPLACE FUNCTION config.trgfn_tipi_ruoli_upd_lock_codiceinterno()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
BEGIN
    IF NEW.cd_int_ruolo <> OLD.cd_int_ruolo THEN
        RAISE EXCEPTION 'Il codice interno ruolo non può essere modificato';
    END IF;
    RETURN NEW;
END;
$BODY$;

