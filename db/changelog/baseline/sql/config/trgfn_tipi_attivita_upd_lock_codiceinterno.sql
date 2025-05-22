-- FUNCTION: config.trgfn_tipi_attivita_upd_lock_codiceinterno()

-- DROP FUNCTION IF EXISTS config.trgfn_tipi_attivita_upd_lock_codiceinterno();

CREATE OR REPLACE FUNCTION config.trgfn_tipi_attivita_upd_lock_codiceinterno()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
BEGIN
    IF NEW.cd_int_tipo_attivita <> OLD.cd_int_tipo_attivita THEN
        RAISE EXCEPTION 'Il codice interno tipo attività non può essere modificato';
    END IF;
    RETURN NEW;
END;
$BODY$;

ALTER FUNCTION config.trgfn_tipi_attivita_upd_lock_codiceinterno()
    OWNER TO titodb;
