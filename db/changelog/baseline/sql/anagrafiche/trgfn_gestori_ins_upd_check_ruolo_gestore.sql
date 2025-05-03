CREATE OR REPLACE FUNCTION anagrafiche.trgfn_gestori_ins_upd_check_ruolo_gestore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    codice_ruolo TEXT;
BEGIN
-- Verifica che sia definito effettivamente come gestore
    SELECT r.cd_int_ruolo
    INTO codice_ruolo
    FROM anagrafiche.soggetti_ruoli sr
    JOIN config.tipi_ruoli r ON r.id = sr.ruolo_id
    WHERE sr.id = NEW.soggetto_ruolo_id;

    IF codice_ruolo IS DISTINCT FROM 'GE' THEN
        RAISE EXCEPTION '%',
            script.fn_get_messaggio('E_GESTORE_RUOLO_MANCANTE');
    END IF;

    RETURN NEW;
END;
$function$
