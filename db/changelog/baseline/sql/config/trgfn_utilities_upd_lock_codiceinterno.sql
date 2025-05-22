-- FUNCTION: config.trgfn_utilities_upd_lock_codiceinterno()

-- DROP FUNCTION IF EXISTS config.trgfn_utilities_upd_lock_codiceinterno();

CREATE OR REPLACE FUNCTION config.trgfn_utilities_upd_lock_codiceinterno()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
BEGIN
    IF NEW.cd_int_utility <> OLD.cd_int_utility THEN
        RAISE EXCEPTION 'Il codice interno utility non può essere modificato';
    END IF;
    RETURN NEW;
END;
$BODY$;

ALTER FUNCTION config.trgfn_utilities_upd_lock_codiceinterno()
    OWNER TO titodb;

COMMENT ON FUNCTION config.trgfn_utilities_upd_lock_codiceinterno()
    IS 'Blocca modifica del codice interno utility';
