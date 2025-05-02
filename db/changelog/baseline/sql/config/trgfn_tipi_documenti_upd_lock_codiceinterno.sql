-- FUNCTION: config.trgfn_tipi_documenti_upd_lock_codiceinterno()

-- DROP FUNCTION IF EXISTS config.trgfn_tipi_documenti_upd_lock_codiceinterno();

CREATE OR REPLACE FUNCTION config.trgfn_tipi_documenti_upd_lock_codiceinterno()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
BEGIN
    IF NEW.cd_int_tipo_documento <> OLD.cd_int_tipo_documento THEN
        RAISE EXCEPTION 'Il codice interno tipo documento non può essere modificato';
    END IF;
    RETURN NEW;
END;
$BODY$;

ALTER FUNCTION config.trgfn_tipi_documenti_upd_lock_codiceinterno()
    OWNER TO postgres;

COMMENT ON FUNCTION config.trgfn_tipi_documenti_upd_lock_codiceinterno()
    IS 'Blocca modifica al codice interno tipo documento.Before';
