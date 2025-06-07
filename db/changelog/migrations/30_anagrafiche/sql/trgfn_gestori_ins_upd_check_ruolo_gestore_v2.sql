-- ========================================================================
-- FUNCTION: anagrafiche.trgfn_gestori_ins_upd_check_ruolo_gestore()
--   Ogni volta che inserisco/aggiorno in gestori, gestisco la
--   creazione/verifica della riga corrispondente in soggetti_ruoli
--   alimentando poi in NEW.soggetto_ruolo_id il record finale.
-- ========================================================================
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_gestori_ins_upd_check_ruolo_gestore()
    RETURNS trigger
    LANGUAGE plpgsql
AS $$
BEGIN
    -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (nuovo o esistente),
    -- delegando completamente alla funzione generica:
    NEW.soggetto_ruolo_id := script.fn_check_ins_soggetto_ruolo(
                              p_soggetto_id       := NEW.soggetto_id,
                              p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                              p_cd_int_ruolo      := 'GE'
                            );
    RETURN NEW;
END;
$$;


COMMENT ON FUNCTION anagrafiche.trgfn_gestori_ins_upd_check_ruolo_gestore() IS
  'Trigger che, prima di inserire/aggiornare in anagrafiche.gestori,
   chiama fn_check_ins_soggetto_ruolo per creare o validare il legame
   soggetto→ruolo (cd_int_ruolo = ''GE'').';
