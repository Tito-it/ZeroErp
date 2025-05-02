-- FUNCTION: config.trgfn_stati_pratiche_upd_lock_codiceinterno()

-- DROP FUNCTION IF EXISTS config.trgfn_stati_pratiche_upd_lock_codiceinterno();

CREATE OR REPLACE FUNCTION config.trgfn_stati_pratiche_upd_lock_codiceinterno()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
BEGIN
    IF NEW.cd_int_stato <> OLD.cd_int_stato THEN
        RAISE EXCEPTION 'Il codice interno stato non può essere modificato';
    END IF;
    RETURN NEW;
END;
$BODY$;

ALTER FUNCTION config.trgfn_stati_pratiche_upd_lock_codiceinterno()
    OWNER TO postgres;

COMMENT ON FUNCTION config.trgfn_stati_pratiche_upd_lock_codiceinterno()
    IS 'Blocco codice interno stato pratica';
